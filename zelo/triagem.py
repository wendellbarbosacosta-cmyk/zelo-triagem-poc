"""Orquestra a triagem: IA indica a linha da tabela -> camadas de urgencia -> trava -> quem resolve."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from . import config
from .equipe import Equipe, resolver_executor
from .garantia import possivel_garantia
from .modelos import Classificacao, Contexto
from .tabela import Tabela
from .trava import detectar_risco
from .urgencia import calcular_urgencia

STATUS_TRIADO = "triado"
STATUS_NAO_OCORRENCIA = "nao_ocorrencia"
STATUS_PERGUNTA = "pergunta_ao_morador"
STATUS_SINDICO_DUVIDA = "sindico_por_duvida"

_tabela_cache: Tabela | None = None


def tabela_padrao() -> Tabela:
    global _tabela_cache
    if _tabela_cache is None:
        _tabela_cache = Tabela.from_csv()
    return _tabela_cache


@dataclass
class ResultadoTriagem:
    status: str
    mensagem: str
    codigo: str | None = None
    tipo_ocorrencia: str | None = None
    categoria: str | None = None
    urgencia_base: str | None = None
    urgencia_final: str | None = None
    imediato: bool = False
    prazo_horas: int | None = None
    responsavel: str | None = None  # quem responde pela ocorrencia (Sindico, Zelador, Portaria...)
    responsavel_detalhe: str | None = None
    executor: str | None = None  # quem executa conforme a tabela e o cadastro da equipe
    apoio: list[str] = field(default_factory=list)
    vai_ao_sindico: bool = False
    avisa_sindico: bool = False
    motivos_sindico: list[str] = field(default_factory=list)
    selo_garantia: bool = False
    aviso_preventiva: bool = False
    ajustes: list[str] = field(default_factory=list)
    resposta_automatica: str | None = None
    pergunta: str | None = None
    botoes: list[str] | None = None
    redirecionado_de: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _sindico_por_duvida(mensagem, classificacao, regra_cand, riscos, motivo) -> ResultadoTriagem:
    motivos = [motivo] + [f"palavra_de_risco:{r.tipo}:{r.trecho}" for r in riscos]
    if regra_cand is not None and regra_cand.sensivel:
        motivos.append("sensivel_tabela")
    urgencia = "Alta" if riscos else "Média"
    categoria = regra_cand.categoria if regra_cand else (riscos[0].categoria if riscos else None)
    return ResultadoTriagem(
        status=STATUS_SINDICO_DUVIDA,
        mensagem=mensagem,
        codigo=classificacao.codigo if regra_cand else None,
        tipo_ocorrencia=regra_cand.tipo_ocorrencia if regra_cand else None,
        categoria=categoria,
        urgencia_final=urgencia,
        prazo_horas=config.PRAZO_HORAS[urgencia],
        responsavel="Síndico",
        responsavel_detalhe="Síndico",
        vai_ao_sindico=True,
        avisa_sindico=True,
        motivos_sindico=motivos,
        ajustes=["na dúvida, vai ao síndico"],
    )


def triar(
    mensagem: str,
    classificacao: Classificacao,
    contexto: Contexto | None = None,
    tabela: Tabela | None = None,
    equipe: Equipe | None = None,
) -> ResultadoTriagem:
    contexto = contexto or Contexto()
    tabela = tabela or tabela_padrao()
    equipe = equipe or Equipe.padrao()

    riscos = detectar_risco(mensagem)
    ctx = contexto.com_sinais(classificacao.sinais)
    tokens = ctx.tokens()
    regra_cand = tabela.get(classificacao.codigo)

    # --- A IA nao sabe, errou o codigo ou esta com pouca confianca ---------------------------
    codigo_invalido = classificacao.codigo is not None and regra_cand is None
    em_duvida = classificacao.codigo is None or codigo_invalido or classificacao.confianca < config.LIMIAR_CONFIANCA
    if em_duvida:
        if codigo_invalido:
            return _sindico_por_duvida(mensagem, classificacao, None, riscos, "codigo_desconhecido")
        if riscos or (regra_cand is not None and regra_cand.sensivel):
            # regra especial 10 (excecao): palavra de risco nao pergunta, vai direto ao sindico
            return _sindico_por_duvida(mensagem, classificacao, regra_cand, riscos, "duvida_com_risco")
        esc = config.ESCLARECIMENTOS.get(classificacao.esclarecimento or "")
        return ResultadoTriagem(
            status=STATUS_PERGUNTA,
            mensagem=mensagem,
            pergunta=esc["pergunta"] if esc else "Pode me contar um pouco mais sobre o que aconteceu?",
            botoes=list(esc["botoes"]) if esc else None,
            ajustes=["mensagem vaga: pergunta antes de classificar"],
        )

    regra = regra_cand

    # --- Nao e ocorrencia (regra especial 4) -------------------------------------------------
    if regra.nao_e_ocorrencia:
        if riscos:
            return _sindico_por_duvida(mensagem, classificacao, regra, riscos, "risco_em_nao_ocorrencia")
        resposta = config.RESPOSTA_RESERVAS if regra.codigo == "NR4" else config.RESPOSTA_PORTARIA
        return ResultadoTriagem(
            status=STATUS_NAO_OCORRENCIA,
            mensagem=mensagem,
            codigo=regra.codigo,
            tipo_ocorrencia=regra.tipo_ocorrencia,
            categoria=regra.categoria,
            responsavel="Resposta automática",
            responsavel_detalhe=regra.quem_resolve,
            executor="Resposta automática",
            resposta_automatica=resposta,
        )

    # --- Camadas 1 e 2: urgencia-base + contexto ---------------------------------------------
    calc = calcular_urgencia(regra, tabela, tokens)
    regra_final = calc.regra
    final = calc.final
    ajustes = list(calc.ajustes)

    # --- Camada 3: trava de seguranca (regra do sensivel) ------------------------------------
    motivos: list[str] = []
    if regra_final.sensivel:
        motivos.append("sensivel_tabela")
    if calc.sensivel_contexto:
        motivos.append("sensivel_contexto")
    selo = possivel_garantia(regra_final, ctx.meses_desde_habitese)
    if selo:
        motivos.append("possivel_garantia")
        ajustes.append('selo "Possível garantia da construtora": síndico decide se abre chamado')
    ja_sensivel = regra_final.sensivel or calc.sensivel_contexto
    trava_sobrepos_ia = bool(riscos) and not ja_sensivel
    for r in riscos:
        motivos.append(f"palavra_de_risco:{r.tipo}:{r.trecho}")
    if trava_sobrepos_ia:
        ajustes.append("trava: palavra de risco em item não sensível -> síndico e urgência Alta")
        if final != "Alta":
            final = "Alta"
    vai = bool(motivos)

    # --- Quem resolve (cadastro da equipe, regra especial 9) ---------------------------------
    principal = regra_final.responsavel_principal
    exec_papel, exec_detalhe, fallback = resolver_executor(principal, equipe)
    if fallback:
        ajustes.append(f"{principal} não existe neste condomínio: segue para {exec_detalhe}")

    if not vai:
        responsavel, detalhe = exec_papel, exec_detalhe
    elif principal == "Síndico":
        responsavel, detalhe = "Síndico", "Síndico"
    elif regra_final.avisa_sindico and not trava_sobrepos_ia and not selo:
        responsavel, detalhe = exec_papel, exec_detalhe  # ex.: Portaria executa e avisa o sindico
    else:
        responsavel, detalhe = "Síndico", "Síndico"

    prazo = config.PRAZO_HORAS["imediato" if calc.imediato else final]
    return ResultadoTriagem(
        status=STATUS_TRIADO,
        mensagem=mensagem,
        codigo=regra_final.codigo,
        tipo_ocorrencia=regra_final.tipo_ocorrencia,
        categoria=regra_final.categoria,
        urgencia_base=calc.base,
        urgencia_final=final,
        imediato=calc.imediato,
        prazo_horas=prazo,
        responsavel=responsavel,
        responsavel_detalhe=detalhe,
        executor=exec_papel,
        apoio=list(regra_final.apoio),
        vai_ao_sindico=vai,
        avisa_sindico=vai or regra_final.avisa_sindico,
        motivos_sindico=motivos,
        selo_garantia=selo,
        aviso_preventiva=ctx.reclamacoes_30d >= config.LIMITE_REPETICAO,
        ajustes=ajustes,
        redirecionado_de=calc.redirecionado_de,
    )


def triar_resposta_botao(
    mensagem_original: str,
    esclarecimento: str,
    botao: str,
    contexto: Contexto | None = None,
    tabela: Tabela | None = None,
    equipe: Equipe | None = None,
) -> ResultadoTriagem:
    """Regra especial 10: a resposta do botao ja classifica, sem chamar a IA de novo."""
    esc = config.ESCLARECIMENTOS[esclarecimento]
    codigo = esc["mapa"].get(botao)
    if codigo is None:  # "Outro": nao da para classificar sozinho -> na duvida, sindico
        return _sindico_por_duvida(
            mensagem_original, Classificacao(None, 0.0), None, detectar_risco(mensagem_original), "botao_outro"
        )
    return triar(mensagem_original, Classificacao(codigo, 1.0, motivo=f"botao:{botao}"), contexto, tabela, equipe)
