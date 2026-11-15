"""Tipos de dados do motor: Regra (uma linha da tabela), Modificador, Contexto, Classificacao."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from . import config

PAPEIS = {
    "zelador": "Zelador",
    "manutenção": "Manutenção",
    "engenharia": "Engenharia",
    "portaria": "Portaria",
    "síndico": "Síndico",
    "resposta automática": "Resposta automática",
}


@dataclass(frozen=True)
class Modificador:
    """Um efeito de contexto. Gramatica no CSV: `cond1&cond2:efeito` separados por `;`.

    efeito: +1 / -1 (sobe/desce um nivel) | imediato | alta | sensivel | vira=<codigo>
    (`alta,sensivel` na mesma coluna vira dois modificadores)
    """

    condicoes: tuple[str, ...]
    efeito: str  # 'delta' | 'imediato' | 'alta' | 'sensivel' | 'vira'
    valor: int | str | None = None


def parse_modificadores(texto: str) -> tuple[Modificador, ...]:
    if not texto or not texto.strip():
        return ()
    saida: list[Modificador] = []
    for parte in texto.split(";"):
        parte = parte.strip()
        if not parte:
            continue
        if ":" not in parte:
            raise ValueError(f"modificador sem ':' -> {parte!r}")
        cond, efeitos = parte.split(":", 1)
        condicoes = tuple(c.strip() for c in cond.split("&") if c.strip())
        if not condicoes:
            raise ValueError(f"modificador sem condicao -> {parte!r}")
        for ef in efeitos.split(","):
            ef = ef.strip()
            if re.fullmatch(r"[+-]\d+", ef):
                saida.append(Modificador(condicoes, "delta", int(ef)))
            elif ef in ("imediato", "alta", "sensivel"):
                saida.append(Modificador(condicoes, ef))
            elif ef.startswith("vira="):
                saida.append(Modificador(condicoes, "vira", ef.split("=", 1)[1].strip()))
            else:
                raise ValueError(f"efeito desconhecido {ef!r} em {parte!r}")
    return tuple(saida)


def interpretar_responsavel(texto: str) -> tuple[str, tuple[str, ...], bool]:
    """'Síndico (+ eletricista)' -> ('Síndico', ('Eletricista',), False)."""
    t = texto.strip()
    principal_bruto = re.split(r"[(+]", t, maxsplit=1)[0].strip()
    principal = PAPEIS.get(principal_bruto.lower())
    if principal is None:
        raise ValueError(f"responsavel desconhecido: {texto!r}")
    apoio: list[str] = []
    for item in re.findall(r"\(\+\s*([^)]+)\)", t):
        if not item.lower().startswith("síndico"):
            apoio.append(item.strip().capitalize())
    for item in re.findall(r"\)\s*\+\s*([^(+]+)", t):
        apoio.append(item.strip().capitalize())
    avisa = "avisa o síndico" in t.lower()
    return principal, tuple(apoio), avisa


@dataclass(frozen=True)
class Regra:
    codigo: str
    tipo_ocorrencia: str
    categoria: str
    urgencia_base: str | None  # None = nao entra na triagem
    o_que_sobe_ou_desce: str
    modificadores: tuple[Modificador, ...]
    quem_resolve: str
    sensivel: bool
    sistema_garantia: str | None
    origem: str = "tabela_v3"

    @property
    def nao_e_ocorrencia(self) -> bool:
        return self.urgencia_base is None

    @property
    def responsavel_principal(self) -> str:
        return interpretar_responsavel(self.quem_resolve)[0]

    @property
    def apoio(self) -> tuple[str, ...]:
        return interpretar_responsavel(self.quem_resolve)[1]

    @property
    def avisa_sindico(self) -> bool:
        return interpretar_responsavel(self.quem_resolve)[2]


@dataclass(frozen=True)
class Contexto:
    """O que o condominio/mensagem informa ALEM do texto. Camada 2 da urgencia."""

    hora: int | None = None
    afetados: str | None = None  # 'um_apto' | 'varios' | 'bloco'
    reclamacoes_30d: int = 1  # mesmo problema, mesmo lugar, ultimos 30 dias
    periodo_especial: bool = False  # ferias, temporada da piscina, festas (calendario do condominio)
    chuva: bool = False  # periodo de chuva marcado no calendario (regra especial 2)
    evento_reservado_48h: bool = False  # salao/churrasqueira reservado nas proximas 48h
    meses_desde_habitese: int | None = None  # cadastro do condominio
    sinais: frozenset[str] = field(default_factory=frozenset)  # extraidos da mensagem pela IA

    def com_sinais(self, extras) -> "Contexto":
        return replace(self, sinais=frozenset(self.sinais) | frozenset(extras))

    def tokens(self) -> frozenset[str]:
        t = set(self.sinais)
        if self.hora is not None:
            h = self.hora
            if h >= config.HORA_INICIO_NOITE or h < config.HORA_FIM_NOITE:
                t.add("noite")
            if h >= config.HORA_INICIO_SILENCIO or h < config.HORA_FIM_NOITE:
                t.add("apos_22h")
        if self.afetados == "um_apto":
            t.add("um_apto")
        if self.reclamacoes_30d >= config.LIMITE_REPETICAO:
            t.add("repeticao")
        if self.periodo_especial:
            t.add("periodo_especial")
        if self.chuva:
            t.add("chuva")
        if self.evento_reservado_48h:
            t.add("evento_reservado")
        return frozenset(t)


@dataclass(frozen=True)
class Classificacao:
    """Saida da IA (ou de um classificador de regras): qual linha da tabela + sinais da mensagem."""

    codigo: str | None
    confianca: float = 1.0
    sinais: frozenset[str] = field(default_factory=frozenset)
    esclarecimento: str | None = None  # chave de config.ESCLARECIMENTOS quando a mensagem e vaga
    motivo: str = ""
