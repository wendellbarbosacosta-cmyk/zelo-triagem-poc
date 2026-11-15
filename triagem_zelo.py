import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from datetime import datetime

# 1. Configurações dos Bancos (PostgreSQL na 5435 e MongoDB na 27019)
PG_CONFIG = {
    "host": "localhost",
    "port": 5435,
    "database": "zelo_db",
    "user": "zelo_admin",
    "password": "zelo_password_123"
}

MONGO_URI = "mongodb://zelo_admin:zelo_password_123@localhost:27019/"

def elevar_urgencia(urgencia_atual, sla_atual):
    if urgencia_atual == 'Baixa':
        return 'Média', int(sla_atual / 2)
    elif urgencia_atual == 'Média':
        return 'Alta', int(sla_atual / 3)
    return 'Alta', sla_atual

def processar_ocorrencia(condominio, morador, mensagem_morador, codigo_ia, modificador_contexto=False, foto_url=None):
    try:
        # --- ETAPA 1: CONSULTA REGRAS RÍGIDAS NO POSTGRESQL ---
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_cursor = pg_conn.cursor(cursor_factory=RealDictCursor)

        pg_cursor.execute("SELECT * FROM regras_triagem WHERE codigo_regra = %s;", (codigo_ia,))
        regra = pg_cursor.fetchone()

        if not regra:
            print(f"[ERRO] Regra '{codigo_ia}' não encontrada.")
            return

        urgencia_final = regra['urgencia_base']
        sla_final = regra['sla_horas']
        alerta_modificador = "Não aplicado (Cenário padrão)"

        if modificador_contexto and regra['condicao_modificadora']:
            urgencia_final, sla_final = elevar_urgencia(urgencia_final, sla_final)
            alerta_modificador = f"ATIVO ({regra['condicao_modificadora']})"

        notificar_sindico = regra['is_sensivel'] or urgencia_final == 'Alta'

        # --- ETAPA 2: CRIA O DOCUMENTO DE HISTÓRICO NO MONGODB ---
        mongo_client = MongoClient(MONGO_URI)
        mongo_db = mongo_client["zelo_logs"]
        colecao_ocorrencias = mongo_db["ocorrencias"]

        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Monta a Linha do Tempo igual à Tela do protótipo
        historico_eventos = [
            {
                "data_hora": agora,
                "evento": f"Recebida pelo WhatsApp ({morador})",
                "mensagem_original": mensagem_morador
            },
            {
                "data_hora": agora,
                "evento": f"Classificada pela IA: {regra['categoria']} | Urgência {urgencia_final}",
                "modificador_aplicado": alerta_modificador
            },
            {
                "data_hora": agora,
                "evento": f"Encaminhada automaticamente para: {regra['responsavel']}"
            }
        ]

        if notificar_sindico:
            historico_eventos.append({
                "data_hora": agora,
                "evento": "🚨 ALERTA CRÍTICO enviado ao painel do Síndico"
            })

        documento_ocorrencia = {
            "condominio": condominio,
            "morador": morador,
            "status": "Em andamento",
            "classificacao": {
                "codigo_nbr": regra['codigo_regra'],
                "tipo": regra['tipo_ocorrencia'],
                "categoria": regra['categoria'],
                "urgencia_base": regra['urgencia_base'],
                "urgencia_final": urgencia_final,
                "sla_horas": sla_final,
                "responsavel": regra['responsavel'],
                "sensivel_sindico": notificar_sindico
            },
            "midia": {
                "foto_abertura": foto_url,
                "foto_resolucao": None
            },
            "historico_timeline": historico_eventos
        }

        resultado_mongo = colecao_ocorrencias.insert_one(documento_ocorrencia)

        # --- EXIBE RESUMO NO TERMINAL ---
        print("=" * 70)
        print(f"✅ OCORRÊNCIA REGISTRADA! ID MongoDB: {resultado_mongo.inserted_id}")
        print(f"🏢 {condominio} | 👤 {morador}")
        print(f"💬 \"{mensagem_morador}\"")
        print("-" * 70)
        print(f"🏷️  NBR 5674   : [{regra['codigo_regra']}] {regra['tipo_ocorrencia']}")
        print(f"⚡ Urgência   : {regra['urgencia_base']} ➡️  {urgencia_final.upper()} (SLA: {sla_final}h)")
        print(f"👷 Destino    : {regra['responsavel']}")
        print(f"🚨 Síndico?   : {'SIM (Notificado)' if notificar_sindico else 'NÃO (Silenciado)'}")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"Erro no processamento: {e}")
    finally:
        if 'pg_conn' in locals() and pg_conn:
            pg_cursor.close()
            pg_conn.close()
        if 'mongo_client' in locals() and mongo_client:
            mongo_client.close()

if __name__ == "__main__":
    print("\n🚀 INICIANDO ARQUITETURA HÍBRIDA ZELO (POSTGRESQL + MONGODB)\n")

    # Teste 1: A bomba da piscina
    processar_ocorrencia(
        condominio="Condomínio Jardim",
        morador="Morador Apto 21",
        mensagem_morador="A bomba da piscina está vazando de novo!",
        codigo_ia="4",
        modificador_contexto=False,
        foto_url="https://zelo.app/uploads/bomba_vazando_antes.jpg"
    )

    # Teste 2: Portão travado à noite
    processar_ocorrencia(
        condominio="Condomínio Aurora",
        morador="Morador Apto 303",
        mensagem_morador="O portão da garagem travou aberto e já são 23h30!",
        codigo_ia="16",
        modificador_contexto=True
    )