"""As 3 camadas da urgencia.

1. Urgencia-base: vem da tabela (risco: pessoas, predio, uso - logica GUT).
2. Contexto sobe ou desce um nivel (horario, periodo especial, repeticao, quantas pessoas afeta...).
3. Trava de seguranca: risco a pessoas vai ao sindico (ver triagem.py / trava.py).

Funcoes puras: recebem a regra e os "tokens" de contexto, nao leem banco nem mensagem.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .modelos import Regra
from .tabela import Tabela

_IDX = {n: i for i, n in enumerate(config.NIVEIS)}


@dataclass
class CalculoUrgencia:
    regra: Regra  # regra final (depois de um eventual "vira=")
    redirecionado_de: str | None
    base: str
    final: str
    imediato: bool = False
    sensivel_contexto: bool = False
    ajustes: list[str] = field(default_factory=list)


def _aplica(m, tokens) -> bool:
    return all(c in tokens for c in m.condicoes)


def calcular_urgencia(regra: Regra, tabela: Tabela, tokens: frozenset[str]) -> CalculoUrgencia:
    ajustes: list[str] = []
    atual = regra
    origem = None
    for _ in range(3):  # "vira=" encadeado, com limite para nao entrar em loop
        alvo = next(
            (m for m in atual.modificadores if m.efeito == "vira" and _aplica(m, tokens) and m.valor != atual.codigo),
            None,
        )
        if alvo is None:
            break
        origem = origem or regra.codigo
        ajustes.append(f"vira item {alvo.valor} ({'+'.join(alvo.condicoes)}): {atual.codigo} -> {alvo.valor}")
        atual = tabela[alvo.valor]

    idx = _IDX[atual.urgencia_base]
    base = atual.urgencia_base
    delta = 0
    imediato = False
    sensivel_ctx = False
    for m in atual.modificadores:
        if not _aplica(m, tokens):
            continue
        cond = "+".join(m.condicoes)
        if m.efeito == "delta":
            delta += m.valor
            ajustes.append(f"{cond}: {'sobe' if m.valor > 0 else 'desce'} {abs(m.valor)}")
        elif m.efeito == "alta":
            idx = max(idx, _IDX["Alta"])
            ajustes.append(f"{cond}: vira Alta")
        elif m.efeito == "sensivel":
            sensivel_ctx = True
            ajustes.append(f"{cond}: vira sensivel")
        elif m.efeito == "imediato":
            imediato = True
            idx = max(idx, _IDX["Alta"])
            ajustes.append(f"{cond}: atendimento imediato")
    idx = max(0, min(len(config.NIVEIS) - 1, idx + delta))
    return CalculoUrgencia(
        regra=atual,
        redirecionado_de=origem,
        base=base,
        final=config.NIVEIS[idx],
        imediato=imediato,
        sensivel_contexto=sensivel_ctx,
        ajustes=ajustes,
    )
