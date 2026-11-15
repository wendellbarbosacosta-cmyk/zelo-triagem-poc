"""TRAVA DE SEGURANCA (regra do sensivel): fica ACIMA da IA.

Se a ocorrencia envolve risco ou dinheiro, vai ao sindico, mesmo que a IA tenha indicado outro
responsavel. Gas, eletrica, estrutura, elevador, incendio e gastos. Na duvida, vai ao sindico.

Esta e uma rede de seguranca por palavras. Ela NAO substitui a coluna "Sensivel?" da tabela;
as duas se somam. A lista cresce com as mensagens reais do ZELO-7.
Texto e comparado em minusculas e sem acento.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return sem_acento.lower()


PADROES_RISCO: dict[str, list[str]] = {
    "gas": [r"\bgas\b"],
    "eletrica": [
        r"faisc", r"choque", r"fios? (exposto|descascado|pelado|solto)", r"curto[- ]?circuito",
        r"tomada.{0,20}(esquent|quente|derret)", r"cheiro de queimad", r"queimando",
        r"acabou a luz|sem luz|falta de luz|queda de energia|apagao", r"disjuntor", r"spda|para-?raio",
    ],
    "incendio": [
        r"fumaca(?! de cigarro)", r"incendio", r"\bfogo\b", r"\bchamas\b", r"extintor", r"hidrante",
        r"corta-?fogo", r"luz de emergencia", r"alarme de incendio",
    ],
    "estrutura": [
        r"rachadura", r"\bviga\b", r"\bpilar\b", r"desaband|desabou|desabar|desmoron|cedendo|afundando",
        r"ferro (aparecendo|exposto|enferrujad)|ferrugem|armadura|concreto (soltando|caindo)",
        r"caiu um pedaco|reboco|pastilh|desplac|fachada",
    ],
    "elevador": [
        r"elevador.{0,40}(parou|parado|travou|travad|preso|presa|tranco|barulho|caiu|despenc)",
        r"(parou|travou|preso|presa).{0,40}elevador", r"gente dentro", r"pessoa presa", r"cabine",
    ],
    "dinheiro": [
        r"r\$", r"orcamento", r"\bcompra(r|s|ndo)?\b", r"\bpagar\b|pagamento", r"\breais\b",
        r"prestacao de contas|cobranca",
    ],
    "pessoas": [
        r"ameac", r"agred|agress", r"\barma\b", r"assalto|roubo|furto", r"invad|invas|arromb",
        r"(estranho|desconhecido).{0,40}(tentando|portao|porta|pulando)",
        r"passando mal|desmaiou|machucou|acidente|ferido",
    ],
    "lazer_seguranca": [
        r"(grade|ralo|grelha).{0,20}piscina|piscina.{0,20}(ralo|grelha)|grade do ralo",
        r"(balanco|escorregador|gangorra|brinquedo|playground|parquinho).{0,40}(solt|quebrad|rachad|corrente|caindo)",
        r"(solt|quebrad|corrente).{0,40}(balanco|escorregador|gangorra|brinquedo)",
    ],
    "areas_verdes": [r"(galho|arvore).{0,60}(risco|cair|caindo|rachad|pendurad|tombou|caiu)"],
    # regra especial 3: reclamacao sobre funcionario vai sempre ao sindico, nunca para o reclamado
    "funcionario": [
        r"(porteiro|zelador|faxineir[ao]|funcionari[ao]|vigilante).{0,60}"
        r"(dormindo|dormiu|nao fez|nao veio|mal educad|desrespeit|ausente|sumiu|grosseir|abandon)"
    ],
}

CATEGORIA_DO_RISCO = {
    "gas": "Gás", "eletrica": "Elétrica", "incendio": "Incêndio", "estrutura": "Estrutura",
    "elevador": "Elevador", "dinheiro": "Gestão", "pessoas": "Segurança",
    "lazer_seguranca": "Lazer", "areas_verdes": "Áreas verdes", "funcionario": "Gestão",
}

_COMPILADOS = {k: [re.compile(p) for p in v] for k, v in PADROES_RISCO.items()}


@dataclass(frozen=True)
class RiscoDetectado:
    tipo: str
    trecho: str

    @property
    def categoria(self) -> str:
        return CATEGORIA_DO_RISCO[self.tipo]


def detectar_risco(mensagem: str) -> list[RiscoDetectado]:
    texto = normalizar(mensagem)
    achados: list[RiscoDetectado] = []
    for tipo, padroes in _COMPILADOS.items():
        for p in padroes:
            m = p.search(texto)
            if m:
                achados.append(RiscoDetectado(tipo, m.group(0)))
                break
    return achados
