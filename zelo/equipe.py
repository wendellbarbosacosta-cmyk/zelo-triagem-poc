"""Regra especial 9: cada condominio tem uma equipe diferente (cadastro do condominio)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Equipe:
    zelador: bool = True
    faxina: bool = True
    portaria_presencial: bool = True
    portaria_remota: bool = False
    manutencao_terceirizada: bool = True

    @classmethod
    def padrao(cls) -> "Equipe":
        return cls()

    @classmethod
    def so_portaria_remota(cls) -> "Equipe":
        return cls(portaria_presencial=False, portaria_remota=True)


def _disponivel(papel: str, e: Equipe) -> bool:
    if papel == "Zelador":
        return e.zelador
    if papel == "Manutenção":
        return e.manutencao_terceirizada
    if papel == "Portaria":
        return e.portaria_presencial or e.portaria_remota
    return True  # Engenharia (acionada pelo sindico), Sindico e Resposta automatica sempre existem


def resolver_executor(papel: str, e: Equipe) -> tuple[str, str, bool]:
    """Devolve (papel, detalhe, usou_fallback).

    Se o responsavel da tabela nao existe no predio, segue a ordem:
    zelador -> manutencao terceirizada -> sindico e portaria presencial -> portaria remota -> sindico.
    """
    if _disponivel(papel, e):
        if papel == "Portaria":
            return papel, ("Portaria presencial" if e.portaria_presencial else "Portaria remota"), False
        return papel, papel, False
    if e.zelador:
        return "Zelador", "Zelador", True
    if e.manutencao_terceirizada:
        return "Manutenção", "Manutenção terceirizada", True
    if e.portaria_presencial:
        return "Portaria", "Portaria presencial (avisa o síndico)", True
    if e.portaria_remota:
        return "Portaria", "Portaria remota", True
    return "Síndico", "Síndico", True
