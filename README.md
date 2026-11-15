# Zelo — Motor de Triagem Inteligente (v3)

Motor determinístico de triagem de ocorrências condominiais alinhado à especificação do Linear (**ZELO-6**, **ZELO-7** e **ZELO-9**), aplicando **ABNT NBR 5674** + lógica **Matriz GUT** com arquitetura de dados híbrida opcional (**PostgreSQL + MongoDB**).

## O que este repositório entrega

1. **Tabela única de triagem (`data/tabela_triagem.csv`) — ZELO-6**
   - Fonte única de verdade com as **70 linhas da tabela v3** + regra especial de reservas (`NR4`, total de **71 regras**), **16 categorias oficiais** (+ `"Não é ocorrência"`) e **21 casos sensíveis**.
   - O arquivo `init.sql` é gerado automaticamente a partir do CSV (`python -m zelo.gerar_sql`), evitando divergência entre código e banco.
2. **Trava de segurança do sensível (`zelo/trava.py` e `zelo/triagem.py`) — ZELO-9**
   - Camada **acima da IA**: detecta palavras de risco (gás, elétrica, estrutura, elevador, incêndio, dinheiro/gastos, segurança/pessoas, lazer/risco, árvores e reclamações sobre funcionários).
   - **Na dúvida, vai ao síndico**: código desconhecido, confiança abaixo de `0.6` (`LIMIAR_CONFIANCA`) ou risco em mensagens vagas/reservas vão direto ao síndico — nenhuma ocorrência é descartada silenciosamente.
   - Regra especial 10: mensagens vagas sem palavra de risco disparam pergunta com botões antes de classificar.
3. **Urgência em 3 camadas e Regras Especiais (`zelo/urgencia.py`, `zelo/equipe.py`, `zelo/garantia.py`)**
   - **Camada 1 (Base):** vem da tabela (pessoas > prédio > uso).
   - **Camada 2 (Contexto):** sobe ou desce 1 nível conforme horário (`18h–6h` noite / `22h–6h` silêncio), período especial (férias/temporada), período de chuva, evento reservado em 48h, número de afetados (`um_apto` desce), repetição (`>= 3` em 30 dias gera aviso de preventiva) e redirecionamentos (`vira=`, `imediato`, `alta,sensivel`).
   - **Camada 3 (Trava):** risco ou sensível sempre vai ao síndico.
   - **Equipe (`zelo/equipe.py`):** fallback automático conforme cadastro do prédio (zelador -> manutenção terceirizada -> portaria presencial -> portaria remota -> síndico).
   - **Garantia da construtora (`zelo/garantia.py`):** aplica o selo `"Possível garantia da construtora"` quando o sistema afetado está dentro do prazo a partir do habite-se.
4. **Conjunto de avaliação com 49 ocorrências (`data/ocorrencias_exemplo.json` e `zelo/avaliacao.py`) — ZELO-7**
   - Contém as **30 ocorrências base** (15 sensíveis + 15 não sensíveis) e **19 casos extras** de regras especiais (garantia, repetição, linguagem leiga, portaria remota, mobiliário, mensagem vaga).
   - Inclui `ClassificadorPorRegras` apenas como baseline para exercitar o motor de ponta a ponta sem depender de LLM; no **ZELO-8**, basta plugar um LLM que implemente `classificar(mensagem) -> Classificacao`.

## Estrutura de Arquivos

- `data/tabela_triagem.csv`: fonte única da tabela de triagem v3 (`71` regras).
- `data/ocorrencias_exemplo.json`: `49` ocorrências de exemplo (`30` base + `19` extras).
- `zelo/config.py`: categorias oficiais, horários, limiar de confiança, SLA proposto e prazos de garantia.
- `zelo/modelos.py`: `Regra`, `Modificador`, `Contexto`, `Classificacao` e parser de responsáveis/modificadores.
- `zelo/tabela.py`: carga e validação do CSV.
- `zelo/trava.py`: detecção de palavras de risco independente da IA.
- `zelo/urgencia.py`: cálculo puro das camadas 1 e 2 (`sobe`, `desce`, `imediato`, `vira=`).
- `zelo/equipe.py`: regra especial 9 (fallback por equipe do condomínio).
- `zelo/garantia.py`: regras especiais 6 e 7 (prazo de garantia a partir do habite-se).
- `zelo/triagem.py`: orquestrador principal (`triar`, `triar_resposta_botao`).
- `zelo/classificador.py`: interface `Classificador`, `ClassificadorPorRegras` (baseline) e `ClassificadorFixo` (simulação de falha da IA).
- `zelo/avaliacao.py`: executor da avaliação nas 49 ocorrências.
- `zelo/persistencia.py` e `zelo/gerar_sql.py`: integração opcional com PostgreSQL + MongoDB e gerador do `init.sql`.
- `triagem_zelo.py`: CLI de demonstração, avaliação, seed e persistência.
- `tests/`: suíte de testes unitários (`test_tabela.py`, `test_urgencia_e_regras.py`, `test_regra_do_sensivel.py`) e integração (`test_integracao.py`).

## Como rodar (sem precisar de banco de dados)

O núcleo do motor e os testes unitários usam apenas a biblioteca padrão do Python 3.12+:

```bash
# 1. Demonstração interativa de 5 cenários
python triagem_zelo.py

# 2. Avaliar as 49 ocorrências de exemplo (ZELO-7 / ZELO-9)
python triagem_zelo.py --avaliar

# 3. Testar uma mensagem específica com contexto
python triagem_zelo.py "O portão da garagem travou aberto" --hora 23

# 4. Rodar todos os testes unitários
python -m unittest discover -s tests -t . -v

# 5. Conferir se o init.sql está sincronizado com o CSV
python -m zelo.gerar_sql --check
```

## Como rodar com PostgreSQL + MongoDB (Docker)

1. Copie `.env.example` para `.env` se quiser customizar credenciais/portas.
2. Suba os bancos e instale os drivers:

```bash
docker compose up -d
python -m pip install -r requirements.txt
```

3. Popule a tabela no PostgreSQL a partir do CSV e teste com persistência no MongoDB:

```bash
python triagem_zelo.py --seed
python triagem_zelo.py --persistir "Tô sentindo um cheiro forte de gás na escada" --hora 19
ZELO_INTEGRACAO=1 python -m unittest tests.test_integracao -v
```

## Premissas em aberto (para validar com PO / Engenharia)

Os itens abaixo estão centralizados em `zelo/config.py` e precisam de validação com a PO (Rayssa) e engenheiro de manutenção predial:

- **SLA por urgência (`PRAZO_HORAS`):** proposto como `imediato = 1h`, `Alta = 4h`, `Média = 24h`, `Baixa = 72h` (a tabela v3 não define horas exatas, embora o protótipo exiba prazos).
- **Janela noturna (`HORA_INICIO_NOITE`, `HORA_FIM_NOITE`):** adotado `18h às 6h` para noite e `22h às 6h` (`HORA_INICIO_SILENCIO`) para barulho após as 22h.
- **Prazos de garantia (`PRAZOS_GARANTIA_MESES`):** adotados `60` meses (estrutura, impermeabilização, revestimento de fachada), `36` meses (instalações) e `12` meses (revestimento interno) conforme Código Civil art. 618 e NBR 17170 — confirmar com o manual do proprietário de cada condomínio.
- **Limitação conhecida da trava por palavras:** casos sensíveis sem palavras explícitas de risco (por exemplo, `"infiltração no teto"` seguida de contexto estrutural sutil ou garantia pelo cadastro) ainda dependem de a IA/contexto identificar corretamente a linha da tabela ou a data de habite-se; nos testes de ataque em que a IA erra propositalmente, a trava por palavras garante `20/23` casos sensíveis sozinha e os `3` restantes dependem do contexto/classificação.
