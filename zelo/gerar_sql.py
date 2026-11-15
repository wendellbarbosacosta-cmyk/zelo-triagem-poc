"""Gera o init.sql a partir de data/tabela_triagem.csv (o CSV e a fonte unica).

    python -m zelo.gerar_sql           # reescreve init.sql
    python -m zelo.gerar_sql --check   # sai com erro se init.sql estiver desatualizado
"""
from __future__ import annotations

import sys

from . import config
from .persistencia import DDL, _modificadores_texto
from .tabela import COLUNAS, Tabela

CAMINHO_INIT_SQL = config.RAIZ / "init.sql"


def _lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return "'" + str(v).replace("'", "''") + "'"


def gerar(tabela: Tabela) -> str:
    cab = (
        "-- GERADO por `python -m zelo.gerar_sql` a partir de data/tabela_triagem.csv. NAO edite a mao.\n"
        "-- Para mudar uma regra: edite o CSV, rode o gerador e `python triagem_zelo.py --seed`.\n"
    )
    linhas = []
    for r in tabela:
        vals = (
            r.codigo, r.tipo_ocorrencia, r.categoria, r.urgencia_base, r.o_que_sobe_ou_desce,
            _modificadores_texto(r), r.quem_resolve, r.sensivel, r.sistema_garantia, r.origem,
        )
        linhas.append("(" + ", ".join(_lit(v) for v in vals) + ")")
    upd = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUNAS if c != "codigo")
    ins = f"INSERT INTO regras_triagem ({', '.join(COLUNAS)}) VALUES\n" + ",\n".join(linhas)
    return f"{cab}\n{DDL}\n\n{ins}\nON CONFLICT (codigo) DO UPDATE SET {upd};\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    novo = gerar(Tabela.from_csv())
    if "--check" in argv:
        atual = CAMINHO_INIT_SQL.read_text(encoding="utf-8").replace("\r\n", "\n") if CAMINHO_INIT_SQL.exists() else ""
        if atual != novo:
            print("init.sql desatualizado: rode `python -m zelo.gerar_sql`")
            return 1
        print("init.sql em dia com o CSV")
        return 0
    CAMINHO_INIT_SQL.write_text(novo, encoding="utf-8", newline="\n")
    print(f"init.sql gerado ({len(Tabela.from_csv())} regras)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
