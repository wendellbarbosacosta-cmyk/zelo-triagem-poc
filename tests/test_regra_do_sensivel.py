"""REGRA DO SENSIVEL (ZELO-9): a trava fica acima da IA e nenhum caso sensivel escapa."""
import unittest

from zelo import avaliacao
from zelo.classificador import ClassificadorFixo, ClassificadorPorRegras
from zelo.modelos import Classificacao, Contexto
from zelo.trava import detectar_risco
from zelo.triagem import triar, tabela_padrao

CASOS_SENSIVEIS_DA_TABELA = [r.codigo for r in tabela_padrao() if r.sensivel]


def t(codigo, msg="x", conf=1.0):
    return triar(msg, Classificacao(codigo, conf), Contexto(), tabela_padrao())


class TestTravaDoSensivel(unittest.TestCase):
    def test_todas_as_linhas_sensiveis_da_tabela_vao_ao_sindico(self):
        self.assertEqual(len(CASOS_SENSIVEIS_DA_TABELA), 21)
        for cod in CASOS_SENSIVEIS_DA_TABELA:
            self.assertTrue(t(cod).vai_ao_sindico, f"item {cod} escapou do síndico")

    def test_sensivel_vale_em_qualquer_contexto(self):
        for ctx in (Contexto(hora=3), Contexto(periodo_especial=True), Contexto(afetados="um_apto"), Contexto(chuva=True)):
            r = triar("x", Classificacao("25"), ctx, tabela_padrao())  # ralo de succao
            self.assertTrue(r.vai_ao_sindico)
            self.assertEqual(r.urgencia_final, "Alta")

    def test_ia_indicou_outro_responsavel_mas_tem_risco(self):
        """A IA erra e manda gas para 'Lampada queimada / Zelador': a trava corrige."""
        r = t("1", "Tô sentindo cheiro de gás na escada")
        self.assertTrue(r.vai_ao_sindico)
        self.assertEqual(r.responsavel, "Síndico")
        self.assertEqual(r.executor, "Zelador")  # quem executaria pela tabela fica registrado
        self.assertEqual(r.urgencia_final, "Alta")
        self.assertTrue(any("gas" in m for m in r.motivos_sindico))

    def test_cada_tipo_de_risco_da_regra(self):
        msgs = {
            "gas": "cheiro de gás no corredor", "eletrica": "tomada soltando faísca",
            "estrutura": "rachadura grande na laje", "elevador": "o elevador travou com gente",
            "incendio": "tem fumaça saindo do quadro", "dinheiro": "o orçamento ficou R$ 5.000",
            "pessoas": "o vizinho me ameaçou", "funcionario": "o porteiro tava dormindo de novo",
        }
        for tipo, msg in msgs.items():
            self.assertIn(tipo, [r.tipo for r in detectar_risco(msg)], msg)
            r = t("38", msg)  # IA indicou 'lixo' (Zelador, nao sensivel)
            self.assertTrue(r.vai_ao_sindico, msg)

    def test_acentos_e_maiusculas_nao_enganam(self):
        for msg in ("CHEIRO DE GAS!!!", "cheiro de gás", "Gás", "FAÍSCA na tomada", "faisca"):
            self.assertTrue(detectar_risco(msg), msg)

    def test_palavra_de_risco_nao_dispara_em_conversa_normal(self):
        for msg in ("lixo do lado do elevador tá fedendo", "a lâmpada queimou", "quero reservar o salão",
                    "tem duas cadeiras quebradas", "carro na minha vaga", "interfone não toca"):
            self.assertEqual(detectar_risco(msg), [], msg)

    def test_codigo_desconhecido_vai_ao_sindico_e_nao_some(self):
        """Bug original: codigo inexistente dava 'return' e a ocorrencia sumia."""
        r = t("9999", "qualquer coisa")
        self.assertEqual(r.status, "sindico_por_duvida")
        self.assertTrue(r.vai_ao_sindico)
        self.assertIn("codigo_desconhecido", r.motivos_sindico)

    def test_baixa_confianca_com_risco_vai_ao_sindico(self):
        r = t("1", "acho que tem cheiro de gás", conf=0.3)
        self.assertTrue(r.vai_ao_sindico)

    def test_baixa_confianca_em_item_sensivel_vai_ao_sindico(self):
        self.assertTrue(t("19", "hum, sei lá", conf=0.2).vai_ao_sindico)

    def test_baixa_confianca_sem_risco_pergunta_e_nao_vai_ao_sindico(self):
        r = t("M1", "alguma coisa com a cadeira", conf=0.3)
        self.assertEqual(r.status, "pergunta_ao_morador")
        self.assertFalse(r.vai_ao_sindico)

    def test_reclamacao_de_funcionario_vai_ao_sindico_nunca_ao_reclamado(self):
        r = t("42", "o porteiro dormiu de novo")
        self.assertEqual(r.responsavel, "Síndico")

    def test_risco_em_mensagem_de_reserva_nao_e_ignorado(self):
        r = t("NR4", "quero reservar o salão, mas tem cheiro de gás lá")
        self.assertTrue(r.vai_ao_sindico)


class TestOcorrenciasDeExemplo(unittest.TestCase):
    """Criterio 'Pronto quando' do ZELO-9 sobre as ocorrencias de exemplo do ZELO-7."""

    @classmethod
    def setUpClass(cls):
        cls.ocs = avaliacao.carregar_ocorrencias()

    def test_ha_49_ocorrencias_e_pelo_menos_5_sensiveis(self):
        self.assertEqual(len(self.ocs), 49)
        base = [o for o in self.ocs if o["grupo"] == "base"]
        self.assertEqual(len(base), 30)
        self.assertGreaterEqual(sum(o["esperado"]["vai_ao_sindico"] for o in base), 5)

    def test_nenhum_sensivel_escapa_com_o_classificador_de_regras(self):
        rel = avaliacao.avaliar(ClassificadorPorRegras())
        self.assertEqual(rel.escapes, [], "sensível que NÃO foi ao síndico")
        self.assertEqual(rel.falsos_alarmes, [], "foi ao síndico sem precisar")

    def test_meta_do_zelo_8_25_de_30(self):
        rel = avaliacao.avaliar(ClassificadorPorRegras())
        self.assertGreaterEqual(rel.base_acertos, 25, rel.falhas)

    def test_acerta_todos_os_campos(self):
        rel = avaliacao.avaliar(ClassificadorPorRegras())
        self.assertEqual(rel.falhas, {})

    def test_comparar_detecta_divergencia(self):
        """Garante que o 49/49 nao e um teste que sempre passa."""
        oc = next(o for o in self.ocs if o["id"] == 4)  # gas
        r = triar(oc["mensagem"], Classificacao("1"), Contexto(), tabela_padrao())  # ia erra: lampada
        self.assertTrue(r.vai_ao_sindico)  # a trava segura
        self.assertNotEqual(avaliacao.comparar(oc, r), [])  # mas o erro da IA aparece na comparacao (codigo/categoria/urgencia)

    def test_ia_errando_sempre_a_trava_segura_os_que_tem_palavra_de_risco(self):
        """Ataque: IA devolve SEMPRE o mesmo codigo errado e nao sensivel (lampada).

        A trava por palavras deve segurar todo sensivel cuja mensagem tem termo de risco.
        Os que nao tem termo (ex.: 'infiltracao com trinca', 'elevador com tranco') dependem da IA
        acertar a linha da tabela - esse e o limite conhecido e esta documentado no README.
        """
        sensiveis = [o for o in self.ocs if o["esperado"]["vai_ao_sindico"]]
        segurados, dependem_da_ia = [], []
        for o in sensiveis:
            r = triar(o["mensagem"], Classificacao("1"), avaliacao.contexto_de(o), tabela_padrao(), avaliacao.EQUIPES[o["equipe"]])
            (segurados if r.vai_ao_sindico else dependem_da_ia).append(o["id"])
            if detectar_risco(o["mensagem"]):
                self.assertTrue(r.vai_ao_sindico, f"#{o['id']} tem palavra de risco e escapou")
        print(f"\n[ataque] com a IA sempre errada: {len(segurados)}/{len(sensiveis)} sensíveis seguros só pela trava;"
              f" dependem da IA: {dependem_da_ia}")
        # os 3 que dependem da IA: #26 (infiltracao + trinca), #37 e #38 (garantia, vem do cadastro)
        self.assertEqual(dependem_da_ia, [26, 37, 38])
        self.assertGreaterEqual(len(segurados), 20)

    def test_ia_errando_codigo_aleatorio_trava_segura(self):
        """Mesmo ataque com varios codigos errados e nao sensiveis."""
        nao_sensiveis = [r.codigo for r in tabela_padrao() if not r.sensivel and not r.nao_e_ocorrencia]
        for o in self.ocs:
            if not o["esperado"]["vai_ao_sindico"]:
                continue
            if not detectar_risco(o["mensagem"]):
                continue
            for cod in nao_sensiveis:
                r = triar(o["mensagem"], Classificacao(cod), avaliacao.contexto_de(o), tabela_padrao())
                self.assertTrue(r.vai_ao_sindico, f"#{o['id']} com código errado {cod} escapou")


if __name__ == "__main__":
    unittest.main()
