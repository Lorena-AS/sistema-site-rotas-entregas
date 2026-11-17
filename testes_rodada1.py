import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import banco
import funcoes

CAMINHO_BANCO_REAL = banco.CAMINHO_BANCO
TOKEN_FALSO = "token-falso"
#______________________________________________________________________________________________________________________#
#Bloqueia a rede e a pausa em todos os testes

bloqueio_rede = mock.patch.object(funcoes.requests, "get", side_effect=AssertionError("Rede real bloqueada nos testes."))
bloqueio_pausa = mock.patch.object(funcoes.time, "sleep")


def setUpModule():
    bloqueio_rede.start()
    bloqueio_pausa.start()


def tearDownModule():
    bloqueio_pausa.stop()
    bloqueio_rede.stop()


class RespostaFalsa:
    def __init__(self, status_code, dados):
        self.status_code = status_code
        self.dados = dados

    def json(self):
        return self.dados


class ApiFalsa:
    def __init__(self, respostas):
        self.respostas = respostas
        self.chamadas = []

    def __call__(self, url, headers=None, params=None, timeout=None):
        self.chamadas.append({"url": url, "params": params, "timeout": timeout})
        posicao = len(self.chamadas) - 1
        if posicao >= len(self.respostas):
            posicao = len(self.respostas) - 1
        return self.respostas[posicao]
#______________________________________________________________________________________________________________________#
#Prepara um banco novo numa pasta temporária para cada teste

class TesteComBanco(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.caminho = Path(self.pasta) / "teste.db"
        self.troca_caminho = mock.patch.object(banco, "CAMINHO_BANCO", self.caminho)
        self.troca_caminho.start()
        self.assertNotEqual(banco.CAMINHO_BANCO, CAMINHO_BANCO_REAL)

    def tearDown(self):
        self.troca_caminho.stop()
        shutil.rmtree(self.pasta, ignore_errors=True)

    def colunas_da_tabela(self, tabela):
        conexao = sqlite3.connect(self.caminho)
        cursor = conexao.cursor()
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = []
        for linha in cursor.fetchall():
            colunas.append(linha[1])
        conexao.close()
        return colunas
#______________________________________________________________________________________________________________________#
#Migração

class TesteMigracao(TesteComBanco):
    def test_migracao_duas_vezes_sem_perder_linhas(self):
        conexao = sqlite3.connect(self.caminho)
        cursor = conexao.cursor()
        cursor.execute("""CREATE TABLE pedidos (codigo INTEGER PRIMARY KEY, prioridade INTEGER NOT NULL,
                          adicionado_em TEXT NOT NULL)""")
        cursor.execute("INSERT INTO pedidos (codigo, prioridade, adicionado_em) VALUES (?, ?, ?)",
                       (1032, 1, "2026-11-01 10:00"))
        cursor.execute("INSERT INTO pedidos (codigo, prioridade, adicionado_em) VALUES (?, ?, ?)",
                       (1040, 2, "2026-11-02 11:00"))
        cursor.execute("""CREATE TABLE rota_pendente_extras (posicao INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL,
                          motivo TEXT NOT NULL, gerada_em TEXT NOT NULL)""")
        cursor.execute("INSERT INTO rota_pendente_extras (posicao, cliente_id, motivo, gerada_em) VALUES (?, ?, ?, ?)",
                       (1, 7, "Entrega de amostra", "2026-11-02 11:00"))
        conexao.commit()
        conexao.close()

        banco.criar_tabelas()
        banco.criar_tabelas()

        self.assertEqual(banco.listar_pedidos(), [(1032, 1, "2026-11-01 10:00"), (1040, 2, "2026-11-02 11:00")])
        self.assertEqual(banco.listar_extras_pendentes(), [(1, 7, "Entrega de amostra")])
        for tabela, coluna, tipo in banco.MIGRACOES:
            self.assertIn(coluna, self.colunas_da_tabela(tabela))
        self.assertIn("eh_extra", self.colunas_da_tabela("historico_entregas"))

    def test_migracoes_rejeita_fora_da_lista(self):
        banco.criar_tabelas()
        conexao = banco.conectar()
        cursor = conexao.cursor()
        tentativas = [("usuarios", "nf", "INTEGER"),
                      ("pedidos", "nf", "TEXT"),
                      ("pedidos", "senha", "TEXT"),
                      ("pedidos; DROP TABLE usuarios", "nf", "INTEGER"),
                      ("pedidos", "nf INTEGER; DROP TABLE usuarios", "INTEGER")]
        for tabela, coluna, tipo in tentativas:
            with self.assertRaises(ValueError):
                banco.adicionar_coluna_se_faltar(cursor, tabela, coluna, tipo)
        conexao.close()
        self.assertIn("senha_hash", self.colunas_da_tabela("usuarios"))
        self.assertNotIn("nf", self.colunas_da_tabela("usuarios"))
#______________________________________________________________________________________________________________________#
#Histórico de entregas

class TesteHistoricoEntregas(TesteComBanco):
    def inserir(self, data_hora, destino_tipo="cliente", eh_extra=0):
        conexao = banco.conectar()
        cursor = conexao.cursor()
        try:
            cursor.execute("""INSERT INTO historico_entregas (data_hora, usuario, pedido_id, eh_extra, motivo, nf,
                              volume, destino_tipo, destino_nome, cliente_nome)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (data_hora, "teste", 1032, eh_extra, None, 123, 2, destino_tipo, "Destino", "Cliente"))
            conexao.commit()
        finally:
            conexao.close()

    def contar(self):
        conexao = banco.conectar()
        cursor = conexao.cursor()
        cursor.execute("SELECT COUNT(*) FROM historico_entregas")
        total = cursor.fetchone()[0]
        conexao.close()
        return total

    def test_rejeita_destino_tipo_invalido(self):
        banco.criar_tabelas()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir(agora, destino_tipo="loja")
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir(agora, eh_extra=2)
        self.inserir(agora, destino_tipo="transportadora")
        self.assertEqual(self.contar(), 1)

    def test_limpeza_apaga_registros_antigos(self):
        banco.criar_tabelas()
        antiga = (datetime.now() - timedelta(days=banco.DIAS_GUARDAR_DADOS + 10)).strftime("%Y-%m-%d %H:%M:%S")
        recente = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.inserir(antiga)
        self.inserir(recente)

        banco.limpar_dados_antigos()

        conexao = banco.conectar()
        cursor = conexao.cursor()
        cursor.execute("SELECT data_hora FROM historico_entregas")
        linhas = cursor.fetchall()
        conexao.close()
        self.assertEqual(linhas, [(recente,)])
#______________________________________________________________________________________________________________________#
#Validação de NF, volume e local de entrega

class TesteValidacao(unittest.TestCase):
    def test_nf_valida(self):
        casos = [(1, 1), (123456789, 123456789), ("123", 123), (" 42 ", 42), ("000000001", 1)]
        for valor, esperado in casos:
            self.assertEqual(banco.conferir_nf(valor), esperado)

    def test_nf_invalida(self):
        casos = [True, False, 1.0, 1.5, -1, 0, "", "   ", "abc", "12a", "-5", "1.0", "0", "1 2",
                 "1234567890", 1234567890, None, "١٢٣", [1]]
        for valor in casos:
            with self.assertRaises(ValueError):
                banco.conferir_nf(valor)

    def test_volume_valido(self):
        casos = [(1, 1), (9999, 9999), ("10", 10), (" 7 ", 7)]
        for valor, esperado in casos:
            self.assertEqual(banco.conferir_volume(valor), esperado)

    def test_volume_invalido(self):
        casos = [True, 0, -3, 10000, "10000", "0", 2.0, "", "x", "2.5", None]
        for valor in casos:
            with self.assertRaises(ValueError):
                banco.conferir_volume(valor)

    def test_entregar_no(self):
        self.assertEqual(banco.conferir_entregar_no("cliente"), "cliente")
        self.assertEqual(banco.conferir_entregar_no("transportadora"), "transportadora")
        for valor in ["Cliente", "", "loja", None, 1, " cliente"]:
            with self.assertRaises(ValueError):
                banco.conferir_entregar_no(valor)
#______________________________________________________________________________________________________________________#
#API: transportadora da venda e transportadora pelo ID

ENDERECO_FALSO = {"cep": "00000-000", "logradouro": "Rua Teste", "numero": "1", "nome_cidade": "Cidade", "estado": "SP"}


class TesteTransportadoraPorId(unittest.TestCase):
    def test_transportadora_id_da_venda(self):
        casos = [(None, None), ("", None), ("abc", None), ("5", 5), (5, 5), ("0", None), (True, None)]
        for valor, esperado in casos:
            api = ApiFalsa([RespostaFalsa(200, {"data": {"id": 10, "transportadora_id": valor}})])
            with mock.patch.object(funcoes.requests, "get", api):
                resultado = funcoes.buscar_transportadora_da_venda(10, TOKEN_FALSO, TOKEN_FALSO)
            self.assertEqual(resultado, esperado)
            self.assertTrue(api.chamadas[0]["url"].endswith("/vendas/10"))
            self.assertEqual(api.chamadas[0]["timeout"], funcoes.TEMPO_LIMITE)

    def test_venda_nao_encontrada(self):
        api = ApiFalsa([RespostaFalsa(404, {})])
        with mock.patch.object(funcoes.requests, "get", api):
            self.assertIsNone(funcoes.buscar_transportadora_da_venda(10, TOKEN_FALSO, TOKEN_FALSO))

    def test_venda_erro_da_api(self):
        api = ApiFalsa([RespostaFalsa(500, {})])
        with mock.patch.object(funcoes.requests, "get", api):
            with self.assertRaises(funcoes.ErroAPI):
                funcoes.buscar_transportadora_da_venda(10, TOKEN_FALSO, TOKEN_FALSO)

    def test_transportadora_por_id(self):
        ficha = {"id": "5", "nome": "Transportes Teste", "enderecos": [{"endereco": ENDERECO_FALSO}]}
        api = ApiFalsa([RespostaFalsa(200, {"data": ficha})])
        with mock.patch.object(funcoes.requests, "get", api):
            resultado = funcoes.buscar_transportadora_por_id(5, TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(resultado, {"id": 5, "nome": "Transportes Teste", "endereco": ENDERECO_FALSO})
        self.assertTrue(api.chamadas[0]["url"].endswith("/transportadoras/5"))

    def test_transportadora_sem_endereco_ou_inexistente(self):
        respostas = [RespostaFalsa(200, {"data": {"id": "5", "nome": "Sem Endereço", "enderecos": []}}),
                     RespostaFalsa(200, {"data": {"id": "5", "nome": "Endereço Vazio", "enderecos": [{"endereco": {}}]}}),
                     RespostaFalsa(404, {})]
        for resposta in respostas:
            api = ApiFalsa([resposta])
            with mock.patch.object(funcoes.requests, "get", api):
                self.assertIsNone(funcoes.buscar_transportadora_por_id(5, TOKEN_FALSO, TOKEN_FALSO))
#______________________________________________________________________________________________________________________#
#API: busca de transportadoras pelo nome

def montar_pagina(fichas, proxima_pagina):
    return RespostaFalsa(200, {"meta": {"proxima_pagina": proxima_pagina}, "data": fichas})


def ficha_transportadora(id_transportadora, nome, ativo):
    return {"id": str(id_transportadora), "nome": nome, "ativo": ativo, "enderecos": [{"endereco": ENDERECO_FALSO}]}


class TesteBuscaPorNome(unittest.TestCase):
    def test_nome_curto(self):
        api = ApiFalsa([montar_pagina([], None)])
        with mock.patch.object(funcoes.requests, "get", api):
            for nome in ["", "ab", "  ab  ", None]:
                with self.assertRaises(ValueError):
                    funcoes.procurar_transportadoras_por_nome(nome, TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(api.chamadas, [])

    def test_filtra_inativas_e_usa_params(self):
        fichas = [ficha_transportadora(1, "Trans Ativa", "1"),
                  ficha_transportadora(2, "Trans Inativa", "0"),
                  ficha_transportadora(3, "Trans Sem Campo", None)]
        api = ApiFalsa([montar_pagina(fichas, None)])
        with mock.patch.object(funcoes.requests, "get", api):
            resultado = funcoes.procurar_transportadoras_por_nome("  Trans  ", TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], 1)
        self.assertEqual(api.chamadas[0]["url"], funcoes.URL_GESTAOCLICK + "/transportadoras")
        self.assertEqual(api.chamadas[0]["params"]["nome"], "Trans")

    def test_tres_paginas_juntam_resultados(self):
        api = ApiFalsa([montar_pagina([ficha_transportadora(1, "Trans A", "1")], 2),
                        montar_pagina([ficha_transportadora(2, "Trans B", "1")], 3),
                        montar_pagina([ficha_transportadora(3, "Trans C", "1")], None)])
        with mock.patch.object(funcoes.requests, "get", api):
            resultado = funcoes.procurar_transportadoras_por_nome("Trans", TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(len(resultado), 3)
        paginas = []
        for chamada in api.chamadas:
            paginas.append(chamada["params"]["pagina"])
        self.assertEqual(paginas, [1, 2, 3])

    def test_mais_de_tres_paginas(self):
        api = ApiFalsa([montar_pagina([ficha_transportadora(1, "Trans A", "1")], 99)])
        with mock.patch.object(funcoes.requests, "get", api):
            with self.assertRaises(ValueError) as erro:
                funcoes.procurar_transportadoras_por_nome("Trans", TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(str(erro.exception), "Muitos resultados. Digite um nome mais completo.")
        self.assertEqual(len(api.chamadas), funcoes.MAXIMO_PAGINAS_TRANSPORTADORA)

    def test_respeita_limite_de_consultas(self):
        api = ApiFalsa([montar_pagina([], 2), montar_pagina([], None)])
        with mock.patch.object(funcoes.requests, "get", api):
            with mock.patch.object(funcoes.time, "sleep") as pausa:
                funcoes.procurar_transportadoras_por_nome("Trans", TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(pausa.call_count, 2)
        for chamada in pausa.call_args_list:
            self.assertGreaterEqual(chamada.args[0], 1 / 3)
#______________________________________________________________________________________________________________________#

if __name__ == "__main__":
    unittest.main(verbosity=2)
