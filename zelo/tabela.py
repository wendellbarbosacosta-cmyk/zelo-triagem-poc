"""Carrega e valida a tabela de triagem (fonte unica: data/tabela_triagem.csv)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Iterator

from . import config
from .modelos import Regra, parse_modificadores, interpretar_responsavel

COLUNAS = (
    "codigo", "tipo_ocorrencia", "categoria", "urgencia_base", "o_que_sobe_ou_desce",
    "modificadores", "quem_resolve", "sensivel", "sistema_garantia", "origem",
)


def regra_de_linha(d: dict) -> Regra:
    urg = (d.get("urgencia_base") or "").strip()
    return Regra(
        codigo=d["codigo"].strip(),
        tipo_ocorrencia=d["tipo_ocorrencia"].strip(),
        categoria=d["categoria"].strip(),
        urgencia_base=None if urg in ("", "—", "-") else urg,
        o_que_sobe_ou_desce=(d.get("o_que_sobe_ou_desce") or "").strip(),
        modificadores=parse_modificadores(d.get("modificadores") or ""),
        quem_resolve=d["quem_resolve"].strip(),
        sensivel=(d["sensivel"].strip().lower() in ("sim", "true", "t", "1")),
        sistema_garantia=(d.get("sistema_garantia") or "").strip() or None,
        origem=(d.get("origem") or "tabela_v3").strip(),
    )


class Tabela:
    def __init__(self, regras: Iterable[Regra]):
        self._regras = {}
        for r in regras:
            if r.codigo in self._regras:
                raise ValueError(f"codigo duplicado na tabela: {r.codigo}")
            self._regras[r.codigo] = r

    @classmethod
    def from_csv(cls, caminho: Path | str = config.CAMINHO_TABELA_CSV) -> "Tabela":
        with open(caminho, newline="", encoding="utf-8-sig") as f:
            return cls(regra_de_linha(l) for l in csv.DictReader(f))

    @classmethod
    def from_linhas(cls, linhas: Iterable[dict]) -> "Tabela":
        return cls(regra_de_linha(l) for l in linhas)

    def get(self, codigo: str | None) -> Regra | None:
        return self._regras.get(codigo) if codigo is not None else None

    def __getitem__(self, codigo: str) -> Regra:
        return self._regras[codigo]

    def __contains__(self, codigo) -> bool:
        return codigo in self._regras

    def __iter__(self) -> Iterator[Regra]:
        return iter(self._regras.values())

    def __len__(self) -> int:
        return len(self._regras)

    def validar(self) -> list[str]:
        """Devolve a lista de problemas (vazia = tabela ok)."""
        erros: list[str] = []
        for r in self:
            if r.categoria not in config.CATEGORIAS_OFICIAIS:
                erros.append(f"[{r.codigo}] categoria fora da lista oficial: {r.categoria!r}")
            if r.urgencia_base is not None and r.urgencia_base not in config.NIVEIS:
                erros.append(f"[{r.codigo}] urgencia invalida: {r.urgencia_base!r}")
            try:
                interpretar_responsavel(r.quem_resolve)
            except ValueError as e:
                erros.append(f"[{r.codigo}] {e}")
            if r.sistema_garantia and r.sistema_garantia not in config.PRAZOS_GARANTIA_MESES:
                erros.append(f"[{r.codigo}] sistema_garantia sem prazo: {r.sistema_garantia!r}")
            for m in r.modificadores:
                if m.efeito == "vira" and m.valor not in self._regras:
                    erros.append(f"[{r.codigo}] vira=<codigo inexistente {m.valor!r}>")
            if r.nao_e_ocorrencia and r.sensivel:
                erros.append(f"[{r.codigo}] nao e ocorrencia mas esta marcada como sensivel")
        return erros
