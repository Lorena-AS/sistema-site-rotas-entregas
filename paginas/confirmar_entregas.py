from datetime import datetime
from html import escape
import streamlit as st
import banco
import funcoes
import rota
import textos
import visual

if st.session_state.get("logado") != True:
    st.stop()

TOKEN_ACESSO = st.secrets["gestaoclick"]["access_token"]
TOKEN_SECRETO = st.secrets["gestaoclick"]["secret_access_token"]
DIAS_DA_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

visual.estilo_pagina_interna()
visual.estilo_confirmar_entregas()

if "cache_transportadoras" not in st.session_state:
    st.session_state["cache_transportadoras"] = {}
#______________________________________________________________________________________________________________________#
#Chave da caixinha de cada item (pedidos e paradas extras usam chaves separadas)

def chave_do_item(item):
    if item["tipo"] == "pedido":
        return f"entregue_{item['codigo']}"
    return f"extra_{item['posicao']}"


def chave_da_transportadora(transportadora_id):
    return f"transportadora_{transportadora_id}"
#______________________________________________________________________________________________________________________#
#Busca no GestãoClick o cliente, a cidade e o endereço de cada item da rota (só o que a tela precisa)

def buscar_dados_entregas(itens):
    dados = {}
    for item in itens:
        if item["tipo"] == "pedido":
            dados[chave_do_item(item)] = funcoes.buscar_dados_do_pedido(item["codigo"], TOKEN_ACESSO, TOKEN_SECRETO)
        else:
            dados[chave_do_item(item)] = funcoes.buscar_dados_da_parada_extra(item["cliente_id"], TOKEN_ACESSO,
                                                                              TOKEN_SECRETO)

        if item["destino_tipo"] == "transportadora":
            chave = chave_da_transportadora(item["transportadora_id"])
            if chave not in dados:
                transportadora = rota.obter_transportadora(item["transportadora_id"],
                                                           st.session_state["cache_transportadoras"],
                                                           TOKEN_ACESSO, TOKEN_SECRETO)
                if transportadora is None:
                    dados[chave] = "Transportadora sem endereço cadastrado"
                else:
                    dados[chave] = funcoes.enderecos_em_texto(transportadora["endereco"])
    return dados


def com_nome_do_cliente(itens, dados):
    completos = []
    for item in itens:
        copia = dict(item)
        if copia["cliente_nome"] == "":
            copia["cliente_nome"] = dados[chave_do_item(item)]["nome"]
        if copia["destino_tipo"] == "cliente" and copia["destino_nome"] == "":
            copia["destino_nome"] = copia["cliente_nome"]
        completos.append(copia)
    return completos
#______________________________________________________________________________________________________________________#
#Ações dos botões

def marcar_todos(itens):
    for item in itens:
        st.session_state[chave_do_item(item)] = True


def confirmar(itens, dados):
    entregues = []
    extras_entregues = []
    for item in itens:
        chave = chave_do_item(item)
        if st.session_state.get(chave) == True:
            if item["tipo"] == "pedido":
                entregues.append((item["codigo"], dados[chave]["cidade"], dados[chave]["cliente_id"]))
            else:
                extras_entregues.append((item["posicao"], dados[chave]["cidade"]))

    total_marcadas, total_paradas = banco.confirmar_entregas(entregues, st.session_state["usuario"], extras_entregues)

    for item in itens:
        st.session_state.pop(chave_do_item(item), None)
    st.session_state.pop("dados_confirmacao", None)
    st.toast(f"Entregas confirmadas: {total_marcadas} de {total_paradas}.", icon=":material/check_circle:")
#______________________________________________________________________________________________________________________#
#Pedidos e paradas extras da rota pendente, na ordem da rota

visual.titulo_pagina("Confirmar entregas")

pendente = banco.data_rota_pendente()
if pendente is None:
    st.html('<p class="subtitulo-pagina">Não há rota aguardando confirmação.</p>')
    st.stop()

itens = banco.listar_itens_pendentes()
salva = banco.ler_ultima_rota()

guardado = st.session_state.get("dados_confirmacao")
if guardado is None or guardado[0] != pendente:
    try:
        with st.spinner("Buscando os clientes no GestãoClick..."):
            st.session_state["dados_confirmacao"] = (pendente, buscar_dados_entregas(itens))
    except funcoes.ErroAPI as erro:
        st.error(f"{erro} As entregas só podem ser confirmadas com os dados do GestãoClick.", icon=":material/error:")
        st.button("Tentar de novo", key="tentar_de_novo")
        st.stop()

dados = st.session_state["dados_confirmacao"][1]
paradas = banco.agrupar_em_paradas(com_nome_do_cliente(itens, dados))

data_rota = datetime.strptime(pendente, "%Y-%m-%d %H:%M")
subtitulo = f"Rota de {DIAS_DA_SEMANA[data_rota.weekday()]}, {data_rota.strftime('%d/%m/%Y')}"
if salva is not None and salva["gerada_em"][:16] == pendente:
    subtitulo += f" · saída {salva['hora_saida']}"
palavra = "entregas"
if len(paradas) == 1:
    palavra = "entrega"
st.html(f'<p class="subtitulo-pagina">{escape(subtitulo)} · <b>{len(paradas)}</b> {palavra}</p>')
#______________________________________________________________________________________________________________________#
#Lista com uma caixinha para cada item (também dentro das paradas de transportadora)

with st.container(key="caixa_confirmar"):
    with st.container(key="topo_confirmar", horizontal=True, vertical_alignment="center"):
        st.html('<span class="instrucao">Marque as paradas que foram concluídas</span>')
        st.button("Marcar todos", key="marcar_todos", type="tertiary", on_click=marcar_todos, args=(itens,))

    numero = 1
    for parada in paradas:
        if parada["destino_tipo"] == "transportadora":
            endereco = dados.get(chave_da_transportadora(parada["transportadora_id"]), "")
            exibir = rota.parada_para_exibir(parada, endereco)
            with st.container(key=f"cabeca_grupo_{numero}"):
                st.html(f'''<div class="item-entrega"><span class="numero-entrega">{numero}</span>
                        <div><b class="titulo-extra">{escape(exibir["titulo"])}<span class="etiqueta-transportadora">Transportadora</span></b>
                        <span class="linha-item">{escape(endereco)}</span></div></div>''')
            with st.container(key=f"itens_grupo_{numero}"):
                for posicao_item in range(len(parada["itens"])):
                    item = parada["itens"][posicao_item]
                    texto = exibir["itens"][posicao_item]
                    chave = chave_do_item(item)
                    detalhe = ""
                    if texto["detalhe"] != "":
                        detalhe = f'<span class="volumes-item">{escape(texto["detalhe"])}</span>'
                    with st.container(key=f"item_{chave}", horizontal=True, vertical_alignment="center"):
                        st.checkbox(textos.escapar_markdown(f"{texto['titulo']} entregue"), key=chave,
                                    label_visibility="collapsed")
                        st.html(f'''<div class="item-entrega"><span class="numero-entrega"></span>
                                <div><b>{escape(texto["titulo"])}</b>{detalhe}</div></div>''')
        else:
            item = parada["itens"][0]
            chave = chave_do_item(item)
            exibir = rota.parada_para_exibir(parada, dados[chave]["endereco"])
            with st.container(key=f"item_{chave}", horizontal=True, vertical_alignment="center"):
                if item["tipo"] == "pedido":
                    linhas = ""
                    if exibir["detalhe"] != "":
                        linhas += f'<span class="volumes-item">{escape(exibir["detalhe"])}</span>'
                    if exibir["cliente"] != "":
                        linhas += f'<span class="linha-item">{escape(exibir["cliente"])}</span>'
                    st.checkbox(f"Pedido {item['codigo']} entregue", key=chave, label_visibility="collapsed")
                    st.html(f'''<div class="item-entrega"><span class="numero-entrega">{numero}</span>
                            <div><b>{escape(exibir["titulo"])}</b>{linhas}<span class="linha-item">{escape(exibir["endereco"])}</span></div></div>''')
                else:
                    st.checkbox(f"Parada extra {numero} entregue", key=chave, label_visibility="collapsed")
                    st.html(f'''<div class="item-entrega"><span class="numero-entrega">{numero}</span>
                            <div><b class="titulo-extra">{escape(exibir["titulo"])}<span class="etiqueta-extra">Extra</span></b>
                            <span class="motivo-parada">{escape(exibir["detalhe"])}</span><span class="linha-item">{escape(exibir["endereco"])}</span></div></div>''')
        numero += 1
#______________________________________________________________________________________________________________________#
#Explicação e botão de confirmar

quantidade_pedidos = 0
quantidade_extras = 0
pedidos_nao_marcados = []
extras_nao_marcadas = []
for item in itens:
    chave = chave_do_item(item)
    if item["tipo"] == "pedido":
        quantidade_pedidos += 1
        if st.session_state.get(chave) != True:
            pedidos_nao_marcados.append(str(item["codigo"]))
    else:
        quantidade_extras += 1
        if st.session_state.get(chave) != True:
            extras_nao_marcadas.append(dados[chave]["nome"])

partes = []
if quantidade_pedidos > 0:
    if len(pedidos_nao_marcados) == 0:
        partes.append("Todos os pedidos marcados saem da Lista de Pedidos.")
    else:
        partes.append(f"Os pedidos marcados saem da lista. Os não marcados ({', '.join(pedidos_nao_marcados)}) continuam "
                      f"na Lista de Pedidos, na mesma prioridade, para a próxima rota.")
if quantidade_extras > 0:
    if len(extras_nao_marcadas) == 0:
        partes.append("As paradas extras marcadas contam como entregues.")
    else:
        partes.append(f"As paradas extras não marcadas ({', '.join(extras_nao_marcadas)}) não voltam para a lista: "
                      f"são descartadas e ficam registradas no histórico.")
explicacao = " ".join(partes)

with st.container(key="rodape_confirmar", horizontal=True, vertical_alignment="center"):
    st.html(f'<p class="explicacao-confirmar">{escape(explicacao)}</p>')
    st.button("Confirmar entregas", key="enviar_confirmacao", type="primary", on_click=confirmar, args=(itens, dados))
