"""Integracao com PostgreSQL + MongoDB reais (docker compose). So roda com ZELO_INTEGRACAO=1.

    docker compose up -d
    ZELO_INTEGRACAO=1 python -m unittest tests.test_integracao -v
"""
import os
import unittest

from zelo.tabela import Tabela

RODAR = os.environ.get("ZELO_INTEGRACAO") == "1"


@unittest.skipUnless(RODAR, "defina ZELO_INTEGRACAO=1 com os bancos no ar")
class TestIntegracao(unittest.TestCase):
    def test_tabela_no_postgres_e_identica_ao_csv(self):
        from zelo import persistencia

        csv_t = Tabela.from_csv()
        conn = persistencia.conectar_pg()
        try:
            self.assertEqual(persistencia.semear_tabela(conn, csv_t), len(csv_t))
            pg_t = persistencia.tabela_do_postgres(conn)
        finally:
            conn.close()
        self.assertEqual([r.codigo for r in pg_t], [r.codigo for r in csv_t])
        for a, b in zip(csv_t, pg_t):
            self.assertEqual(a, b, a.codigo)

    def test_motor_da_o_mesmo_resultado_com_tabela_do_postgres(self):
        from zelo import avaliacao, persistencia

        conn = persistencia.conectar_pg()
        try:
            persistencia.semear_tabela(conn, Tabela.from_csv())
            pg_t = persistencia.tabela_do_postgres(conn)
        finally:
            conn.close()
        rel = avaliacao.avaliar(tabela=pg_t)
        self.assertEqual(rel.escapes, [])
        self.assertEqual(rel.falhas, {})

    def test_grava_ocorrencia_no_mongo_com_data_nativa(self):
        from datetime import datetime
        from pymongo import MongoClient
        from zelo import persistencia
        from zelo.classificador import ClassificadorPorRegras
        from zelo.modelos import Contexto
        from zelo.triagem import triar

        msg = "Tô sentindo um cheiro forte de gás na escada do bloco B"
        r = triar(msg, ClassificadorPorRegras().classificar(msg), Contexto(hora=19))
        _id = persistencia.salvar_ocorrencia(r, "Condomínio Teste", "Morador Teste")
        cli = MongoClient(persistencia.MONGO_URI)
        try:
            doc = cli["zelo_logs"]["ocorrencias"].find_one({"_id": _id})
            self.assertTrue(doc["classificacao"]["vai_ao_sindico"])
            self.assertIsInstance(doc["criada_em"], datetime)
            self.assertEqual(doc["classificacao"]["codigo_tabela"], "19")
            cli["zelo_logs"]["ocorrencias"].delete_one({"_id": _id})
        finally:
            cli.close()


if __name__ == "__main__":
    unittest.main()
