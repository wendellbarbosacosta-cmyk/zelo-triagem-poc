"""CLI do POC do Zelo.

    python triagem_zelo.py                 # demo: classifica algumas mensagens (sem banco)
    python triagem_zelo.py --avaliar       # roda as 49 ocorrencias de exemplo
    python triagem_zelo.py "mensagem"      # triagem de uma mensagem  [--hora 22] [--ferias] [--chuva] ...
    python triagem_zelo.py --seed          # recria regras_triagem no PostgreSQL a partir do CSV
    python triagem_zelo.py --persistir ... # alem de triar, grava a ocorrencia no MongoDB
"""
from __future__ import annotations

import argparse
import sys

from zelo import avaliacao
from zelo.classificador import ClassificadorPorRegras
from zelo.equipe import Equipe
from zelo.modelos import Contexto
from zelo.triagem import ResultadoTriagem, triar, tabela_padrao


def imprimir(r: ResultadoTriagem) -> None:
    print("=" * 72)
    print(f'"{r.mensagem}"')
    print("-" * 72)
    if r.status == "pergunta_ao_morador":
        print(f"PERGUNTA AO MORADOR: {r.pergunta}  {r.botoes or ''}")
    elif r.status == "nao_ocorrencia":
        print(f"NÃO É OCORRÊNCIA -> resposta automática: {r.resposta_automatica}")
    else:
        print(f"Item da tabela : [{r.codigo}] {r.tipo_ocorrencia}" if r.codigo else "Item da tabela : (não classificada)")
        print(f"Categoria      : {r.categoria}")
        print(f"Urgência       : {r.urgencia_base or '-'} -> {r.urgencia_final}"
              f"{' (IMEDIATO)' if r.imediato else ''}  | prazo {r.prazo_horas}h")
        print(f"Responsável    : {r.responsavel_detalhe}" + (f"  (executa: {r.executor})" if r.executor and r.executor != r.responsavel else ""))
        print(f"Síndico        : {'SIM - ' + ', '.join(r.motivos_sindico) if r.vai_ao_sindico else ('só avisado' if r.avisa_sindico else 'não')}")
        if r.selo_garantia:
            print('Selo           : "Possível garantia da construtora"')
        if r.aviso_preventiva:
            print('Aviso          : "hora de manutenção preventiva"')
        for a in r.ajustes:
            print(f"   * {a}")
    print("=" * 72 + "\n")


DEMO = [
    ("A bomba da piscina está vazando de novo!", Contexto(hora=10)),
    ("O portão da garagem travou aberto e já são 23h30!", Contexto(hora=23)),
    ("Tô sentindo um cheiro forte de gás na escada do bloco B", Contexto(hora=19)),
    ("Quero reservar a churrasqueira sábado", Contexto(hora=10)),
    ("Problema com a cadeira do salão", Contexto(hora=15)),
]


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mensagem", nargs="?")
    ap.add_argument("--avaliar", action="store_true")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--persistir", action="store_true")
    ap.add_argument("--condominio", default="Condomínio Jardim")
    ap.add_argument("--morador", default="Morador Apto 21")
    ap.add_argument("--hora", type=int)
    ap.add_argument("--ferias", action="store_true", help="periodo especial (ferias/temporada/festas)")
    ap.add_argument("--chuva", action="store_true")
    ap.add_argument("--evento", action="store_true", help="salao/churrasqueira reservado nas proximas 48h")
    ap.add_argument("--reclamacoes", type=int, default=1, help="reclamacoes do mesmo problema em 30 dias")
    ap.add_argument("--habitese-meses", type=int, help="meses desde o habite-se")
    ap.add_argument("--so-portaria-remota", action="store_true")
    a = ap.parse_args(argv)

    if a.seed:
        from zelo import persistencia

        conn = persistencia.conectar_pg()
        try:
            print(f"{persistencia.semear_tabela(conn, tabela_padrao())} regras gravadas no PostgreSQL")
        finally:
            conn.close()
        return 0
    if a.avaliar:
        return avaliacao.main()

    clf = ClassificadorPorRegras()
    equipe = Equipe.so_portaria_remota() if a.so_portaria_remota else Equipe.padrao()
    casos = (
        [(a.mensagem, Contexto(
            hora=a.hora, periodo_especial=a.ferias, chuva=a.chuva, evento_reservado_48h=a.evento,
            reclamacoes_30d=a.reclamacoes, meses_desde_habitese=a.habitese_meses))]
        if a.mensagem else DEMO
    )
    for msg, ctx in casos:
        r = triar(msg, clf.classificar(msg), ctx, tabela_padrao(), equipe)
        imprimir(r)
        if a.persistir:
            from zelo import persistencia

            print(f"   gravada no MongoDB: {persistencia.salvar_ocorrencia(r, a.condominio, a.morador)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
