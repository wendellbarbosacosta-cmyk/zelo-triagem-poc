"""Zelo - motor de triagem de ocorrencias (POC).

Camadas (de baixo para cima):
  tabela   -> data/tabela_triagem.csv (fonte unica, espelho da tabela v3 do Linear ZELO-6)
  urgencia -> 3 camadas: base, contexto (sobe/desce), trava de seguranca
  trava    -> regra do sensivel: acima da IA, na duvida vai ao sindico
  triagem  -> junta tudo e devolve um ResultadoTriagem
"""

__version__ = "0.2.0"
TABELA_VERSAO = "v3"
