import html
from datetime import datetime
import streamlit as st
import banco
import funcoes
import visual

if st.session_state.get("logado") != True:
    st.stop()

TOKEN_ACESSO = st.secrets["gestaoclick"]["access_token"]
TOKEN_SECRETO = st.secrets["gestaoclick"]["secret_access_token"]
NF_MAXIMA = 10 ** banco.TAMANHO_MAXIMO_NF - 1
NOMES_DESTINOS = {"transportadora": "Transportadora", "cliente": "Cliente"}

visual.estilo_pagina_interna()
#______________________________________________________________________________________________________________________#
#Consulta a situação e a transportadora de um pedido no GestãoClick

def consultar_pedido(codigo):
    pedido = funcoes.buscar_pedido(codigo, TOKEN_ACESSO, TOKEN_SECRETO)
    if pedido is None:
        return "Não encontrado", None
    return pedido.get("nome_situacao", ""), funcoes.transportadora_do_pedido(pedido)


def guardar_consulta(codigo):
    situacao, transportadora_id = consultar_pedido(codigo)
    st.session_state["situacoes"][codigo] = situacao
    st.session_state["transportadoras_vendas"][codigo] = transportadora_id
    return situacao


def destino_padrao(codigo):
    if st.session_state["transportadoras_vendas"].get(codigo) is not None:
        return "transportadora"
    return "cliente"


def esquecer_campos(codigo):
    for campo in ["nf", "volume", "destino"]:
        st.session_state.pop(f"{campo}_{codigo}", None)


def dados_do_pedido(codigo):
    if codigo not in st.session_state["dados_pedidos"]:
        st.session_state["dados_pedidos"][codigo] = {"nf": None, "volume": None, "entregar_no": None}
    return st.session_state["dados_pedidos"][codigo]
#______________________________________________________________________________________________________________________#
#Prepara a lista da sessão: lê o banco sempre que não houver alterações pendentes

if "situacoes" not in st.session_state:
    st.session_state["situacoes"] = {}
    st.session_state["pedido_selecionado"] = None
    st.session_state["alteracoes"] = 0
    st.session_state["erros_salvar"] = []
if "dados_pedidos" not in st.session_state:
    st.session_state["dados_pedidos"] = {}
    st.session_state["transportadoras_vendas"] = {}

if st.session_state["alteracoes"] == 0:
    lista = []
    datas = {}
    dados = {}
    for pedido in banco.listar_pedidos_completos():
        codigo = pedido["codigo"]
        lista.append(codigo)
        datas[codigo] = datetime.strptime(pedido["adicionado_em"], "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
        dados[codigo] = {"nf": pedido["nf"], "volume": pedido["volume"], "entregar_no": pedido["entregar_no"]}
        if st.session_state["dados_pedidos"].get(codigo) != dados[codigo]:
            esquecer_campos(codigo)
    st.session_state["lista_pedidos"] = lista
    st.session_state["datas_pedidos"] = datas
    st.session_state["dados_pedidos"] = dados
    st.session_state["lista_base"] = list(lista)

lista_mudou = False
if st.session_state["alteracoes"] > 0:
    lista_mudou = st.session_state.get("lista_base") != banco.listar_codigos_pedidos()

faltam_conferir = []
for codigo in st.session_state["lista_pedidos"]:
    if codigo not in st.session_state["situacoes"] or codigo not in st.session_state["transportadoras_vendas"]:
        faltam_conferir.append(codigo)

if len(faltam_conferir) > 0:
    with st.spinner("Conferindo pedidos no GestãoClick..."):
        try:
            for codigo in faltam_conferir:
                guardar_consulta(codigo)
        except funcoes.ErroAPI as erro:
            st.toast(str(erro), icon=":material/error:")

for codigo in st.session_state["lista_pedidos"]:
    dados_pedido = dados_do_pedido(codigo)
    if dados_pedido["entregar_no"] is None and codigo in st.session_state["transportadoras_vendas"]:
        dados_pedido["entregar_no"] = destino_padrao(codigo)
#______________________________________________________________________________________________________________________#
#Ações dos botões e dos campos (rodam antes da página ser desenhada de novo)

def adicionar_pedido():
    texto = st.session_state["codigo_novo"].strip()
    lista = st.session_state["lista_pedidos"]

    if texto.isdigit() == False:
        st.toast("Digite só os números do código do pedido.", icon=":material/error:")
        return

    codigo = int(texto)
    if codigo in lista:
        st.toast(f"O pedido {codigo} já está na lista.", icon=":material/info:")
        return

    try:
        nf = banco.conferir_nf(st.session_state["nf_nova"])
        volume = banco.conferir_volume(st.session_state["volume_novo"])
    except ValueError as erro:
        st.toast(str(erro), icon=":material/error:")
        return

    try:
        guardar_consulta(codigo)
    except funcoes.ErroAPI as erro:
        st.toast(str(erro), icon=":material/error:")
        return

    lista.append(codigo)
    st.session_state["datas_pedidos"][codigo] = "agora"
    st.session_state["dados_pedidos"][codigo] = {"nf": nf, "volume": volume, "entregar_no": destino_padrao(codigo)}
    esquecer_campos(codigo)
    st.session_state["alteracoes"] += 1
    st.toast(f"Pedido {codigo} adicionado.", icon=":material/check_circle:")


def alterar_campo(codigo, campo):
    valor = st.session_state.get(f"{campo}_{codigo}")
    if campo == "destino":
        dados_do_pedido(codigo)["entregar_no"] = valor
    else:
        dados_do_pedido(codigo)[campo] = valor
    st.session_state["alteracoes"] += 1


def descartar_alteracoes():
    for codigo in st.session_state["lista_pedidos"]:
        esquecer_campos(codigo)
    st.session_state["alteracoes"] = 0
    st.session_state["erros_salvar"] = []
    st.session_state["pedido_selecionado"] = None


def selecionar_pedido(codigo):
    st.session_state["pedido_selecionado"] = codigo


def mover_pedido(movimento):
    lista = st.session_state["lista_pedidos"]
    codigo = st.session_state["pedido_selecionado"]
    if codigo not in lista:
        return

    posicao = lista.index(codigo)
    if movimento == "topo":
        lista.remove(codigo)
        lista.insert(0, codigo)
    elif movimento == "subir" and posicao > 0:
        lista[posicao], lista[posicao - 1] = lista[posicao - 1], lista[posicao]
    elif movimento == "descer" and posicao < len(lista) - 1:
        lista[posicao], lista[posicao + 1] = lista[posicao + 1], lista[posicao]
    elif movimento == "remover":
        lista.remove(codigo)
        esquecer_campos(codigo)
        st.session_state["pedido_selecionado"] = None
    st.session_state["alteracoes"] += 1


def montar_frase(problemas):
    frase = "O pedido " + problemas[0]
    for i in range(1, len(problemas)):
        if i == len(problemas) - 1:
            frase += " e o " + problemas[i]
        else:
            frase += ", o " + problemas[i]
    return frase + "."


def salvar_lista():
    lista = st.session_state["lista_pedidos"]
    problemas = []
    try:
        for codigo in lista:
            situacao = guardar_consulta(codigo)
            if situacao == "Não encontrado":
                problemas.append(f"{codigo} não existe no sistema")
            elif situacao != funcoes.SITUACAO_LIBERADA:
                problemas.append(f"{codigo} ainda não está concretizado")
    except funcoes.ErroAPI as erro:
        st.session_state["erros_salvar"] = [str(erro)]
        return

    if len(problemas) > 0:
        st.session_state["erros_salvar"] = [montar_frase(problemas)]
        return

    pedidos = []
    for codigo in lista:
        dados_pedido = st.session_state["dados_pedidos"].get(codigo, {})
        entregar_no = dados_pedido.get("entregar_no") or destino_padrao(codigo)
        pedidos.append({"codigo": codigo, "nf": dados_pedido.get("nf"), "volume": dados_pedido.get("volume"),
                        "entregar_no": entregar_no})

    lista_base = st.session_state.get("lista_base")
    if lista_base is None:
        st.session_state["erros_salvar"] = [banco.MENSAGEM_LISTA_ALTERADA]
        return

    try:
        banco.salvar_lista_pedidos(pedidos, st.session_state["transportadoras_vendas"], lista_base)
    except ValueError as erro:
        st.session_state["erros_salvar"] = [str(erro)]
        return

    banco.registrar_atividade(st.session_state["usuario"], "Salvou a lista de pedidos")
    st.session_state["alteracoes"] = 0
    st.session_state["erros_salvar"] = []
    st.toast("Lista de pedidos salva.", icon=":material/check_circle:")
#______________________________________________________________________________________________________________________#
#Título e campos para adicionar pedidos

lista = st.session_state["lista_pedidos"]
selecionado = st.session_state["pedido_selecionado"]

visual.titulo_pagina("Lista de Pedidos")

with st.form("form_adicionar", clear_on_submit=True, border=False):
    with st.container(key="linha_adicionar", horizontal=True, vertical_alignment="center"):
        st.html(f'<p class="contagem"><b>{len(lista)}</b> pedidos para entrega</p>')
        st.text_input("Código do pedido", key="codigo_novo", placeholder="Código do pedido", label_visibility="collapsed")
        st.text_input("Nº da NF", key="nf_nova", placeholder="Nº da NF", max_chars=banco.TAMANHO_MAXIMO_NF,
                      label_visibility="collapsed")
        st.text_input("Volume", key="volume_novo", placeholder="Volume", max_chars=len(str(banco.VOLUME_MAXIMO)),
                      label_visibility="collapsed")
        st.form_submit_button("Adicionar", on_click=adicionar_pedido)
#______________________________________________________________________________________________________________________#
#Aviso quando a lista do banco mudou enquanto havia alterações não salvas nesta tela

if lista_mudou:
    with st.container(key="aviso_lista_mudou", horizontal=True, vertical_alignment="center"):
        st.html('''<div class="aviso-salvar" role="alert"><strong>A lista mudou em outro lugar.</strong>
                <span>Recarregue para ver a versão atual.</span></div>''')
        st.button("Descartar alterações e recarregar", key="descartar_alteracoes", on_click=descartar_alteracoes,
                  type="tertiary")
#______________________________________________________________________________________________________________________#
#Caixa com as ações e a tabela de pedidos

with st.container(key="caixa_pedidos"):
    nada_selecionado = selecionado not in lista
    with st.container(key="acoes_pedidos", horizontal=True):
        st.button("Mover para o topo", on_click=mover_pedido, args=("topo",), disabled=nada_selecionado, type="tertiary")
        st.button("Subir", on_click=mover_pedido, args=("subir",), disabled=nada_selecionado, type="tertiary")
        st.button("Descer", on_click=mover_pedido, args=("descer",), disabled=nada_selecionado, type="tertiary")
        st.button("Remover", on_click=mover_pedido, args=("remover",), disabled=nada_selecionado, type="tertiary")

    st.html(visual.linha_tabela(["Posição", "Pedido", "Adicionado em", "Situação", "Nº da NF", "Volume", "Entregar no"],
                                cabecalho=True, tipo="pedidos cabecalho-pedidos"))

    posicao = 1
    for codigo in lista:
        dados_pedido = dados_do_pedido(codigo)
        situacao = st.session_state["situacoes"].get(codigo, "")
        if situacao == funcoes.SITUACAO_LIBERADA:
            texto_situacao = f'<span class="situacao-ok">{html.escape(situacao)}</span>'
        else:
            texto_situacao = f'<span class="situacao-erro">{html.escape(situacao)}</span>'
        if dados_pedido["nf"] is None:
            texto_situacao += '<span class="falta-dados falta-nf">Falta o nº da NF</span>'
        if dados_pedido["volume"] is None:
            texto_situacao += '<span class="falta-dados falta-volume">Falta o volume</span>'

        celulas = [f'<span class="cinza">{posicao}</span>',
                   f'<b>{codigo}</b>',
                   f'<span class="cinza">{html.escape(st.session_state["datas_pedidos"].get(codigo, ""))}</span>',
                   texto_situacao]
        destino = dados_pedido["entregar_no"] or destino_padrao(codigo)
        with st.container(key=f"linha_{codigo}", horizontal=True):
            st.html(visual.linha_tabela(celulas, selecionada=(codigo == selecionado)))
            st.number_input(f"Nº da NF do pedido {codigo}", min_value=1, max_value=NF_MAXIMA, value=dados_pedido["nf"],
                            step=1, format="%d", placeholder="NF", key=f"nf_{codigo}", label_visibility="collapsed",
                            on_change=alterar_campo, args=(codigo, "nf"))
            st.number_input(f"Volume do pedido {codigo}", min_value=1, max_value=banco.VOLUME_MAXIMO,
                            value=dados_pedido["volume"], step=1, format="%d", placeholder="Volume",
                            key=f"volume_{codigo}", label_visibility="collapsed", on_change=alterar_campo,
                            args=(codigo, "volume"))
            st.selectbox(f"Entregar o pedido {codigo} no", list(banco.DESTINOS_VALIDOS),
                         index=list(banco.DESTINOS_VALIDOS).index(destino), format_func=NOMES_DESTINOS.get,
                         key=f"destino_{codigo}", label_visibility="collapsed", on_change=alterar_campo,
                         args=(codigo, "destino"))
            st.button("Selecionar", key=f"selecionar_{codigo}", on_click=selecionar_pedido, args=(codigo,))
        posicao += 1
#______________________________________________________________________________________________________________________#
#Avisos de erro e botão de salvar

with st.container(key="rodape_pedidos", horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
    erros = st.session_state["erros_salvar"]
    with st.container(key="aviso_pedidos"):
        if len(erros) > 0:
            linhas_erro = ""
            for erro in erros:
                linhas_erro += f"<span>{html.escape(erro)}</span>"
            st.html(f'''<div class="aviso-salvar" role="alert"><strong>Não foi possível salvar!</strong>{linhas_erro}
                    <span>Nada foi salvo.</span></div>''')

    alteracoes = st.session_state["alteracoes"]
    if alteracoes == 1:
        st.html('<span class="alteracoes">1 alteração não salva</span>')
    elif alteracoes > 1:
        st.html(f'<span class="alteracoes">{alteracoes} alterações não salvas</span>')
    st.button("Salvar", key="salvar_pedidos", on_click=salvar_lista, type="primary")
