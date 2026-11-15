"""Classificadores: dizem QUAL linha da tabela se aplica a uma mensagem + sinais extraidos do texto.

A interface e `classificar(mensagem) -> Classificacao`. Quem decide urgencia, sensivel e responsavel
NAO e o classificador: e o motor (triagem.py) olhando a tabela. Assim trocar a IA nao muda as regras.

- ClassificadorPorRegras: BASELINE de palavras-chave, so para testar o motor de ponta a ponta sem LLM.
  Foi escrito olhando as 49 mensagens de exemplo, entao a nota dele e OTIMISTA: nao mede a qualidade de uma IA.
- ClassificadorFixo: devolve sempre o mesmo codigo. Serve para simular a IA errando e provar a trava.
- Para o ZELO-8 (IA de verdade): implementar `classificar` chamando um LLM que devolve JSON
  {"codigo": "19", "confianca": 0.93, "sinais": ["cheiro_forte"]} e validar contra os mesmos exemplos.
"""
from __future__ import annotations

import re
from typing import Protocol

from .modelos import Classificacao
from .trava import normalizar


class Classificador(Protocol):
    def classificar(self, mensagem: str) -> Classificacao: ...


class ClassificadorFixo:
    def __init__(self, codigo: str | None, confianca: float = 1.0):
        self.codigo, self.confianca = codigo, confianca

    def classificar(self, mensagem: str) -> Classificacao:
        return Classificacao(self.codigo, self.confianca, motivo="fixo")


# sinal -> regex (texto normalizado). So importam para as linhas da tabela que usam esse sinal.
SINAIS = {
    "pessoa_presa": r"gente dentro|pessoas? (presa|dentro)|(preso|presa|presos).{0,30}elevador|elevador.{0,30}(preso|presa)",
    "cheiro_forte": r"fedendo|fedor|mau cheiro|cheiro forte|cheirando mal",
    "cheiro_queimado": r"cheiro de queimad",
    "com_trinca": r"trinca|rachadura|fissura",
    "portao_aberto": r"aberto|nao fecha|sem fechar",
    "bloqueando_saida": r"na frente d|bloquei|ninguem consegue sair|impedindo",
    "morador_preso_fora": r"preso.{0,12}fora|nao consigo entrar",
    "agressao_ou_ameaca": r"ameac|agred|agress|bateu|soco",
    "risco_acidente": r"choque|machuc|perigo|solta\b",
    "risco_corte": r"cortar|corte|estilha|caco|crianca",
    "risco_queda_farpa": r"farpa|vai cair|queda|bambo",
    "alarme_disparando": r"alarme.{0,20}(disparando|tocando|disparou)|disparando",
    "escada_ou_garagem": r"escada|garagem",
    "cheiro_gas": r"\bgas\b",
    "fio_ou_cheiro_queimado": r"\bfio\b|queimad|faisc",
    "mancha_pequena_isolada_aberta": r"pequen(a|inha).{0,30}(isolad|varanda|area aberta)|manchinha",
    "solto_circulacao": r"solto.{0,30}(corredor|hall|escada|garagem|passagem)|(corredor|hall|escada|garagem).{0,30}solto",
    "perto_eletrica_bomba": r"perto.{0,20}(quadro|eletric|bomba)|quadro de luz",
    "agua_cor_cheiro": r"agua (suja|barrenta|marrom|turva|com cheiro|esverdeada)",
    "dentro_apto": r"dentro do (meu )?ap",
    "aumentando": r"aumentou|aumentando|cresc|ontem nao tinha",
    "atingindo_eletrica_elevador_apto": r"(caindo|atingindo|molhando).{0,30}(quadro|elevador|apart|apto)|entrando no ap",
    "incidente": r"assalto|furto|roubo|invasao",
    "aumento_grande": r"dobro|disparou|triplic|aumentou muito",
    "calor_forte": r"calor|quente demais",
    "unico_banheiro": r"unico banheiro|so tem um banheiro",
    "pragas": r"\brato|barata|praga|inseto",
}
_SINAIS = {k: re.compile(v) for k, v in SINAIS.items()}
_UM_APTO = re.compile(r"\bmeu ap")
_NAO_UM_APTO = re.compile(r"vizinh|bloco|predio|todos|andar|condominio")


def extrair_sinais(texto_normalizado: str) -> frozenset[str]:
    s = {k for k, p in _SINAIS.items() if p.search(texto_normalizado)}
    if _UM_APTO.search(texto_normalizado) and not _NAO_UM_APTO.search(texto_normalizado):
        s.add("um_apto")
    return frozenset(s)


# (regex, codigo, confianca) - a ORDEM importa: o mais especifico vem primeiro.
REGRAS: list[tuple[str, str, float]] = [
    (r"reservar|reserva d", "NR4", 0.95),
    (r"(preciso|quero|solicito).{0,20}(tag|controle novo|cadastro facial)", "31e", 0.9),
    (r"cigarro", "37b", 0.9),
    (r"\bgas\b", "19", 0.95),
    (r"elevador.{0,40}(tranco|barulho|ruido)", "21", 0.9),
    (r"elevador.{0,40}(parou|parado|travou|preso|presa)|gente dentro|presa? no elevador", "20", 0.95),
    (r"fumaca|incendio|\bfogo\b|\bchamas\b", "22", 0.95),
    (r"extintor|hidrante|corta-?fogo|luz de emergencia|alarme", "23", 0.9),
    (r"faisc|choque|fios? (exposto|descascado)|tomada.{0,20}(esquent|quente)", "2", 0.95),
    (r"acabou a luz|sem luz|falta de luz|blecaute|apagao", "3", 0.9),
    (r"disjuntor", "4", 0.9),
    (r"spda|para-?raio", "5", 0.9),
    (r"cano (estourou|estourado)|estourou o cano|alagando|alagamento", "7", 0.9),
    (r"(bomba|filtro).{0,30}piscina|piscina.{0,30}(bomba|filtro)", "24b", 0.9),
    (r"(ralo|grelha|grade).{0,20}piscina|piscina.{0,20}(ralo|grelha)|grade do ralo", "25", 0.9),
    (r"piscina", "24", 0.85),
    (r"sem agua|falta de agua|bomba parada", "8", 0.9),
    (r"esgoto|ralo voltando|caixa de gordura", "9", 0.9),
    (r"(ralo|grelha).{0,20}entupid", "10", 0.9),
    (r"caixa d.?agua", "10b", 0.85),
    (r"conta de agua.{0,30}(alta|dobro)|vazamento oculto|ninguem acha (o )?vazamento|umidade sem origem", "10c", 0.85),
    (r"calha", "15", 0.9),
    (r"(telhado|laje).{0,30}(vaz|pingando)|goteira", "14", 0.85),
    (r"infiltra|mancha de umidade|bolha|tinta descascando|parede estufando|po branco|manchas? branca|eflorescen", "11", 0.85),
    (r"mofo|parede preta|parede verde|cheiro de guardado", "12", 0.9),
    (r"peitoril", "13", 0.85),
    (r"ferro (aparecendo|enferrujad)|ferrugem|armadura|concreto (soltando|caindo)", "16", 0.9),
    (r"(trinca|fissura|rachadura).{0,40}(janela|porta)|(janela|porta).{0,40}(trinca|fissura)", "16b", 0.8),
    (r"rachadura|trinca|fissura", "16", 0.9),
    (r"fachada|reboco|pastilh|azulejo caindo|desplac|revestimento.{0,15}caiu", "17", 0.9),
    (r"piso manchado", "18b", 0.9),
    (r"piso (oco|solto|estufado)|piso fazendo barulho", "18", 0.85),
    (r"(galho|arvore).{0,60}(risco|cair|caindo|rachad|pendurad|tombou|caiu)", "28", 0.9),
    (r"balanco|escorregador|gangorra|brinquedo|playground|parquinho", "26", 0.85),
    (r"jardim|\bpoda\b|grama", "27", 0.9),
    (r"(estranho|desconhecido).{0,40}(tentando|portao|porta|pulando|invad)|invad|arromb", "31", 0.9),
    (r"(facial|\btag\b|controle).{0,40}(nao (me )?reconhec|nao abre|nao funciona)|preso.{0,12}fora", "31b", 0.85),
    (r"porta d[oe] (bloco|entrada)|\bmola\b|fechadura", "31c", 0.8),
    (r"(porteiro|zelador|funcionario).{0,50}(dormindo|nao fez|mal educad|desrespeit|ausente)", "42", 0.9),
    (r"portao.{0,60}(nao fecha|travad|travou|sem fechar|aberto|lento|nao abre)", "29", 0.9),
    (r"interfone|portaria sem funcionar", "30", 0.9),
    (r"briga|ameac|agred|agress", "37c", 0.9),
    (r"som alt|barulho|musica alta", "32", 0.8),
    (r"(carro|veiculo|moto).{0,50}(vaga|estacion|parado)", "34", 0.9),
    (r"cachorro|gato|animal|\bcoco\b|xixi", "36", 0.85),
    (r"encomenda|entrega|correspondencia", "37", 0.85),
    (r"lixo|sujeira", "38", 0.9),
    (r"\brato|barata|praga|cupim|escorpiao", "39", 0.9),
    (r"(comprar|trocar|precisa(mos)? de|pedir|novas?).{0,40}(mesa|cadeira|movel|moveis|sofa|equipamento)|(mesas?|cadeiras?|moveis) novas?", "M13", 0.8),
    (r"prestacao de contas|conselho fiscal", "41", 0.85),
    (r"conta (de energia|de luz).{0,30}(alta|dobro)|conta alta", "41b", 0.85),
    (r"orcamento|r\$|\bcomprar\b|\bcompra\b|pagar|cobranca", "40", 0.85),
    (r"esteira|bicicleta ergometrica|academia|anilha", "M7", 0.85),
    (r"(vidro|espelho|tampo).{0,30}(trincad|quebrad|rachad)", "M8", 0.85),
    (r"(torneira|pia).{0,40}(salao|churrasqueira|copa)", "M2", 0.85),
    (r"churrasqueira", "M4", 0.8),
    (r"geladeira|freezer|fogao|cooktop", "M5", 0.85),
    (r"ar condicionado|ar-condicionado|ventilador", "M6", 0.85),
    (r"sauna", "M9", 0.85),
    (r"vaso|descarga|banheiro", "M3", 0.8),
    (r"sinuca|ping.?pong|pebolim", "M11", 0.85),
    (r"lixeira|bicicletario|caixa de correio|cortina|persiana", "M12", 0.8),
    (r"(cadeira|mesa|movel|moveis|banco).{0,50}(jogad|fora do lugar|desarrumad|bagunc)|salao (desarrumad|bagunc)", "M12b", 0.85),
    (r"(cadeira|mesa|banco).{0,30}(quebrad|bambo|solt)", "M1", 0.85),
    (r"vazamento|pingando|torneira", "6", 0.8),
    (r"\btv\b|\bsom\b|brinquedoteca|espaco gourmet", "M10", 0.8),
    (r"lampada", "1", 0.9),
]
_REGRAS = [(re.compile(p), c, conf) for p, c, conf in REGRAS]
_VAGAS = [(re.compile(r"cadeira|mesa"), "cadeira_salao")]


class ClassificadorPorRegras:
    def classificar(self, mensagem: str) -> Classificacao:
        t = normalizar(mensagem)
        sinais = extrair_sinais(t)
        for padrao, codigo, conf in _REGRAS:
            if padrao.search(t):
                return Classificacao(codigo, conf, sinais, motivo=f"regra:{padrao.pattern[:40]}")
        for padrao, chave in _VAGAS:
            if padrao.search(t):
                return Classificacao(None, 0.4, sinais, esclarecimento=chave, motivo="mensagem vaga")
        return Classificacao(None, 0.0, sinais, motivo="sem correspondencia")
