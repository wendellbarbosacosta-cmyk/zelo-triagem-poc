"""Parametros do motor. Tudo aqui e PREMISSA a validar com a PO / engenheiro de manutencao."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_TABELA_CSV = RAIZ / "data" / "tabela_triagem.csv"
CAMINHO_OCORRENCIAS = RAIZ / "data" / "ocorrencias_exemplo.json"

NIVEIS = ("Baixa", "Média", "Alta")

# As 16 categorias oficiais da tabela v3 (+ "Não é ocorrência")
CATEGORIAS_OFICIAIS = (
    "Elétrica", "Hidráulica", "Umidade", "Cobertura", "Estrutura", "Gás", "Elevador",
    "Incêndio", "Lazer", "Áreas verdes", "Acesso", "Segurança", "Convivência",
    "Limpeza", "Mobiliário", "Gestão", "Não é ocorrência",
)

# Horarios (PREMISSA): "noite" = 18h as 5h59; "depois das 22h" = 22h as 5h59 (silencio).
HORA_INICIO_NOITE = 18
HORA_FIM_NOITE = 6
HORA_INICIO_SILENCIO = 22

# Repeticao (regra especial 1): 3 ou mais reclamacoes do mesmo problema no mesmo lugar em 30 dias.
LIMITE_REPETICAO = 3

# Prazo de atendimento por urgencia (PROPOSTA, nao esta na tabela v3).
# O prototipo Lovable mostra "prazo: hoje, 11:00", entao algum prazo existe; falta definir os valores.
PRAZO_HORAS = {"imediato": 1, "Alta": 4, "Média": 24, "Baixa": 72}

# Prazos de garantia da construtora, em meses, contados do habite-se (regra especial 6).
# Fonte: Codigo Civil art. 618 (5 anos solidez) + NBR 17170. CONFIRMAR com o manual do proprietario.
PRAZOS_GARANTIA_MESES = {
    "estrutura": 60,
    "impermeabilizacao": 60,
    "instalacoes": 36,
    "revestimento_fachada": 60,
    "revestimento_interno": 12,
}

# Abaixo disso a IA "nao tem certeza" (regra especial 10: pergunta antes de classificar).
LIMIAR_CONFIANCA = 0.6

# Regra especial 10: botoes de esclarecimento. Resposta do botao ja classifica, sem chamar a IA.
ESCLARECIMENTOS = {
    "cadeira_salao": {
        "pergunta": "Sobre a cadeira do salão, o que aconteceu?",
        "botoes": ("Quebrada", "Fora do lugar", "Outro"),
        # None = nao classifica sozinho -> na duvida vai ao sindico
        "mapa": {"Quebrada": "M1", "Fora do lugar": "M12b", "Outro": None},
    },
}

RESPOSTA_RESERVAS = "Para reservar espaços, use o canal de reservas do condomínio."
RESPOSTA_PORTARIA = "Pedidos de tag, cadastro facial ou controle novo são feitos direto com a portaria."
