import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest import mock

import banco
import funcoes
import pdf_rota
import rota

CAMINHO_BANCO_REAL = banco.CAMINHO_BANCO
TOKEN_FALSO = "token-falso"
INFINITO = float("inf")
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
#Dados falsos do GestãoClick e do Google Maps

ENDERECO_TRANSPORTADORA = {"logradouro": "Rua da Transportadora", "numero": "10", "nome_cidade": "Cidade Transp",
                           "estado": "SP"}
ENDERECO_LONGE = {"logradouro": "Rua Longe", "numero": "99", "nome_cidade": "Cidade Longe", "estado": "MG"}


def endereco_do_cliente(letra):
    return {"logradouro": f"Rua Cliente {letra}", "numero": "1", "nome_cidade": f"Cidade {letra}", "estado": "SP"}


def ficha_cliente(cliente_id, letra):
    return {"id": str(cliente_id), "nome": f"Cliente {letra}", "enderecos": [{"endereco": endereco_do_cliente(letra)}]}


class GestaoClickFalso:
    def __init__(self):
        self.vendas = {1067: {"id": "1", "codigo": "1067", "cliente_id": "1", "nome_cliente": "Cliente A",
                              "transportadora_id": "5"},
                       1068: {"id": "2", "codigo": "1068", "cliente_id": "2", "nome_cliente": "Cliente B",
                              "transportadora_id": 5},
                       1055: {"id": "3", "codigo": "1055", "cliente_id": "3", "nome_cliente": "Cliente C",
                              "transportadora_id": None},
                       1056: {"id": "4", "codigo": "1056", "cliente_id": "4", "nome_cliente": "Cliente D",
                              "transportadora_id": ""}}
        self.clientes = {1: ficha_cliente(1, "A"), 2: ficha_cliente(2, "B"), 3: ficha_cliente(3, "C"),
                         4: ficha_cliente(4, "D"), 9: ficha_cliente(9, "E")}
        self.transportadoras = {5: {"id": 5, "nome": "Trans Rápida", "endereco": ENDERECO_TRANSPORTADORA},
                                6: {"id": 6, "nome": "Trans Longe", "endereco": ENDERECO_LONGE}}
        self.consultas_transportadora = []

    def buscar_pedido(self, codigo, token_acesso, token_secreta):
        return self.vendas.get(codigo)

    def buscar_endereco(self, cliente_id, token_acesso, token_secreta):
        return self.clientes.get(int(cliente_id))

    def buscar_transportadora_por_id(self, transportadora_id, token_acesso, token_secreta):
        self.consultas_transportadora.append(transportadora_id)
        return self.transportadoras.get(transportadora_id)


class MapsFalso:
    def __init__(self, distancias_da_base=None):
        if distancias_da_base is None:
            distancias_da_base = {}
        self.distancias_da_base = distancias_da_base
        self.enderecos_recebidos = []

    def distancia(self, endereco):
        return self.distancias_da_base.get(endereco, 10000)

    def __call__(self, lista_enderecos, chave_maps):
        self.enderecos_recebidos = list(lista_enderecos)
        distancias = []
        tempos = []
        for i in range(len(lista_enderecos)):
            linha_distancia = []
            linha_tempo = []
            for j in range(len(lista_enderecos)):
                if i == j:
                    distancia = 0
                elif i == 0:
                    distancia = self.distancia(lista_enderecos[j])
                elif j == 0:
                    distancia = self.distancia(lista_enderecos[i])
                else:
                    distancia = 1000
                linha_distancia.append(distancia)
                if distancia == INFINITO:
                    linha_tempo.append(INFINITO)
                else:
                    linha_tempo.append(600)
            distancias.append(linha_distancia)
            tempos.append(linha_tempo)
        return distancias, tempos


def pedido_salvo(codigo, nf, volume, entregar_no):
    return {"codigo": codigo, "nf": nf, "volume": volume, "entregar_no": entregar_no}


def parada_extra(cliente_id, letra, transportadora_id=None, nf=None, volume=None):
    return {"cliente_id": cliente_id, "motivo": "Entrega de amostra", "nome": f"Cliente {letra}",
            "endereco": endereco_do_cliente(letra), "nf": nf, "volume": volume, "transportadora_id": transportadora_id}


def gerar(pedidos, extras, quantidade, gestaoclick, maps):
    with mock.patch.object(funcoes, "buscar_pedido", gestaoclick.buscar_pedido), \
            mock.patch.object(funcoes, "buscar_endereco", gestaoclick.buscar_endereco), \
            mock.patch.object(funcoes, "buscar_transportadora_por_id", gestaoclick.buscar_transportadora_por_id), \
            mock.patch.object(funcoes, "calcular_distancia", maps):
        return rota.gerar_rota(pedidos, quantidade, time(8, 0), time(12, 0), TOKEN_FALSO, TOKEN_FALSO, "chave-falsa",
                               "Base", extras, {})


def item_da_rota(tipo, codigo_ou_cliente, nf, volume, destino_tipo, transportadora_id, destino_nome, cliente_nome):
    item = {"tipo": tipo, "nf": nf, "volume": volume, "destino_tipo": destino_tipo,
            "transportadora_id": transportadora_id, "destino_nome": destino_nome, "cliente_nome": cliente_nome}
    if tipo == "pedido":
        item["codigo"] = codigo_ou_cliente
    else:
        item["cliente_id"] = codigo_ou_cliente
        item["motivo"] = "Entrega de amostra"
    return item


def itens_agrupados_na_transportadora():
    return [item_da_rota("pedido", 1067, 4540, 5, "transportadora", 5, "Trans Rápida", "Cliente A"),
            item_da_rota("pedido", 1068, 4541, 3, "transportadora", 5, "Trans Rápida", "Cliente B"),
            item_da_rota("extra", 9, 77, 2, "transportadora", 5, "Trans Rápida", "Cliente E")]
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
#______________________________________________________________________________________________________________________#
#Lista de pedidos: NF, volume e local de entrega

class TesteListaPedidos(TesteComBanco):
    def test_regrava_sem_perder_nf_volume_entregar_no(self):
        pedidos = [pedido_salvo(1067, 4540, 5, "transportadora"), pedido_salvo(1055, "4533", " 20 ", "cliente")]
        banco.salvar_lista_pedidos(pedidos, {1067: 5, 1055: None})
        primeira = banco.listar_pedidos_completos()

        banco.salvar_lista_pedidos([pedidos[1], pedidos[0]], {1067: "5", 1055: None})
        segunda = banco.listar_pedidos_completos()

        self.assertEqual(segunda[0]["codigo"], 1055)
        self.assertEqual((segunda[0]["nf"], segunda[0]["volume"], segunda[0]["entregar_no"]), (4533, 20, "cliente"))
        self.assertEqual((segunda[1]["nf"], segunda[1]["volume"], segunda[1]["entregar_no"]), (4540, 5, "transportadora"))
        self.assertEqual(segunda[1]["adicionado_em"], primeira[0]["adicionado_em"])

    def test_transportadora_sem_transportadora_na_venda(self):
        banco.salvar_lista_pedidos([pedido_salvo(1055, 4533, 20, "cliente")], {1055: None})
        antes = banco.listar_pedidos_completos()

        with self.assertRaises(ValueError) as erro:
            banco.salvar_lista_pedidos([pedido_salvo(1055, 4533, 20, "transportadora"),
                                        pedido_salvo(1056, 4534, 1, "transportadora")], {1055: None, 1056: ""})
        self.assertIn("1055", str(erro.exception))
        self.assertIn("1056", str(erro.exception))
        self.assertEqual(banco.listar_pedidos_completos(), antes)

        with self.assertRaises(ValueError):
            banco.salvar_lista_pedidos([pedido_salvo(1067, 4540, 5, "transportadora")])
        self.assertEqual(banco.listar_pedidos_completos(), antes)

    def test_dados_invalidos_nao_gravam(self):
        casos = [pedido_salvo(1055, "abc", 20, "cliente"),
                 pedido_salvo(1055, 4533, 0, "cliente"),
                 pedido_salvo(1055, 4533, 20, "loja"),
                 pedido_salvo("x", 4533, 20, "cliente")]
        for pedido in casos:
            with self.assertRaises(ValueError):
                banco.salvar_lista_pedidos([pedido], {})
        self.assertEqual(banco.listar_pedidos_completos(), [])

    def test_pedido_antigo_sem_nf_aparece_como_incompleto(self):
        banco.salvar_lista_pedidos([pedido_salvo(1055, None, None, None), pedido_salvo(1056, 4534, 1, "cliente")], {})
        self.assertEqual(banco.pedidos_sem_nf_ou_volume(), [1055])
#______________________________________________________________________________________________________________________#
#Regras da rota: agrupamento, limite de paradas e raio

class TesteRegrasDaRota(unittest.TestCase):
    def test_agrupa_pedidos_e_extra_da_mesma_transportadora(self):
        gestaoclick = GestaoClickFalso()
        pedidos = [pedido_salvo(1067, 4540, 5, "transportadora"), pedido_salvo(1068, 4541, 3, "transportadora")]
        extras = [parada_extra(9, "E", transportadora_id=5, nf="77", volume="2")]

        resultado = gerar(pedidos, extras, 8, gestaoclick, MapsFalso())

        self.assertEqual(len(resultado["paradas"]), 1)
        self.assertEqual(len(resultado["paradas"][0]["itens"]), 3)
        self.assertEqual(len(resultado["itens_na_rota"]), 3)
        self.assertEqual(gestaoclick.consultas_transportadora, [5])
        self.assertEqual(resultado["quantidade_pedida"], 1)
        self.assertEqual(resultado["problemas"], [])

    def test_limite_conta_paradas(self):
        gestaoclick = GestaoClickFalso()
        pedidos = [pedido_salvo(1067, 4540, 5, "transportadora"), pedido_salvo(1055, 4533, 20, "cliente"),
                   pedido_salvo(1068, 4541, 3, "transportadora"), pedido_salvo(1056, 4534, 1, "cliente")]

        resultado = gerar(pedidos, [], 2, gestaoclick, MapsFalso())

        self.assertEqual(len(resultado["paradas"]), 2)
        self.assertEqual(sorted(resultado["pedidos_na_rota"]), [1055, 1067, 1068])
        self.assertEqual(resultado["problemas"], [])

    def test_extras_da_mesma_transportadora_contam_uma_parada(self):
        extras = [parada_extra(9, "E", transportadora_id=5), parada_extra(4, "D", transportadora_id=5),
                  parada_extra(3, "C")]
        self.assertEqual(rota.contar_paradas_extras(extras), 2)

    def test_raio_usa_endereco_da_transportadora(self):
        gestaoclick = GestaoClickFalso()
        texto_transportadora = funcoes.enderecos_em_texto(ENDERECO_TRANSPORTADORA)
        texto_cliente = funcoes.enderecos_em_texto(endereco_do_cliente("A"))

        perto = MapsFalso({texto_transportadora: 30000, texto_cliente: 90000})
        resultado = gerar([pedido_salvo(1067, 4540, 5, "transportadora")], [], 8, gestaoclick, perto)
        self.assertIn(texto_transportadora, perto.enderecos_recebidos)
        self.assertNotIn(texto_cliente, perto.enderecos_recebidos)
        self.assertEqual(resultado["pedidos_na_rota"], [1067])

        longe = MapsFalso({texto_transportadora: 80000, texto_cliente: 1000})
        resultado = gerar([pedido_salvo(1067, 4540, 5, "transportadora")], [], 8, gestaoclick, longe)
        self.assertEqual(resultado["pedidos_na_rota"], [])
        self.assertEqual(resultado["problemas"], ["Pedido 1067: fora do raio de 50 km ou sem rota."])

    def test_transportadora_escolhida_sem_transportadora_na_venda(self):
        resultado = gerar([pedido_salvo(1055, 4533, 20, "transportadora")], [], 8, GestaoClickFalso(), MapsFalso())
        self.assertEqual(resultado["paradas"], [])
        self.assertEqual(resultado["problemas"], ["Pedido 1055: a venda não tem transportadora no GestãoClick."])

    def test_pedido_sem_nf_bloqueia_a_rota(self):
        with self.assertRaises(ValueError) as erro:
            gerar([pedido_salvo(1055, None, 20, "cliente")], [], 8, GestaoClickFalso(), MapsFalso())
        self.assertIn("1055", str(erro.exception))
#______________________________________________________________________________________________________________________#
#Textos da tela e do PDF

class TesteTextos(unittest.TestCase):
    def test_textos_da_parada(self):
        paradas = banco.agrupar_em_paradas(itens_agrupados_na_transportadora())
        exibir = rota.parada_para_exibir(paradas[0], "Rua da Transportadora, 10")
        self.assertEqual(exibir["tipo"], "transportadora")
        self.assertEqual(exibir["titulo"], "Trans Rápida")
        self.assertEqual(exibir["itens"][0], {"titulo": "Pedido 1067 · NF 4540 · Cliente A", "detalhe": "5 volumes"})
        self.assertEqual(exibir["itens"][2]["titulo"], "Parada extra · Cliente E · Entrega de amostra · NF 77 · 2 volumes")

        normal = banco.agrupar_em_paradas([item_da_rota("pedido", 1055, 4533, 20, "cliente", None, "Cliente C",
                                                        "Cliente C")])
        exibir_normal = rota.parada_para_exibir(normal[0], "Rua Cliente C, 1")
        self.assertEqual(exibir_normal["titulo"], "Pedido 1055 · NF 4533")
        self.assertEqual(exibir_normal["detalhe"], "20 volumes")
        self.assertNotIn("rolo", str(exibir).lower() + str(exibir_normal).lower())

    def test_pdf_com_parada_agrupada(self):
        paradas = banco.agrupar_em_paradas(itens_agrupados_na_transportadora())
        exibir = [rota.parada_para_exibir(paradas[0], "Rua da Transportadora, 10")]
        arquivo = pdf_rota.montar_pdf("segunda-feira", "16/11/2026", "08:00", "10:00", exibir, "teste", "16/11/2026 08:00")
        self.assertTrue(arquivo.startswith(b"%PDF"))
#______________________________________________________________________________________________________________________#
#Gravação da rota, confirmação e histórico de entregas

class TesteConfirmacao(TesteComBanco):
    def gravar_rota_agrupada(self):
        banco.salvar_lista_pedidos([pedido_salvo(1067, 4540, 5, "transportadora"),
                                    pedido_salvo(1068, 4541, 3, "transportadora")], {1067: 5, 1068: 5})
        return banco.salvar_rota_gerada("teste", "08:00", itens_agrupados_na_transportadora(), 3600, 14400, 1, [], 4)

    def test_salvar_rota_guarda_os_dados_de_cada_item(self):
        self.assertIsNotNone(self.gravar_rota_agrupada())
        self.assertEqual(self.consultar("SELECT qtd_entregas FROM historico"), [(1,)])

        salva = banco.ler_ultima_rota()
        self.assertEqual(len(salva["itens"]), 3)
        self.assertEqual(salva["itens"][0]["nf"], 4540)
        self.assertEqual(salva["itens"][2]["posicao"], 3)
        self.assertEqual(len(banco.agrupar_em_paradas(salva["itens"])), 1)

        pendentes = banco.listar_itens_pendentes()
        self.assertEqual(pendentes, salva["itens"])

    def test_salvar_rota_recusa_dados_invalidos(self):
        casos = [item_da_rota("pedido", 1067, None, 5, "cliente", None, "A", "A"),
                 item_da_rota("pedido", 1067, 4540, 5, "transportadora", None, "T", "A"),
                 item_da_rota("pedido", 1067, 4540, 5, "loja", None, "T", "A"),
                 item_da_rota("extra", 9, "x", None, "cliente", None, "E", "E")]
        for item in casos:
            with self.assertRaises(ValueError):
                banco.salvar_rota_gerada("teste", "08:00", [item], 3600, 14400, 1, [], 4)
        self.assertIsNone(banco.ler_ultima_rota())

    def test_confirmacao_parcial_dentro_da_parada_agrupada(self):
        self.gravar_rota_agrupada()

        marcadas, total = banco.confirmar_entregas([(1067, "Cidade A", 1)], "teste", [(3, "Cidade E")])

        self.assertEqual((marcadas, total), (2, 3))
        historico = self.consultar("""SELECT pedido_id, eh_extra, motivo, nf, volume, destino_tipo, destino_nome,
                                      cliente_nome FROM historico_entregas ORDER BY id""")
        self.assertEqual(historico, [(1067, 0, None, 4540, 5, "transportadora", "Trans Rápida", "Cliente A"),
                                     (None, 1, "Entrega de amostra", 77, 2, "transportadora", "Trans Rápida",
                                      "Cliente E")])
        restantes = banco.listar_pedidos_completos()
        self.assertEqual(len(restantes), 1)
        self.assertEqual((restantes[0]["codigo"], restantes[0]["nf"], restantes[0]["volume"]), (1068, 4541, 3))
        self.assertIsNone(banco.data_rota_pendente())

    def test_cidade_do_cliente_nas_estatisticas(self):
        self.gravar_rota_agrupada()
        gestaoclick = GestaoClickFalso()
        with mock.patch.object(funcoes, "buscar_pedido", gestaoclick.buscar_pedido), \
                mock.patch.object(funcoes, "buscar_endereco", gestaoclick.buscar_endereco):
            dados = funcoes.buscar_dados_do_pedido(1067, TOKEN_FALSO, TOKEN_FALSO)
        self.assertEqual(dados["cidade"], "Cidade A")
        self.assertEqual(dados["transportadora_id"], 5)

        banco.confirmar_entregas([(1067, dados["cidade"], dados["cliente_id"])], "teste", [])
        self.assertEqual(self.consultar("SELECT cidade FROM cidades_atendidas"), [("CIDADE A",)])

    def test_aba_entregas_lista_so_recentes_e_em_ordem(self):
        conexao = banco.conectar()
        cursor = conexao.cursor()
        antiga = (datetime.now() - timedelta(days=banco.DIAS_GUARDAR_DADOS + 5)).strftime("%Y-%m-%d %H:%M:%S")
        ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for data_hora, pedido_id in [(antiga, 1), (ontem, 2), (hoje, 3)]:
            banco.gravar_entrega_no_historico(cursor, data_hora, "teste",
                                              banco.item_de_pedido(pedido_id, (pedido_id, None, None, None, "cliente",
                                                                               "Cliente", "Cliente")))
        conexao.commit()
        conexao.close()

        entregas = banco.listar_historico_entregas()
        pedidos = []
        for entrega in entregas:
            pedidos.append(entrega["pedido_id"])
        self.assertEqual(pedidos, [3, 2])
#______________________________________________________________________________________________________________________#
#Busca de transportadora: ativo "1" ou 1

class TesteBuscaTransportadora(unittest.TestCase):
    def test_aceita_ativo_texto_ou_numero(self):
        fichas = []
        ativos = ["1", 1, " 1 ", "0", 0, None, True]
        numero = 1
        for ativo in ativos:
            fichas.append({"id": str(numero), "nome": f"Trans {numero}", "ativo": ativo,
                           "enderecos": [{"endereco": ENDERECO_TRANSPORTADORA}]})
            numero += 1

        def api_falsa(url, headers=None, params=None, timeout=None):
            resposta = mock.Mock()
            resposta.status_code = 200
            resposta.json.return_value = {"meta": {"proxima_pagina": None}, "data": fichas}
            return resposta

        with mock.patch.object(funcoes.requests, "get", api_falsa):
            resultado = funcoes.procurar_transportadoras_por_nome("Trans", TOKEN_FALSO, TOKEN_FALSO)

        ids = []
        for transportadora in resultado:
            ids.append(transportadora["id"])
        self.assertEqual(ids, [1, 2, 3])
#______________________________________________________________________________________________________________________#

if __name__ == "__main__":
    unittest.main(verbosity=2)
