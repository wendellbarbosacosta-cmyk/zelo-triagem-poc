"""Avalia o motor contra as ocorrencias de exemplo (ZELO-7) e mede o criterio "nenhum sensivel escapa" (ZELO-9).

    python -m zelo.avaliacao
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

from . import config
from .classificador import Classificador, ClassificadorPorRegras
from .equipe import Equipe
from .modelos import Contexto
from .tabela import Tabela
from .triagem import ResultadoTriagem, triar, tabela_padrao

EQUIPES = {"padrao": Equipe.padrao(), "portaria_remota": Equipe.so_portaria_remota()}


def carregar_ocorrencias(caminho=config.CAMINHO_OCORRENCIAS) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)["ocorrencias"]


def contexto_de(d: dict) -> Contexto:
    return Contexto(**d["contexto"])


def comparar(oc: dict, r: ResultadoTriagem) -> list[str]:
    """Lista de divergencias entre o esperado e o obtido (vazia = acertou)."""
    esp = oc["esperado"]
    erros = []
    if r.status != esp.get("status", "triado"):
        erros.append(f"status: esperado {esp.get('status', 'triado')}, veio {r.status}")
    if esp.get("categoria") != r.categoria and esp.get("status", "triado") != "pergunta_ao_morador":
        erros.append(f"categoria: esperado {esp.get('categoria')}, veio {r.categoria}")
    if esp.get("urgencia") != r.urgencia_final and esp.get("status", "triado") == "triado":
        erros.append(f"urgência: esperado {esp.get('urgencia')}, veio {r.urgencia_final}")
    if esp.get("responsavel") != r.responsavel and esp.get("status", "triado") != "pergunta_ao_morador":
        erros.append(f"responsável: esperado {esp.get('responsavel')}, veio {r.responsavel}")
    if esp["vai_ao_sindico"] != r.vai_ao_sindico:
        erros.append(f"vai_ao_sindico: esperado {esp['vai_ao_sindico']}, veio {r.vai_ao_sindico}")
    if "selo_garantia" in esp and esp["selo_garantia"] != r.selo_garantia:
        erros.append(f"selo_garantia: esperado {esp['selo_garantia']}, veio {r.selo_garantia}")
    if "imediato" in esp and esp["imediato"] != r.imediato:
        erros.append(f"imediato: esperado {esp['imediato']}, veio {r.imediato}")
    if "aviso_preventiva" in esp and esp["aviso_preventiva"] != r.aviso_preventiva:
        erros.append(f"aviso_preventiva: esperado {esp['aviso_preventiva']}, veio {r.aviso_preventiva}")
    if "avisa_sindico" in esp and esp["avisa_sindico"] != r.avisa_sindico:
        erros.append(f"avisa_sindico: esperado {esp['avisa_sindico']}, veio {r.avisa_sindico}")
    if "botoes" in esp and esp["botoes"] != r.botoes:
        erros.append(f"botoes: esperado {esp['botoes']}, veio {r.botoes}")
    if "detalhe_contem" in esp and esp["detalhe_contem"] not in (r.responsavel_detalhe or "").lower():
        erros.append(f"detalhe: esperado conter {esp['detalhe_contem']!r}, veio {r.responsavel_detalhe!r}")
    return erros


@dataclass
class Relatorio:
    total: int = 0
    acertos: int = 0
    base_total: int = 0
    base_acertos: int = 0
    sensiveis_total: int = 0
    escapes: list[int] = field(default_factory=list)  # ids de sensiveis que NAO foram ao sindico
    falsos_alarmes: list[int] = field(default_factory=list)  # nao sensiveis que foram ao sindico
    falhas: dict[int, list[str]] = field(default_factory=dict)


def avaliar(
    classificador: Classificador | None = None,
    ocorrencias: list[dict] | None = None,
    tabela: Tabela | None = None,
) -> Relatorio:
    classificador = classificador or ClassificadorPorRegras()
    ocorrencias = ocorrencias or carregar_ocorrencias()
    tabela = tabela or tabela_padrao()
    rel = Relatorio()
    for oc in ocorrencias:
        cls = classificador.classificar(oc["mensagem"])
        r = triar(oc["mensagem"], cls, contexto_de(oc), tabela, EQUIPES[oc["equipe"]])
        erros = comparar(oc, r)
        rel.total += 1
        if oc["grupo"] == "base":
            rel.base_total += 1
        if not erros:
            rel.acertos += 1
            if oc["grupo"] == "base":
                rel.base_acertos += 1
        else:
            rel.falhas[oc["id"]] = erros
        if oc["esperado"]["vai_ao_sindico"]:
            rel.sensiveis_total += 1
            if not r.vai_ao_sindico:
                rel.escapes.append(oc["id"])
        elif r.vai_ao_sindico:
            rel.falsos_alarmes.append(oc["id"])
    return rel


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rel = avaliar()
    print(f"Acertos (todos os campos): {rel.acertos}/{rel.total}  |  só as 30 base: {rel.base_acertos}/{rel.base_total} (meta ZELO-8: 25/30)")
    print(f"Sensíveis que foram ao síndico: {rel.sensiveis_total - len(rel.escapes)}/{rel.sensiveis_total}  | escapes: {rel.escapes or 'nenhum'}")
    print(f"Falsos alarmes (foram ao síndico sem precisar): {rel.falsos_alarmes or 'nenhum'}")
    for i, e in rel.falhas.items():
        print(f"  #{i}: " + "; ".join(e))
    return 0 if not rel.escapes else 1


if __name__ == "__main__":
    raise SystemExit(main())
