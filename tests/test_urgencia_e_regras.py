"""As 3 camadas da urgencia e as regras especiais."""
import unittest

from zelo.classificador import ClassificadorFixo
from zelo.equipe import Equipe, resolver_executor
from zelo.modelos import Classificacao, Contexto
from zelo.triagem import triar, triar_resposta_botao, tabela_padrao


def t(codigo, ctx=None, msg="x", sinais=(), equipe=None, conf=1.0):
    return triar(msg, Classificacao(codigo, conf, frozenset(sinais)), ctx or Contexto(), tabela_padrao(), equipe)


class TestUrgencia(unittest.TestCase):
    # --- Camada 1: base
    def test_base_vem_da_tabela(self):
        self.assertEqual(t("1").urgencia_final, "Baixa")
        self.assertEqual(t("7").urgencia_final, "Alta")

    # --- Camada 2: contexto
    def test_piscina_baixa_no_dia_a_dia_media_nas_ferias(self):  # pergunta da Dani
        self.assertEqual(t("24", Contexto(periodo_especial=False)).urgencia_final, "Baixa")
        self.assertEqual(t("24", Contexto(periodo_especial=True)).urgencia_final, "Média")

    def test_portao_quebrado_a_noite_sobe(self):
        self.assertEqual(t("29", Contexto(hora=14)).urgencia_final, "Média")
        self.assertEqual(t("29", Contexto(hora=23)).urgencia_final, "Alta")

    def test_noite_comeca_as_18h(self):
        self.assertEqual(t("31c", Contexto(hora=17)).urgencia_final, "Média")  # porta do bloco sem fechar
        self.assertEqual(t("31c", Contexto(hora=18)).urgencia_final, "Alta")
        self.assertEqual(t("31c", Contexto(hora=5)).urgencia_final, "Alta")
        self.assertEqual(t("31c", Contexto(hora=6)).urgencia_final, "Média")
        # lampada: so sobe se for escada/garagem E for noite
        self.assertEqual(t("1", Contexto(hora=20), sinais=["escada_ou_garagem"]).urgencia_final, "Média")
        self.assertEqual(t("1", Contexto(hora=10), sinais=["escada_ou_garagem"]).urgencia_final, "Baixa")
        self.assertEqual(t("1", Contexto(hora=20)).urgencia_final, "Baixa")

    def test_horario_de_fronteira(self):
        self.assertEqual(t("32", Contexto(hora=21)).urgencia_final, "Baixa")  # antes das 22h
        self.assertEqual(t("32", Contexto(hora=22)).urgencia_final, "Média")
        self.assertEqual(t("32", Contexto(hora=5)).urgencia_final, "Média")
        self.assertEqual(t("32", Contexto(hora=6)).urgencia_final, "Baixa")

    def test_um_apartamento_desce_um_nivel(self):
        self.assertEqual(t("8", Contexto(afetados="um_apto")).urgencia_final, "Média")
        self.assertEqual(t("8", Contexto(afetados="bloco")).urgencia_final, "Alta")
        self.assertEqual(t("30", Contexto(afetados="um_apto")).urgencia_final, "Baixa")

    def test_desce_so_um_nivel_e_nunca_abaixo_de_baixa(self):
        self.assertEqual(t("30", Contexto(afetados="um_apto")).urgencia_final, "Baixa")
        self.assertEqual(t("12", sinais=["mancha_pequena_isolada_aberta"]).urgencia_final, "Média")

    def test_repeticao_3_ou_mais(self):
        self.assertEqual(t("36", Contexto(reclamacoes_30d=2)).urgencia_final, "Baixa")
        r = t("36", Contexto(reclamacoes_30d=3))
        self.assertEqual(r.urgencia_final, "Média")
        self.assertTrue(r.aviso_preventiva)  # regra especial 1
        self.assertFalse(t("36", Contexto(reclamacoes_30d=2)).aviso_preventiva)

    def test_sobe_no_maximo_ate_alta(self):
        r = t("29", Contexto(hora=23), sinais=["portao_aberto"])  # dois "sobe" em cima de Média
        self.assertEqual(r.urgencia_final, "Alta")

    def test_chuva_sobe_cobertura(self):
        self.assertEqual(t("15", Contexto(chuva=False)).urgencia_final, "Média")
        self.assertEqual(t("15", Contexto(chuva=True)).urgencia_final, "Alta")

    def test_evento_reservado_sobe_mobiliario(self):
        self.assertEqual(t("M2", Contexto(evento_reservado_48h=True)).urgencia_final, "Alta")
        self.assertEqual(t("M1", Contexto(evento_reservado_48h=True)).urgencia_final, "Média")

    def test_pessoa_presa_no_elevador_e_imediato(self):
        r = t("20", sinais=["pessoa_presa"])
        self.assertTrue(r.imediato)
        self.assertEqual(r.prazo_horas, 1)
        self.assertFalse(t("20").imediato)

    def test_agressao_vira_alta_e_sensivel(self):
        r = t("37c", sinais=["agressao_ou_ameaca"])
        self.assertEqual(r.urgencia_final, "Alta")
        self.assertTrue(r.vai_ao_sindico)
        self.assertFalse(t("37c").vai_ao_sindico)  # briga sem agressao: so avisa
        self.assertTrue(t("37c").avisa_sindico)

    def test_vira_outro_item(self):
        r = t("11", sinais=["com_trinca"])  # infiltracao com trinca vira estrutura
        self.assertEqual((r.codigo, r.redirecionado_de, r.categoria), ("16", "11", "Estrutura"))
        r = t("M5", sinais=["cheiro_gas"])  # fogao com cheiro de gas vira item 19
        self.assertEqual((r.codigo, r.vai_ao_sindico), ("19", True))
        r = t("M9", sinais=["fio_ou_cheiro_queimado"])  # sauna com fio vira item 2
        self.assertEqual(r.codigo, "2")


class TestRegrasEspeciais(unittest.TestCase):
    def test_garantia_dentro_do_prazo_ganha_selo_e_vai_ao_sindico(self):
        r = t("16b", Contexto(meses_desde_habitese=36))
        self.assertTrue(r.selo_garantia)
        self.assertTrue(r.vai_ao_sindico)
        self.assertEqual(r.responsavel, "Síndico")

    def test_garantia_fora_do_prazo_vira_manutencao(self):
        r = t("16b", Contexto(meses_desde_habitese=61))
        self.assertFalse(r.selo_garantia)
        self.assertFalse(r.vai_ao_sindico)
        self.assertEqual(r.responsavel, "Engenharia")

    def test_garantia_prazo_por_sistema(self):
        self.assertTrue(t("10c", Contexto(meses_desde_habitese=35)).selo_garantia)   # instalacoes: 36
        self.assertFalse(t("10c", Contexto(meses_desde_habitese=36)).selo_garantia)
        self.assertTrue(t("16", Contexto(meses_desde_habitese=59)).selo_garantia)    # estrutura: 60

    def test_sem_habitese_no_cadastro_nao_afirma_garantia(self):
        self.assertFalse(t("10c", Contexto(meses_desde_habitese=None)).selo_garantia)

    def test_item_sem_sistema_de_garantia_nunca_ganha_selo(self):
        self.assertFalse(t("1", Contexto(meses_desde_habitese=1)).selo_garantia)

    def test_nao_e_ocorrencia_resposta_automatica(self):
        r = t("NR4")
        self.assertEqual(r.status, "nao_ocorrencia")
        self.assertIn("reservas", r.resposta_automatica)
        self.assertIsNone(r.urgencia_final)

    def test_mensagem_vaga_pergunta_com_botoes(self):
        r = t(None, conf=0.4, sinais=[])
        self.assertEqual(r.status, "pergunta_ao_morador")
        r = triar("Problema com a cadeira do salão", Classificacao(None, 0.4, esclarecimento="cadeira_salao"))
        self.assertEqual(r.botoes, ["Quebrada", "Fora do lugar", "Outro"])

    def test_botao_classifica_sem_chamar_a_ia(self):
        msg = "Problema com a cadeira do salão"
        self.assertEqual(triar_resposta_botao(msg, "cadeira_salao", "Quebrada").codigo, "M1")
        self.assertEqual(triar_resposta_botao(msg, "cadeira_salao", "Fora do lugar").codigo, "M12b")
        r = triar_resposta_botao(msg, "cadeira_salao", "Outro")  # nao sabe: na duvida, sindico
        self.assertTrue(r.vai_ao_sindico)

    def test_vaga_com_palavra_de_risco_nao_pergunta(self):
        r = triar("Tem um barulho esquisito e cheiro de gás no salão", Classificacao(None, 0.3, esclarecimento="cadeira_salao"))
        self.assertEqual(r.status, "sindico_por_duvida")
        self.assertTrue(r.vai_ao_sindico)


class TestEquipe(unittest.TestCase):
    def test_responsavel_existe(self):
        self.assertEqual(resolver_executor("Zelador", Equipe.padrao())[0], "Zelador")

    def test_sem_zelador_vai_para_manutencao_terceirizada(self):
        self.assertEqual(resolver_executor("Zelador", Equipe(zelador=False))[0], "Manutenção")

    def test_sem_zelador_nem_manutencao_vai_para_portaria_presencial(self):
        e = Equipe(zelador=False, manutencao_terceirizada=False)
        self.assertEqual(resolver_executor("Zelador", e)[0], "Portaria")

    def test_so_portaria_remota(self):
        papel, detalhe, fb = resolver_executor("Portaria", Equipe.so_portaria_remota())
        self.assertEqual((papel, fb), ("Portaria", False))
        self.assertIn("remota", detalhe.lower())

    def test_ninguem_existe_cai_no_sindico(self):
        e = Equipe(zelador=False, manutencao_terceirizada=False, portaria_presencial=False, portaria_remota=False)
        self.assertEqual(resolver_executor("Zelador", e)[0], "Síndico")

    def test_fallback_aparece_nos_ajustes(self):
        r = t("1", equipe=Equipe(zelador=False))
        self.assertEqual(r.executor, "Manutenção")
        self.assertTrue(any("não existe" in a for a in r.ajustes))


if __name__ == "__main__":
    unittest.main()
