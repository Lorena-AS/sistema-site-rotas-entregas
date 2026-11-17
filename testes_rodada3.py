import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import banco
import funcoes
import rota
import textos

CAMINHO_BANCO_REAL = banco.CAMINHO_BANCO
#______________________________________________________________________________________________________________________#
#Bloqueia a rede e a pausa em todos os testes

bloqueio_rede = mock.patch.object(funcoes.requests, "get", side_effect=AssertionError("Rede real bloqueada nos testes."))
bloqueio_maps = mock.patch.object(funcoes.requests, "post", side_effect=AssertionError("Rede real bloqueada nos testes."))
bloqueio_pausa = mock.patch.object(funcoes.time, "sleep")


def setUpModule():
    bloqueio_rede.start()
    bloqueio_maps.start()
    bloqueio_pausa.start()


def tearDownModule():
    bloqueio_pausa.stop()
    bloqueio_maps.stop()
    bloqueio_rede.stop()
#______________________________________________________________________________________________________________________#
#Dados de apoio

ENDERECO_FALSO = {"logradouro": "Rua Teste", "numero": "1", "nome_cidade": "Cidade", "estado": "SP"}


def item_pedido(codigo, cliente_nome="Cliente A"):
    return {"tipo": "pedido", "codigo": codigo, "nf": 4500 + codigo % 100, "volume": 2, "destino_tipo": "cliente",
            "transportadora_id": None, "destino_nome": cliente_nome, "cliente_nome": cliente_nome}


def pedido_salvo(codigo):
    return {"codigo": codigo, "nf": 4500, "volume": 1, "entregar_no": "cliente"}
#______________________________________________________________________________________________________________________#
#Prepara um banco novo numa pasta temporária para cada teste

class TesteComBanco(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.caminho = Path(self.pasta) / "teste.db"
        self.troca_caminho = mock.patch.object(banco, "CAMINHO_BANCO", self.caminho)
        self.troca_caminho.start()
        self.assertNotEqual(banco.CAMINHO_BANCO, CAMINHO_BANCO_REAL)
        banco.criar_tabelas()

    def tearDown(self):
        self.troca_caminho.stop()
        shutil.rmtree(self.pasta, ignore_errors=True)

    def consultar(self, sql, parametros=()):
        conexao = sqlite3.connect(self.caminho)
        cursor = conexao.cursor()
        cursor.execute(sql, parametros)
        linhas = cursor.fetchall()
        conexao.close()
        return linhas

    def executar(self, sql, parametros=()):
        conexao = sqlite3.connect(self.caminho)
        conexao.execute(sql, parametros)
        conexao.commit()
        conexao.close()

    def gerar_rota(self, codigo=1055, cliente_nome="Cliente A"):
        return banco.salvar_rota_gerada("teste", "08:00", [item_pedido(codigo, cliente_nome)], 3600, 14400, 1, [], 4)
#______________________________________________________________________________________________________________________#
#Gerar rota: a rota (e o PDF) só aparecem enquanto estão valendo

class TesteRotaValendo(TesteComBanco):
    def test_aparece_pendente_de_hoje(self):
        gerada_em = self.gerar_rota()
        salva = banco.ultima_rota_valendo()
        self.assertIsNotNone(salva)
        self.assertEqual(salva["gerada_em"], gerada_em)

    def test_nao_aparece_depois_de_confirmada(self):
        self.gerar_rota()
        banco.confirmar_entregas([(1055, "Cidade", 1)], "teste", [])
        self.assertIsNone(banco.ultima_rota_valendo())
        self.assertIsNotNone(banco.ler_ultima_rota())

    def test_nao_aparece_pendente_de_ontem(self):
        self.gerar_rota()
        ontem = datetime.now() - timedelta(days=1)
        self.executar("UPDATE rota_pendente SET gerada_em = ?", (ontem.strftime("%Y-%m-%d %H:%M"),))
        self.executar("UPDATE ultima_rota SET gerada_em = ?", (ontem.strftime("%Y-%m-%d %H:%M:%S"),))
        self.assertIsNone(banco.ultima_rota_valendo())
        self.assertIsNotNone(banco.data_rota_pendente())

    def test_nao_aparece_sem_rota(self):
        self.assertIsNone(banco.ultima_rota_valendo())

    def test_regra_usa_a_data_de_hoje(self):
        self.gerar_rota()
        amanha = (datetime.now() + timedelta(days=1)).date()
        self.assertIsNone(banco.ultima_rota_valendo(hoje=amanha))
        self.assertIsNotNone(banco.ultima_rota_valendo(hoje=datetime.now().date()))
#______________________________________________________________________________________________________________________#
#Duas rotas ao mesmo tempo: BEGIN IMMEDIATE + conferência dentro da gravação

class TesteDuasRotas(TesteComBanco):
    def test_segunda_rota_com_pendente_da_erro_e_primeira_fica_intacta(self):
        primeira = self.gerar_rota(1055)
        antes = self.consultar("SELECT codigo, nf, cliente_nome FROM rota_pendente")

        with self.assertRaises(ValueError) as erro:
            self.gerar_rota(1056)

        self.assertEqual(str(erro.exception), banco.MENSAGEM_ROTA_JA_GERADA)
        self.assertEqual(self.consultar("SELECT codigo, nf, cliente_nome FROM rota_pendente"), antes)
        salva = banco.ler_ultima_rota()
        self.assertEqual(salva["gerada_em"], primeira)
        self.assertEqual(salva["pedidos"], [1055])
        self.assertEqual(self.consultar("SELECT COUNT(*), SUM(elementos) FROM historico"), [(2, 8)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM log_atividades WHERE acao = 'Gerou uma rota'"), [(1,)])
        self.assertEqual(self.consultar("SELECT rotas FROM rotas_por_usuario WHERE usuario = 'teste'"), [(1,)])

    def test_rota_gravada_por_outra_conexao_no_meio_do_caminho(self):
        self.executar("INSERT INTO rota_pendente (codigo, gerada_em) VALUES (?, ?)",
                      (999, datetime.now().strftime("%Y-%m-%d %H:%M")))
        with self.assertRaises(ValueError):
            self.gerar_rota(1055)
        self.assertEqual(self.consultar("SELECT codigo FROM rota_pendente"), [(999,)])
        self.assertEqual(self.consultar("SELECT qtd_entregas, elementos FROM historico"), [(1, 4)])
        self.assertIsNone(banco.ler_ultima_rota())

    def test_cota_somada_na_recusa_com_duas_conexoes(self):
        primeira = self.gerar_rota(1055)

        with self.assertRaises(ValueError) as erro:
            banco.salvar_rota_gerada("outra", "09:00", [item_pedido(1056)], 3600, 14400, 1, [], 9)

        self.assertEqual(str(erro.exception), banco.MENSAGEM_ROTA_JA_GERADA)
        self.assertEqual(banco.ler_ultima_rota()["gerada_em"], primeira)
        self.assertEqual(self.consultar("SELECT codigo FROM rota_pendente"), [(1055,)])
        self.assertEqual(self.consultar("SELECT usuario, elementos FROM historico ORDER BY id"),
                         [("teste", 4), ("outra", 9)])
        self.assertEqual(banco.elementos_usados_no_mes(), 13)
        self.assertEqual(self.consultar("SELECT usuario FROM log_atividades WHERE acao = ?",
                                        ("Rota recusada (outra rota já gerada); uso da cota registrado",)),
                         [("outra",)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM rotas_por_usuario WHERE usuario = 'outra'"), [(0,)])

    def test_banco_ocupado_so_na_rota_grava_a_cota_uma_vez(self):
        outra = sqlite3.connect(self.caminho)
        outra.execute("BEGIN IMMEDIATE")
        chamadas = []

        def conectar_falso():
            chamadas.append(1)
            if len(chamadas) == 2:
                outra.rollback()
            return sqlite3.connect(self.caminho, timeout=0.1)

        try:
            with mock.patch.object(banco, "conectar", conectar_falso):
                with self.assertRaises(ValueError) as erro:
                    self.gerar_rota(1055)
        finally:
            outra.close()

        self.assertEqual(str(erro.exception), banco.MENSAGEM_BANCO_OCUPADO)
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(self.consultar("SELECT elementos FROM historico"), [(4,)])
        self.assertIsNone(banco.ler_ultima_rota())
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM log_atividades WHERE acao = ?",
                                        ("Rota recusada (banco ocupado); uso da cota registrado",)), [(1,)])

    def test_falha_de_outro_tipo_na_cota_nao_e_escondida(self):
        self.gerar_rota(1055)
        with mock.patch.object(banco, "gravar_uso_da_cota", side_effect=RuntimeError("falha ao gravar a cota")):
            with self.assertRaises(RuntimeError):
                self.gerar_rota(1056)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM historico"), [(1,)])

    def test_begin_immediate_segura_a_outra_conexao(self):
        primeira = sqlite3.connect(self.caminho)
        segunda = sqlite3.connect(self.caminho, timeout=0.1)
        try:
            primeira.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                segunda.execute("BEGIN IMMEDIATE")
            primeira.rollback()
            segunda.execute("BEGIN IMMEDIATE")
            segunda.rollback()
        finally:
            primeira.close()
            segunda.close()

    def test_banco_ocupado_vira_mensagem_e_nao_grava(self):
        outra = sqlite3.connect(self.caminho)
        espera_curta = mock.patch.object(banco, "conectar", lambda: sqlite3.connect(self.caminho, timeout=0.1))
        inicio = datetime.now()
        try:
            outra.execute("BEGIN IMMEDIATE")
            with espera_curta:
                with self.assertRaises(ValueError) as erro_rota:
                    self.gerar_rota(1055)
                with self.assertRaises(ValueError) as erro_lista:
                    banco.salvar_lista_pedidos([pedido_salvo(1055)], {}, [])
        finally:
            outra.rollback()
            outra.close()
        self.assertLess((datetime.now() - inicio).total_seconds(), 3)
        self.assertEqual(str(erro_rota.exception), banco.MENSAGEM_BANCO_OCUPADO)
        self.assertEqual(str(erro_lista.exception), banco.MENSAGEM_BANCO_OCUPADO)
        self.assertIsNone(banco.ler_ultima_rota())
        self.assertEqual(banco.listar_codigos_pedidos(), [])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM historico"), [(0,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM log_atividades"), [(0,)])

    def test_outros_commits_continuam_funcionando(self):
        self.gerar_rota(1055)
        with self.assertRaises(ValueError):
            self.gerar_rota(1056)
        banco.registrar_atividade("teste", "Depois do erro")
        banco.salvar_lista_pedidos([pedido_salvo(1056)], {}, [])
        self.assertEqual(banco.listar_codigos_pedidos(), [1056])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM log_atividades WHERE acao = 'Depois do erro'"), [(1,)])
#______________________________________________________________________________________________________________________#
#Pedidos: lista_base evita "quem salva por último ganha"

class TesteListaBase(TesteComBanco):
    def test_lista_base_desatualizada_nao_apaga_nada(self):
        banco.salvar_lista_pedidos([pedido_salvo(1055)], {}, [])
        antes = banco.listar_pedidos_completos()

        with self.assertRaises(ValueError) as erro:
            banco.salvar_lista_pedidos([pedido_salvo(1056)], {}, [])
        self.assertEqual(str(erro.exception), banco.MENSAGEM_LISTA_ALTERADA)
        self.assertEqual(banco.listar_pedidos_completos(), antes)

    def test_lista_base_certa_salva(self):
        banco.salvar_lista_pedidos([pedido_salvo(1055)], {}, [])
        banco.salvar_lista_pedidos([pedido_salvo(1056), pedido_salvo(1055)], {}, [1055])
        self.assertEqual(banco.listar_codigos_pedidos(), [1056, 1055])

    def test_ordem_diferente_tambem_e_mudanca(self):
        banco.salvar_lista_pedidos([pedido_salvo(1055), pedido_salvo(1056)], {}, [])
        with self.assertRaises(ValueError):
            banco.salvar_lista_pedidos([pedido_salvo(1055)], {}, [1056, 1055])
        self.assertEqual(banco.listar_codigos_pedidos(), [1055, 1056])
#______________________________________________________________________________________________________________________#
#Esconder CPF nos nomes

class TesteEsconderCpf(unittest.TestCase):
    def test_casos_pedidos(self):
        casos = [("11122233344MARIA EXEMPLO", "MARIA EXEMPLO"),
                 ("JOAO EXEMPLO 55566677788", "JOAO EXEMPLO"),
                 ("111.222.333-44 ANA", "ANA"),
                 ("12345678000190 LTDA", "12345678000190 LTDA"),
                 ("12.345.678 CARLOS", "12.345.678 CARLOS"),
                 ("55566677788", "Cliente sem nome"),
                 ("111.222.333-44", "Cliente sem nome"),
                 ("ANA - 111.222.333-44", "ANA"),
                 ("12.345.678/0001-90 COMERCIO", "12.345.678/0001-90 COMERCIO"),
                 ("", "Cliente sem nome"),
                 (None, "Cliente sem nome")]
        for texto, esperado in casos:
            self.assertEqual(textos.esconder_cpf(texto), esperado)

    def test_rodar_de_novo_nao_muda(self):
        for texto in ["11122233344MARIA EXEMPLO", " - ANA 111.222.333-44 . ", "12345678000190 LTDA"]:
            uma_vez = textos.esconder_cpf(texto)
            self.assertEqual(textos.esconder_cpf(uma_vez), uma_vez)

    def test_nomes_da_api_saem_sem_cpf(self):
        ficha = {"id": "7", "nome": "11122233344MARIA EXEMPLO", "enderecos": [{"endereco": ENDERECO_FALSO}]}
        self.assertEqual(funcoes.montar_parada_extra(ficha, "")["nome"], "MARIA EXEMPLO")
        transportadora = {"id": "5", "nome": "55566677788", "enderecos": [{"endereco": ENDERECO_FALSO}]}
        self.assertEqual(funcoes.montar_transportadora(transportadora)["nome"], "Transportadora sem nome")

    def test_tela_e_pdf_saem_sem_cpf(self):
        parada = banco.agrupar_em_paradas([item_pedido(1055, "JOAO EXEMPLO 55566677788")])[0]
        exibir = rota.parada_para_exibir(parada, "Rua Teste, 1")
        self.assertEqual(exibir["cliente"], "JOAO EXEMPLO")
#______________________________________________________________________________________________________________________#
#CPF escondido antes de gravar e limpeza dos registros já gravados

class TesteCpfNoBanco(TesteComBanco):
    def test_grava_sem_cpf(self):
        self.gerar_rota(1055, "11122233344MARIA EXEMPLO")
        self.assertEqual(self.consultar("SELECT cliente_nome, destino_nome FROM rota_pendente"),
                         [("MARIA EXEMPLO", "MARIA EXEMPLO")])
        self.assertEqual(self.consultar("SELECT cliente_nome FROM ultima_rota_pedidos"), [("MARIA EXEMPLO",)])
        banco.confirmar_entregas([(1055, "Cidade", 1)], "teste", [])
        self.assertEqual(self.consultar("SELECT cliente_nome FROM historico_entregas"), [("MARIA EXEMPLO",)])

    def todos_os_nomes(self):
        nomes = []
        for tabela, coluna in banco.COLUNAS_COM_NOME:
            for linha in self.consultar(f"SELECT rowid, {coluna} FROM {tabela} ORDER BY rowid"):
                nomes.append((tabela, coluna, linha[0], linha[1]))
        return nomes

    def test_limpeza_dos_antigos_roda_duas_vezes_sem_mudar_na_segunda(self):
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.executar("""INSERT INTO rota_pendente (codigo, gerada_em, cliente_nome, destino_nome)
                         VALUES (?, ?, ?, ?)""", (1055, agora[:16], "11122233344MARIA EXEMPLO", "12.345.678 CARLOS"))
        self.executar("""INSERT INTO rota_pendente_extras (posicao, cliente_id, motivo, gerada_em, cliente_nome,
                         destino_nome) VALUES (?, ?, ?, ?, ?, ?)""",
                      (2, 9, "Entrega de amostra", agora[:16], "111.222.333-44 ANA", "12345678000190 LTDA"))
        self.executar("INSERT INTO ultima_rota_pedidos (codigo, cliente_nome, destino_nome) VALUES (?, ?, ?)",
                      (1055, "JOAO EXEMPLO 55566677788", "55566677788"))
        self.executar("""INSERT INTO ultima_rota_extras (posicao, cliente_id, motivo, cliente_nome, destino_nome)
                         VALUES (?, ?, ?, ?, ?)""", (2, 9, "Entrega de amostra", "ANA 111.222.333-44", "Trans"))
        self.executar("""INSERT INTO historico_entregas (data_hora, usuario, pedido_id, eh_extra, destino_tipo,
                         destino_nome, cliente_nome) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (agora, "teste", 1055, 0, "cliente", "11122233344MARIA", "11122233344MARIA"))

        banco.criar_tabelas()
        depois_da_primeira = self.todos_os_nomes()

        conexao = banco.conectar()
        alterados_na_segunda = banco.esconder_cpf_dos_nomes_gravados(conexao.cursor())
        conexao.rollback()
        conexao.close()
        banco.criar_tabelas()

        self.assertEqual(alterados_na_segunda, 0)
        self.assertEqual(self.todos_os_nomes(), depois_da_primeira)
        self.assertEqual(self.consultar("SELECT cliente_nome, destino_nome FROM rota_pendente"),
                         [("MARIA EXEMPLO", "12.345.678 CARLOS")])
        self.assertEqual(self.consultar("SELECT cliente_nome, destino_nome FROM rota_pendente_extras"),
                         [("ANA", "12345678000190 LTDA")])
        self.assertEqual(self.consultar("SELECT cliente_nome, destino_nome FROM ultima_rota_pedidos"),
                         [("JOAO EXEMPLO", "Cliente sem nome")])
        self.assertEqual(self.consultar("SELECT cliente_nome FROM historico_entregas"), [("MARIA",)])
#______________________________________________________________________________________________________________________#
#Lista de transportadoras: nenhum nome vira link ou formatação

class TesteEscaparMarkdown(unittest.TestCase):
    def test_link_nao_vira_link(self):
        resultado = textos.escapar_markdown("[clique](http://x)")
        self.assertEqual(resultado, "\\[clique\\]\\(http\\://x\\)")
        self.assertNotIn("[clique](", resultado)

    def test_formatacao_escapada(self):
        self.assertEqual(textos.escapar_markdown("*TRANS* _A_ #1"), "\\*TRANS\\* \\_A\\_ \\#1")
        self.assertEqual(textos.escapar_markdown("Transportes Exemplo"), "Transportes Exemplo")
#______________________________________________________________________________________________________________________#

if __name__ == "__main__":
    unittest.main(verbosity=2)
