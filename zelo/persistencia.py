"""Persistencia (opcional): PostgreSQL guarda a tabela de regras, MongoDB guarda as ocorrencias.

psycopg2 e pymongo so sao importados quando usados - o motor e os testes nao dependem deles.
A tabela do PostgreSQL e SEMPRE gerada a partir do CSV (fonte unica): `python triagem_zelo.py --seed`.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from . import TABELA_VERSAO, config
from .tabela import COLUNAS, Tabela
from .triagem import ResultadoTriagem

PG_CONFIG = {
    "host": os.environ.get("ZELO_PG_HOST", "localhost"),
    "port": int(os.environ.get("ZELO_PG_PORT", "5435")),
    "dbname": os.environ.get("ZELO_PG_DB", "zelo_db"),
    "user": os.environ.get("ZELO_PG_USER", "zelo_admin"),
    "password": os.environ.get("ZELO_PG_PASSWORD", "zelo_password_123"),  # so para dev local
}
MONGO_URI = os.environ.get("ZELO_MONGO_URI", "mongodb://zelo_admin:zelo_password_123@localhost:27019/")

_CATS = ", ".join("'" + c.replace("'", "''") + "'" for c in config.CATEGORIAS_OFICIAIS)

DDL = f"""CREATE TABLE IF NOT EXISTS regras_triagem (
    codigo VARCHAR(10) PRIMARY KEY,
    tipo_ocorrencia VARCHAR(200) NOT NULL,
    categoria VARCHAR(50) NOT NULL CHECK (categoria IN ({_CATS})),
    urgencia_base VARCHAR(10) CHECK (urgencia_base IN ('Baixa', 'Média', 'Alta')),
    o_que_sobe_ou_desce TEXT NOT NULL,
    modificadores TEXT NOT NULL DEFAULT '',
    quem_resolve VARCHAR(100) NOT NULL,
    sensivel BOOLEAN NOT NULL,
    sistema_garantia VARCHAR(40),
    origem VARCHAR(40) NOT NULL DEFAULT 'tabela_v3',
    versao VARCHAR(10) NOT NULL DEFAULT '{TABELA_VERSAO}'
);"""

_UPSERT_COLS = [c for c in COLUNAS if c != "codigo"]
UPSERT = (
    "INSERT INTO regras_triagem (" + ", ".join(COLUNAS) + ") VALUES (" + ", ".join(["%s"] * len(COLUNAS)) + ") "
    "ON CONFLICT (codigo) DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in _UPSERT_COLS)
)


def _valores(r) -> tuple:
    return (
        r.codigo, r.tipo_ocorrencia, r.categoria, r.urgencia_base, r.o_que_sobe_ou_desce,
        _modificadores_texto(r), r.quem_resolve, r.sensivel, r.sistema_garantia, r.origem,
    )


def _modificadores_texto(r) -> str:
    partes = []
    for m in r.modificadores:
        cond = "&".join(m.condicoes)
        efeito = f"{m.valor:+d}" if m.efeito == "delta" else (f"vira={m.valor}" if m.efeito == "vira" else m.efeito)
        partes.append(f"{cond}:{efeito}")
    return ";".join(partes)


def conectar_pg():
    import psycopg2

    return psycopg2.connect(**PG_CONFIG)


def semear_tabela(conn, tabela: Tabela) -> int:
    """Recria regras_triagem a partir do CSV (a tabela e derivada, pode ser recriada)."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS regras_triagem;")
        cur.execute(DDL)
        for r in tabela:
            cur.execute(UPSERT, _valores(r))
    conn.commit()
    return len(tabela)


def tabela_do_postgres(conn) -> Tabela:
    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT " + ", ".join(COLUNAS) + " FROM regras_triagem ORDER BY ctid;")
        linhas = []
        for d in cur.fetchall():
            d = dict(d)
            d["sensivel"] = "Sim" if d["sensivel"] else "Não"
            d["urgencia_base"] = d["urgencia_base"] or "—"
            linhas.append({k: ("" if v is None else v) for k, v in d.items()})
    return Tabela.from_linhas(linhas)


def montar_documento(resultado: ResultadoTriagem, condominio: str, morador: str, foto_url: str | None = None) -> dict:
    agora = datetime.now(timezone.utc)
    r = resultado
    timeline = [
        {"data_hora": agora, "evento": f"Recebida pelo WhatsApp ({morador})", "mensagem_original": r.mensagem},
        {
            "data_hora": agora,
            "evento": f"Classificada pela IA: {r.categoria} | Urgência {r.urgencia_final}",
            "ajustes_de_contexto": r.ajustes,
        },
        {"data_hora": agora, "evento": f"Encaminhada para: {r.responsavel_detalhe}"},
    ]
    if r.vai_ao_sindico:
        timeline.append({"data_hora": agora, "evento": "Enviada ao síndico (regra do sensível)", "motivos": r.motivos_sindico})
    if r.selo_garantia:
        timeline.append({"data_hora": agora, "evento": 'Selo "Possível garantia da construtora"'})
    if r.aviso_preventiva:
        timeline.append({"data_hora": agora, "evento": 'Aviso ao síndico: "hora de manutenção preventiva"'})
    return {
        "condominio": condominio,
        "morador": morador,
        "status": "Em andamento",
        "criada_em": agora,
        "classificacao": {
            "codigo_tabela": r.codigo,
            "tipo": r.tipo_ocorrencia,
            "categoria": r.categoria,
            "urgencia_base": r.urgencia_base,
            "urgencia_final": r.urgencia_final,
            "prazo_horas": r.prazo_horas,
            "imediato": r.imediato,
            "responsavel": r.responsavel,
            "executor": r.executor,
            "sensivel_tabela": "sensivel_tabela" in r.motivos_sindico,  # o que a tabela diz
            "vai_ao_sindico": r.vai_ao_sindico,  # o que a trava decidiu (sensivel, garantia ou palavra de risco)
            "motivos_sindico": r.motivos_sindico,
            "selo_garantia": r.selo_garantia,
        },
        "midia": {"foto_abertura": foto_url, "foto_resolucao": None},
        "historico_timeline": timeline,
    }


def salvar_ocorrencia(resultado: ResultadoTriagem, condominio: str, morador: str, foto_url: str | None = None):
    from pymongo import MongoClient

    cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        return cliente["zelo_logs"]["ocorrencias"].insert_one(montar_documento(resultado, condominio, morador, foto_url)).inserted_id
    finally:
        cliente.close()
