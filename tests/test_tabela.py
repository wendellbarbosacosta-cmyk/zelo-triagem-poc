"""Testes da tabela (fonte unica) e do init.sql gerado."""
import unittest

from zelo import config
from zelo.gerar_sql import gerar
from zelo.tabela import Tabela
from zelo.modelos import parse_modificadores, interpretar_responsavel
from zelo.gerar_sql import CAMINHO_INIT_SQL


class TestTabela(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Tabela.from_csv()

    def test_sem_problemas_de_validacao(self):
        self.assertEqual(self.t.validar(), [])

    def test_cobre_as_70_linhas_da_v3(self):
        v3 = [r for r in self.t if r.origem == "tabela_v3"]
        self.assertEqual(len(v3), 70)
        self.assertGreaterEqual(len(v3), 20)  # meta do ZELO-6

    def test_21_sensiveis_da_v3(self):
        self.assertEqual(sum(r.sensivel for r in self.t if r.origem == "tabela_v3"), 21)

    def test_categorias_oficiais(self):
        for r in self.t:
            self.assertIn(r.categoria, config.CATEGORIAS_OFICIAIS, r.codigo)

    def test_casos_sensiveis_do_linear_cobertos(self):
        """Gas, eletrica, estrutura, elevador, incendio e gastos tem linha sensivel."""
        cats = {r.categoria for r in self.t if r.sensivel}
        for c in ("Gás", "Elétrica", "Estrutura", "Elevador", "Incêndio", "Gestão"):
            self.assertIn(c, cats)

    def test_exemplos_do_linear(self):
        # piscina baixa: Baixa; ralo de succao: Alta e sensivel sempre
        self.assertEqual(self.t["24"].urgencia_base, "Baixa")
        self.assertTrue(self.t["25"].sensivel)
        self.assertEqual(self.t["25"].urgencia_base, "Alta")
        self.assertTrue(self.t["19"].sensivel)  # gas

    def test_codigos_conferem_com_a_v3(self):
        """Regressao do bug original: o POC antigo usava numeracao de outra versao."""
        esperado = {"19": "Cheiro de gás", "16": "Trinca", "11": "Infiltração", "23": "Extintor",
                    "25": "Ralo de sucção", "20": "Elevador parado", "5": "Para-raios", "29": "Portão"}
        for cod, trecho in esperado.items():
            self.assertIn(trecho.lower(), self.t[cod].tipo_ocorrencia.lower(), cod)

    def test_parse_modificadores(self):
        m = parse_modificadores("noite&escada_ou_garagem:+1;agressao_ou_ameaca:alta,sensivel")
        self.assertEqual(len(m), 3)
        self.assertEqual(m[0].condicoes, ("noite", "escada_ou_garagem"))
        with self.assertRaises(ValueError):
            parse_modificadores("sem_dois_pontos")
        with self.assertRaises(ValueError):
            parse_modificadores("x:efeito_inexistente")

    def test_interpretar_responsavel(self):
        self.assertEqual(interpretar_responsavel("Síndico (+ eletricista)"), ("Síndico", ("Eletricista",), False))
        p, apoio, avisa = interpretar_responsavel("Portaria (e avisa o síndico)")
        self.assertEqual((p, avisa), ("Portaria", True))
        p, apoio, _ = interpretar_responsavel("Zelador (limpa) + portaria (avisa o tutor)")
        self.assertEqual((p, apoio), ("Zelador", ("Portaria",)))

    def test_init_sql_em_dia_com_o_csv(self):
        atual = CAMINHO_INIT_SQL.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(atual, gerar(self.t), "rode: python -m zelo.gerar_sql")


if __name__ == "__main__":
    unittest.main()
