# 🏢 Zelo — Motor de Triagem Inteligente

Protótipo funcional da arquitetura de dados e back-end do **Zelo**, aplicando **Rule-Driven AI** (IA guiada por regras da **ABNT NBR 5674** e **Matriz GUT**) com bancos de dados híbridos (**PostgreSQL + MongoDB**).

## 🏗️ Arquitetura do Sistema
- **PostgreSQL (`porta 5435`)**: Guarda a matriz imutável de regras de triagem, SLAs, responsáveis e a trava de segurança do síndico (*Regra do Sensível*).
- **MongoDB (`porta 27019`)**: Armazena os documentos dinâmicos de ocorrências, fotos de abertura/resolução e a linha do tempo (`historico_timeline`).
- **Motor Python (`triagem_zelo.py`)**: Cruza a classificação da IA com o banco relacional, aplica modificadores de contexto (horário, férias, repetição) e registra o histórico no NoSQL.

## 🚀 Como rodar na sua máquina em 3 passos

### Passo 1: Subir os Bancos de Dados no Docker
Certifique-se de estar com o Docker Desktop aberto e execute no terminal, na raiz do projeto:

```bash
docker compose up -d
```
*(O arquivo `init.sql` já cria e popula automaticamente a tabela da NBR 5674 no PostgreSQL assim que o contêiner sobe pela primeira vez!)*

### Passo 2: Instalar as dependências do Python
Instale os drivers de conexão com o PostgreSQL e o MongoDB:

```bash
python -m pip install -r requirements.txt
```

### Passo 3: Executar a simulação de triagem
Rode o script principal para simular a chegada de mensagens do WhatsApp, o cálculo de urgência/SLA e a gravação nos bancos:

```bash
python triagem_zelo.py
```

## 🔍 Como visualizar os dados nas interfaces gráficas

### 🐘 No pgAdmin 4 (PostgreSQL)
- **Host name/address**: `localhost`
- **Port**: `5435`
- **Maintenance database**: `zelo_db`
- **Username**: `zelo_admin`
- **Password**: `zelo_password_123`

### 🍃 No MongoDB Compass (NoSQL)
- **URI de Conexão**: `mongodb://zelo_admin:zelo_password_123@localhost:27019/`
- **Banco de Dados**: `zelo_logs`
- **Coleção**: `ocorrencias`

## 📂 Estrutura de Arquivos
- `docker-compose.yml`: Orquestração dos contêineres PostgreSQL 15 Alpine e MongoDB 7.0 em rede isolada.
- `init.sql`: Carga inicial automática das regras de negócio da NBR 5674 e Matriz GUT.
- `triagem_zelo.py`: Script de integração híbrida e aplicação das 3 camadas de urgência.
- `requirements.txt`: Dependências do ambiente Python (`psycopg2-binary` e `pymongo`).