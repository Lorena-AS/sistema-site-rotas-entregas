from datetime import datetime
from html import escape
import streamlit as st
import banco
import rota
import visual

if st.session_state.get("logado") != True:
    st.stop()

visual.estilo_pagina_interna()
visual.estilo_historico()

if "aba_historico" not in st.session_state:
    st.session_state["aba_historico"] = "rotas"
#______________________________________________________________________________________________________________________#
#Troca a aba e formata datas

def escolher_aba(aba):
    st.session_state["aba_historico"] = aba


def formatar_data(texto):
    data = datetime.strptime(texto[:16], "%Y-%m-%d %H:%M")
    return data.strftime("%d/%m, %H:%M")


def tipo_da_aba(nome):
    if st.session_state["aba_historico"] == nome:
        return "primary"
    return "tertiary"


def numero_ou_traco(valor):
    if valor is None:
        return '<span class="cinza">—</span>'
    return str(int(valor))
#______________________________________________________________________________________________________________________#
#Monta as células de uma entrega concluída (os textos passam pelo escape)

def celulas_entrega(entrega):
    if entrega["eh_extra"]:
        celula_pedido = f'''<div class="celula-dupla"><span class="etiqueta-extra">Extra</span>
                        <span class="cinza">{escape(entrega["cliente_nome"])} · {escape(entrega["motivo"] or "")}</span></div>'''
    else:
        celula_pedido = numero_ou_traco(entrega["pedido_id"])

    if entrega["destino_tipo"] == "transportadora":
        etiqueta = '<span class="etiqueta-transportadora">Transportadora</span>'
        para_quem = f'<span class="cinza">para {escape(entrega["cliente_nome"])}</span>'
    else:
        etiqueta = '<span class="etiqueta-cliente">Cliente</span>'
        para_quem = ""
    celula_destino = f'''<div class="celula-dupla"><span class="titulo-destino">{escape(entrega["destino_nome"])}{etiqueta}</span>
                     {para_quem}</div>'''

    return [f'<span class="cinza">{formatar_data(entrega["data_hora"])}</span>',
            celula_pedido,
            numero_ou_traco(entrega["nf"]),
            numero_ou_traco(entrega["volume"]),
            celula_destino]
#______________________________________________________________________________________________________________________#
#Título e caixa com as abas

visual.titulo_pagina("Histórico")
aba = st.session_state["aba_historico"]

with st.container(key="caixa_historico"):
    with st.container(key="abas_historico", horizontal=True):
        st.button("Rotas geradas", key="aba_rotas", type=tipo_da_aba("rotas"), on_click=escolher_aba, args=("rotas",))
        st.button("Entregas", key="aba_entregas", type=tipo_da_aba("entregas"), on_click=escolher_aba,
                  args=("entregas",))
        st.button("Atividades", key="aba_atividades", type=tipo_da_aba("atividades"), on_click=escolher_aba,
                  args=("atividades",))

    if aba == "rotas":
        linhas = visual.linha_tabela(["Data", "Usuário", "Entregas", "Cota usada"], cabecalho=True, tipo="historico")
        rotas = banco.listar_historico()
        for data_hora, usuario, qtd_entregas, elementos in rotas:
            cota = f"{elementos * 100 / rota.COTA_GRATIS_ELEMENTOS:.1f}".replace(".", ",") + "%"
            linhas += visual.linha_tabela([f'<span class="cinza">{formatar_data(data_hora)}</span>',
                                           escape(usuario),
                                           str(int(qtd_entregas)),
                                           f'<span class="cinza">{cota}</span>'], tipo="historico")
        if len(rotas) == 0:
            linhas += '<p class="tabela-vazia">Nenhuma rota gerada nos últimos 2 meses.</p>'
    elif aba == "entregas":
        linhas = visual.linha_tabela(["Data", "Pedido", "Nº da NF", "Volumes", "Entregue em"], cabecalho=True,
                                     tipo="entregas")
        entregas = banco.listar_historico_entregas()
        for entrega in entregas:
            linhas += visual.linha_tabela(celulas_entrega(entrega), tipo="entregas")
        if len(entregas) == 0:
            linhas += '<p class="tabela-vazia">Nenhuma entrega confirmada nos últimos 2 meses.</p>'
    else:
        linhas = visual.linha_tabela(["Data", "Usuário", "Ação"], cabecalho=True, tipo="atividades")
        atividades = banco.listar_atividades()
        for data_hora, usuario, acao in atividades:
            linhas += visual.linha_tabela([f'<span class="cinza">{formatar_data(data_hora)}</span>',
                                           escape(usuario),
                                           escape(acao)], tipo="atividades")
        if len(atividades) == 0:
            linhas += '<p class="tabela-vazia">Nenhuma atividade nos últimos 2 meses.</p>'

    st.html(linhas)

st.html('<p class="nota-historico">Histórico dos últimos 2 meses.</p>')
#______________________________________________________________________________________________________________________#
#Números desde o início

entregas, cidades, clientes = banco.totais_desde_o_inicio()
st.html(visual.numeros_desde_o_inicio([(entregas, "Entregas feitas"),
                                       (cidades, "Cidades atendidas"),
                                       (clientes, "Clientes atendidos")]))