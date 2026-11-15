"""Regras especiais 6 e 7: garantia da construtora (habite-se + prazo por sistema)."""
from __future__ import annotations

from . import config
from .modelos import Regra


def possivel_garantia(regra: Regra, meses_desde_habitese: int | None) -> bool:
    """True se o sistema afetado ainda esta no prazo de garantia.

    Sem data de habite-se no cadastro nao da para afirmar: devolve False
    (o sindico ainda recebe a ocorrencia se ela for sensivel).
    """
    if not regra.sistema_garantia or meses_desde_habitese is None:
        return False
    return meses_desde_habitese < config.PRAZOS_GARANTIA_MESES[regra.sistema_garantia]
