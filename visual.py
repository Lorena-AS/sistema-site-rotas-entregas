from datetime import date
from html import escape
import streamlit as st
from pathlib import Path
import marca

PASTA_TELAS = Path(__file__).parent / "telas"
#______________________________________________________________________________________________________________________#
#Estilo geral: esconde os menus padrão do Streamlit, deixa a janela de login escura e prepara os cards e o rodapé

def aplicar_estilo():
    css = """
    <style>
    [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"], #MainMenu, footer {
        display: none;
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        max-width: 1160px;
        padding-top: 24px;
    }
    /* Janela de login escura e translúcida, no centro da tela */
    [data-testid="stDialog"] {
        align-items: center;
        background: rgba(5, 10, 20, 0.45);
    }
    [data-testid="stDialog"] > div, [data-testid="stDialog"] [role="dialog"] {
        width: 420px;
        max-width: calc(100vw - 48px);
    }
    [data-testid="stDialog"] > div {
        background: transparent;
    }
    [data-testid="stDialog"] [role="dialog"] {
        background: rgba(255, 255, 255, 0.16);
        backdrop-filter: blur(18px);
        border: none;
        border-radius: 20px;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
        color: #FFFFFF;
    }
    [data-testid="stDialog"] [role="dialog"] > h2 {
        padding: 36px 92px 0 36px;
        color: #FFFFFF;
    }
    [data-testid="stDialog"] [role="dialog"] > h2 p {
        font-size: 24px;
        font-weight: 600;
        line-height: 44px;
    }
    [data-testid="stDialog"] [role="dialog"] > div {
        padding: 20px 36px 36px;
    }
    [data-testid="stDialog"] button[aria-label="Close"] {
        top: 36px;
        right: 36px;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.08);
        color: #FFFFFF;
    }
    [data-testid="stDialog"] button[aria-label="Close"] svg {
        width: 14px;
        height: 14px;
    }
    [data-testid="stDialog"] [data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    [data-testid="stDialog"] [data-testid="stForm"] [data-testid="stVerticalBlock"] {
        gap: 20px;
    }
    [data-testid="stDialog"] label p {
        font-size: 14px;
        font-weight: 500;
        color: #C7D2E1;
    }
    [data-testid="stDialog"] [data-testid="stTextInputRootElement"] {
        height: 50px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.22);
    }
    [data-testid="stDialog"] input {
        font-size: 16px;
        color: #FFFFFF;
        -webkit-text-fill-color: #FFFFFF;
    }
    [data-testid="stDialog"] input:-webkit-autofill {
        -webkit-text-fill-color: #FFFFFF;
        caret-color: #FFFFFF;
        transition: background-color 9999s ease-in-out 0s;
    }
    [data-testid="stDialog"] input::placeholder {
        color: #8FA3BF;
        -webkit-text-fill-color: #8FA3BF;
    }
    [data-testid="stDialog"] [data-testid="InputInstructions"] {
        color: #8FA3BF;
    }
    [data-testid="stDialog"] [data-testid="stTextInputRootElement"] button {
        background: transparent;
        color: #C7D2E1;
    }
    [data-testid="stDialog"] [data-testid="stFormSubmitButton"] button {
        min-height: 48px;
        border-radius: 10px;
    }
    [data-testid="stDialog"] [data-testid="stFormSubmitButton"] button p {
        font-size: 16px;
        font-weight: 600;
    }
    [data-testid="stDialog"] [data-testid="stAlertContainer"] {
        padding: 12px 14px;
        border-radius: 10px;
        background: rgba(239, 68, 68, 0.16);
        border: 1px solid rgba(248, 113, 113, 0.35);
    }
    [data-testid="stDialog"] [data-testid="stAlertContainer"] p, [data-testid="stDialog"] [data-testid="stAlertContainer"] svg {
        font-size: 14px;
        color: #FECACA;
        fill: #FECACA;
    }
    .aviso-senha {
        margin: 0;
        text-align: center;
        font-size: 14px;
        color: #C7D2E1;
    }
    /* Rodapé: cores das páginas claras (nas escuras, o fundo_escuro troca) */
    .rodape {
        margin-top: 48px;
        padding: 20px 0;
        line-height: normal;
        border-top: 1px solid #E3E8EF;
        border-image: linear-gradient(#E3E8EF, #E3E8EF) 1 / 1px 0 0 0 / 0 100vw;
        text-align: center;
        font-size: 13px;
        color: #8A97A8;
    }
    /* Cards clicáveis: um botão invisível cobre o card inteiro */
    [class*="st-key-card_"] {
        position: relative;
        gap: 0;
    }
    [class*="st-key-card_"] [data-testid="stHtml"] {
        line-height: normal;
    }
    [class*="st-key-botao_"] {
        position: absolute;
        inset: 0;
        width: 100% !important;
        height: 100% !important;
        z-index: 5;
    }
    [class*="st-key-botao_"] div, [class*="st-key-botao_"] button, [class*="st-key-botao_"] a {
        width: 100%;
        height: 100%;
    }
    [class*="st-key-botao_"] button, [class*="st-key-botao_"] a {
        opacity: 0;
        cursor: pointer;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Fundo em degradê escuro (tela de entrada e Início)

def fundo_escuro():
    css = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #111827 0%, #0F2A4A 45%, #0B5CA8 100%);
    }
    [data-testid="stHeader"]:has([data-testid="stTopNav"]) {
        background: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .block-container {
        max-width: 1200px;
    }
    .rodape {
        border-image-source: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08));
        color: #8FA3BF;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Visual da página Início: degradê do painel, botão do usuário em pílula e espaços entre os cards

def fundo_painel():
    css = """
    <style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"]:has([data-testid="stTopNav"]) {
        background: linear-gradient(135deg, #1A2740 0%, #163A66 45%, #1668C7 100%);
        background-attachment: fixed;
    }
    .block-container {
        padding: 72px 24px 0;
    }
    .st-key-painel {
        gap: 48px;
    }
    .st-key-painel [data-testid="stHorizontalBlock"] {
        gap: 24px;
    }
    .st-key-usuario button {
        min-height: 48px;
        padding: 0 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        font-size: 16px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Barra do topo azul-marinho com o menu e o botão do usuário (depois do login)

def estilo_menu():
    css = """
    <style>
    [data-testid="stHeader"] {
        background: #0F2A4A;
        height: 64px;
        padding: 0 clamp(16px, 3vw, 48px);
    }
    [data-testid="stToolbar"] {
        height: 64px;
    }
    [data-testid="stHeaderLogo"] {
        height: 27px;
    }
    [data-testid="stTopNav"] {
        margin-left: clamp(20px, 4vw, 56px);
    }
    [data-testid="stTopNavLink"] {
        height: 64px;
        padding: 0 4px;
        margin-right: clamp(16px, 2.2vw, 32px);
        border-radius: 0;
        background: transparent;
    }
    [data-testid="stTopNavLink"]:hover {
        background: transparent;
    }
    [data-testid="stTopNavLink"] p {
        font-size: 15px;
        font-weight: 500;
        color: #AFC3DA;
    }
    [data-testid="stTopNavLink"]:hover p {
        color: #FFFFFF;
    }
    [data-testid="stTopNavLink"][aria-current="page"] {
        box-shadow: inset 0 -3px 0 #4FA3FF;
    }
    [data-testid="stTopNavLink"][aria-current="page"] p {
        font-weight: 600;
        color: #FFFFFF;
    }
    .st-key-usuario {
        position: fixed;
        top: 12px;
        right: clamp(16px, 3vw, 48px);
        width: auto;
        z-index: 999991;
    }
    .st-key-usuario button {
        background: transparent;
        border: none;
        color: #FFFFFF;
    }
    .st-key-usuario button:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #FFFFFF;
    }
    .block-container {
        padding-top: clamp(28px, 4vw, 48px);
    }
        /* Aviso de rota aguardando confirmação (aparece no topo das páginas) */
    div.st-key-aviso_pendente {
        flex-wrap: nowrap;
        gap: 12px;
        margin-top: 48px;
        padding: 6px 16px;
        border-radius: 8px;
        background: #DBEAFE;
    }
    div.st-key-aviso_pendente > div {
        width: auto;
    }
    .texto-aviso-pendente {
        font-size: 14px;
        font-weight: 600;
        color: #0B5CA8;
    }
    .st-key-ir_confirmar button p {
        font-size: 14px;
        font-weight: 700;
        color: #0F2A4A;
        text-decoration: underline;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Mostra o topo da tela de entrada com a logo e devolve o espaço onde entra o botão

def cabecalho():
    topo = st.container(key="topo_entrada", horizontal=True, horizontal_alignment="distribute", vertical_alignment="center")
    dados_marca = marca.ler_marca()
    endereco_logo = marca.logo_em_data_uri(dados_marca)
    with topo:
        if endereco_logo is not None:
            st.image(endereco_logo, width=272)
        else:
            st.html('<span style="font-family: Inter, sans-serif; font-size: 24px; font-weight: 700; color: #FFFFFF">'
                    + marca.logo_em_img(40, dados_marca) + '</span>')
    return topo
#______________________________________________________________________________________________________________________#
#Mostra o rodapé com os direitos da empresa

def rodape():
    st.markdown('<div class="rodape">' + marca.texto_rodape(date.today().year) + '</div>', unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Mostra a tela de entrada (antes do login)

def tela_entrada():
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700;800&family=Montserrat:wght@400;500&display=swap');
    .block-container {
        max-width: 1200px;
        padding: 97px 0 0;
    }
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
        gap: 0;
    }
    .st-key-topo_entrada {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999990;
        height: 97px;
        box-sizing: border-box;
        padding: 24px 48px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        background: linear-gradient(135deg, #111827 0%, #0F2A4A 45%, #0B5CA8 100%);
        background-attachment: fixed;
    }
    .st-key-topo_entrada [data-testid="stElementToolbar"] {
        display: none;
    }
    .st-key-topo_entrada [data-testid="stBaseButton-primary"] {
        min-height: 48px;
        padding: 0 28px;
        border: none;
        border-radius: 999px;
        background: #3B82F6;
    }
    .st-key-topo_entrada [data-testid="stBaseButton-primary"] p {
        font-size: 16px;
        font-weight: 600;
    }
    .rodape {
        margin-top: 0;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    html = (PASTA_TELAS / "entrada.html").read_text(encoding="utf-8")
    st.html(html)
#______________________________________________________________________________________________________________________#
#Mostra o título do painel

def titulo_painel():
    st.html("""
    <div style="display:flex; flex-direction:column; align-items:center; gap:10px; color:#FFFFFF;">
        <h1 style="margin:0; padding:0; text-align:center; font-family:Inter, sans-serif; font-size:36px; font-weight:500; letter-spacing:-0.3px; line-height:1.2; color:#FFFFFF;">
            Crie sua rota com <span style="color:#4FA3FF;">eficiência</span>!
        </h1>
        <p style="margin:0; text-align:center; font-size:20px; color:#C7D2E1;">Aonde gostaria de ir?</p>
    </div>
    """)
#______________________________________________________________________________________________________________________#
#Mostra um card que abre uma página do sistema e devolve True quando é clicado

def card(arquivo_html, chave):
    with st.container(key="card_" + chave):
        html = (PASTA_TELAS / arquivo_html).read_text(encoding="utf-8")
        st.html(html)
        clicado = st.button("Abrir", key="botao_" + chave)
    return clicado
#______________________________________________________________________________________________________________________#
#Mostra um card que abre um site numa nova guia

def card_link(arquivo_html, chave, endereco):
    with st.container(key="card_" + chave):
        html = (PASTA_TELAS / arquivo_html).read_text(encoding="utf-8")
        st.html(html)
        with st.container(key="botao_" + chave):
            st.link_button("Abrir", endereco)
#______________________________________________________________________________________________________________________#
#Visual das páginas internas claras (Pedidos, Gerar rota e Histórico)

def estilo_pagina_interna():
    css = """
    <style>
    .block-container {
        padding: 0 clamp(16px, 3vw, 32px) 64px;
    }
    .titulo-pagina {
        margin: 0;
        padding: clamp(28px, 4vw, 48px) 0 clamp(20px, 2.5vw, 28px);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: clamp(26px, 1.4rem + 1.2vw, 38px);
        font-weight: 700;
        letter-spacing: -0.6px;
        line-height: 1.15;
        color: #0F2A4A;
        margin-bottom: -16px;
    }
    /* Linha de adicionar pedido */
    div.st-key-linha_adicionar {
        flex-wrap: nowrap;
        gap: 8px;
        margin-bottom: 4px;
    }
    div.st-key-linha_adicionar > div:first-child {
        flex: 1 1 0;
        min-width: 0;
    }
    div.st-key-linha_adicionar > .st-key-codigo_novo {
        flex: 0 1 320px;
    }
    div.st-key-linha_adicionar > .st-key-nf_nova {
        flex: 0 1 200px;
    }
    div.st-key-linha_adicionar > .st-key-volume_novo {
        flex: 0 1 140px;
    }
    .contagem {
        margin: 0;
        font-size: clamp(17px, 0.95rem + 0.35vw, 21px);
        color: #5B6B82;
    }
    .contagem b {
        color: #0B5CA8;
    }
    .st-key-linha_adicionar [data-testid="stTextInputRootElement"] {
        height: 44px;
        border: 1px solid #E3E8EF;
        background: #FFFFFF;
    }
    .st-key-linha_adicionar input {
        font-size: 15px;
    }
    .st-key-linha_adicionar button, .st-key-salvar_pedidos button {
        min-height: 44px;
        padding: 0 20px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    div.st-key-linha_adicionar button:hover, div.st-key-linha_adicionar button:focus,
    div.st-key-salvar_pedidos button:hover, div.st-key-salvar_pedidos button:focus {
        border: none;
        background: #163A66;
        color: #FFFFFF;
    }
    .st-key-salvar_pedidos button {
        min-height: 48px;
        padding: 0 28px;
    }
    .st-key-linha_adicionar button p, .st-key-salvar_pedidos button p {
        font-size: 15px;
        font-weight: 600;
    }
    /* Caixa com o canto dobrado */
    [class*="st-key-caixa_"] {
        position: relative;
        gap: 0;
        padding: 24px;
        border-radius: 12px 0 12px 12px;
        background: linear-gradient(225deg, transparent 24px, #EFF2FD 100%);
        filter: drop-shadow(0 4px 10px rgba(15, 42, 74, 0.08));
    }
    [class*="st-key-caixa_"]::before {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 34px;
        height: 34px;
        background: linear-gradient(225deg, transparent 50%, #B8C6D8 50%, #D8E0EB 100%);
        border-bottom-left-radius: 8px;
    }
    /* Botões de ação acima da tabela */
    .st-key-acoes_pedidos {
        gap: 4px 8px;
        padding-bottom: 8px;
        margin-bottom: 8px;
        border-bottom: 1px solid #E3E8EF;
    }
    .st-key-acoes_pedidos button {
        min-height: 36px;
        padding: 0 10px;
    }
    .st-key-acoes_pedidos button p {
        font-size: 14px;
        font-weight: 600;
        color: #0B5CA8;
    }
    .st-key-acoes_pedidos button:disabled p {
        color: #9FB3C8;
    }
    /* Tabela: cada linha é HTML com um botão invisível por cima */
    .linha-tabela {
        display: grid;
        grid-template-columns: 199fr 184fr 307fr 359fr;
        font-size: 15px;
        line-height: normal;
        color: #0F2A4A;
    }
    .linha-tabela > div {
        padding: 14px 16px;
        border-bottom: 1px solid #E3E8EF;
    }
    .linha-tabela.cabecalho > div {
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 700;
        color: #0B5CA8;
    }
    .linha-tabela.selecionada {
        background: #DBEAFE;
    }
    .linha-tabela b {
        font-weight: 600;
    }
    .cinza, .situacao-ok {
        color: #5B6B82;
    }
    .situacao-erro {
        font-weight: 600;
        color: #C0392B;
    }
    [class*="st-key-linha_"]:not(.st-key-linha_adicionar) {
        position: relative;
        gap: 0;
    }
    [class*="st-key-selecionar_"] {
        position: absolute;
        inset: 0;
        z-index: 5;
    }
    [class*="st-key-selecionar_"] button {
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
    }
    [data-testid="stVerticalBlock"]:has(> [class*="st-key-linha_"]:not(.st-key-linha_adicionar)) {
        gap: 0;
    }
    /* Tabela de pedidos: NF, volume e local de entrega editáveis ficam por cima do botão invisível */
    .linha-tabela.pedidos.cabecalho-pedidos {
        grid-template-columns: 199fr 184fr 307fr 359fr 150px 120px 180px;
    }
    .st-key-caixa_pedidos [class*="st-key-linha_"] {
        flex-wrap: nowrap;
        align-items: stretch;
    }
    .st-key-caixa_pedidos [class*="st-key-linha_"] > div:first-child {
        flex: 1 1 0;
        min-width: 0;
    }
    .st-key-caixa_pedidos [class*="st-key-nf_"], .st-key-caixa_pedidos [class*="st-key-volume_"],
    .st-key-caixa_pedidos [class*="st-key-destino_"] {
        position: relative;
        z-index: 6;
        justify-content: center;
        padding: 6px 8px;
        border-bottom: 1px solid #E3E8EF;
    }
    .st-key-caixa_pedidos [class*="st-key-nf_"] {
        flex: 0 0 150px;
        width: 150px;
    }
    .st-key-caixa_pedidos [class*="st-key-volume_"] {
        flex: 0 0 120px;
        width: 120px;
    }
    .st-key-caixa_pedidos [class*="st-key-destino_"] {
        flex: 0 0 180px;
        width: 180px;
    }
    .st-key-caixa_pedidos [data-baseweb="input"], .st-key-caixa_pedidos [data-baseweb="select"] > div {
        min-height: 38px;
        border: 1px solid #E3E8EF;
        background: #FFFFFF;
        font-size: 14px;
    }
    .st-key-caixa_pedidos [data-testid="stNumberInputStepDown"], .st-key-caixa_pedidos [data-testid="stNumberInputStepUp"] {
        display: none;
    }
    .st-key-caixa_pedidos [class*="st-key-linha_"]:has(.linha-tabela.selecionada) {
        background: #DBEAFE;
    }
    .falta-dados {
        display: block;
        margin-top: 2px;
        font-size: 12px;
        font-weight: 600;
        color: #C0392B;
    }
    .st-key-caixa_pedidos [class*="st-key-linha_"]:has(.falta-nf) [class*="st-key-nf_"] [data-baseweb="input"],
    .st-key-caixa_pedidos [class*="st-key-linha_"]:has(.falta-volume) [class*="st-key-volume_"] [data-baseweb="input"] {
        border-color: #C0392B;
    }
    /* Rodapé da página: aviso de erro e botão salvar */
    div.st-key-rodape_pedidos {
        flex-wrap: nowrap;
        gap: 16px;
        padding-top: 8px;
    }
    div.st-key-rodape_pedidos > div:has(.st-key-aviso_pedidos) {
        flex: 1 1 0;
    }
    div.st-key-rodape_pedidos > div:has(.alteracoes) {
        flex: 0 0 auto;
        width: auto;
    }
    .aviso-salvar {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 14px;
        line-height: 1.5;
        color: #5B6B82;
    }
    .aviso-salvar strong {
        font-size: 15px;
        font-weight: 600;
        color: #C0392B;
    }
    .alteracoes {
        font-size: 14px;
        color: #8A97A8;
    }
    /* Etiqueta "Extra" das paradas extras (Gerar rota e Confirmar entregas) */
    .etiqueta-extra {
        padding: 1px 8px;
        border-radius: 999px;
        background: #DCE8F7;
        color: #0B5CA8;
        font-size: 11px;
        font-weight: 700;
    }
    /* Etiquetas "Transportadora" e "Cliente" (Gerar rota, Confirmar entregas e Histórico) */
    .etiqueta-transportadora, .etiqueta-cliente {
        padding: 1px 8px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        white-space: nowrap;
    }
    .etiqueta-transportadora {
        background: #E6EBF1;
        color: #42536B;
    }
    .etiqueta-cliente {
        background: #EEF1F5;
        color: #42536B;
    }
    /* Aviso de lista alterada em outro lugar (página Pedidos) */
    div.st-key-aviso_lista_mudou {
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 8px 16px;
        padding: 12px 0;
    }
    div.st-key-aviso_lista_mudou > div {
        width: auto;
    }
    .st-key-descartar_alteracoes button p {
        font-size: 14px;
        font-weight: 600;
        color: #0B5CA8;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Mostra o título das páginas internas

def titulo_pagina(texto):
    st.html(f'<h1 class="titulo-pagina">{texto}</h1>')
#______________________________________________________________________________________________________________________#
#Monta uma linha da tabela em HTML (as células já chegam prontas e seguras)

def linha_tabela(celulas, cabecalho=False, selecionada=False, tipo="pedidos"):
    classes = "linha-tabela " + tipo
    if cabecalho:
        classes += " cabecalho"
    if selecionada:
        classes += " selecionada"

    html = f'<div class="{classes}">'
    for celula in celulas:
        html += f"<div>{celula}</div>"
    html += "</div>"
    return html
#______________________________________________________________________________________________________________________#
#Visual da página Gerar rota: formulário, barra da cota, números animados e lista de paradas

def estilo_gerar_rota():
    css = """
    <style>
    /* Contador animado: o número sobe de 0 até o valor final (--alvo) */
    @property --n {
        syntax: '<integer>';
        inherits: false;
        initial-value: 0;
    }
    @keyframes conta {
        from { --n: 0; }
        to { --n: var(--alvo); }
    }
    .conta {
        animation: conta 1.4s cubic-bezier(.2, .7, .2, 1) forwards;
        counter-reset: v var(--n);
    }
    .conta::after {
        content: counter(v);
    }
    .conta.hora {
        counter-reset: h round(down, var(--n) / 60, 1) m mod(var(--n), 60);
    }
    .conta.hora::after {
        content: counter(h) "h" counter(m, decimal-leading-zero);
    }
    .so-leitor {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0 0 0 0);
        white-space: nowrap;
    }
    @media (prefers-reduced-motion: reduce) {
        .conta { animation: none; --n: var(--alvo); }
    }
        /* Linha do título com o botão de PDF (imagem colorida colocada pelo CSS) */
    div.st-key-topo_rota {
        flex-wrap: nowrap;
        margin-bottom: -16px;
        padding-bottom: clamp(20px, 2.5vw, 28px);
    }
    div.st-key-topo_rota .titulo-pagina {
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .st-key-baixar_pdf button {
        width: 52px;
        height: 52px;
        min-height: 52px;
        padding: 4px;
        border: 1px solid #E3E8EF;
        border-radius: 10px;
        background: #EDF1F7 url("app/static/pdf.svg?v=1") center / 40px 40px no-repeat;
    }
    .st-key-baixar_pdf button:hover {
        border-color: #0B5CA8;
        background-color: #EDF1F7;
    }
    .st-key-baixar_pdf button:disabled {
        opacity: 0.45;
        cursor: not-allowed;
    }
    .st-key-baixar_pdf button p {
        font-size: 0;
    }
    /* Formulário (a caixa não tem o canto dobrado: só sombra) */
    div.st-key-caixa_formulario {
        flex-wrap: wrap;
        gap: 16px;
        padding: 24px;
        border-radius: 12px;
        background: #EDF1F7;
        filter: none;
        box-shadow: 0 4px 16px rgba(15, 42, 74, 0.08);
    }
    div.st-key-caixa_formulario::before {
        display: none;
    }
    div.st-key-caixa_formulario > .st-key-quantidade_rota {
        flex: 1 1 160px;
    }
    div.st-key-caixa_formulario > .st-key-hora_saida, div.st-key-caixa_formulario > .st-key-hora_retorno {
        flex: 1 1 140px;
    }
    .st-key-caixa_formulario label p {
        font-size: 13px;
        font-weight: 600;
        color: #5B6B82;
    }
    .st-key-caixa_formulario [data-baseweb="input"], .st-key-caixa_formulario [data-baseweb="select"] > div {
        min-height: 44px;
        border: 1px solid #E3E8EF;
        background: #FFFFFF;
    }
    .st-key-caixa_formulario input {
        font-size: 15px;
    }
    .st-key-caixa_formulario [data-testid="stNumberInputStepDown"], .st-key-caixa_formulario [data-testid="stNumberInputStepUp"] {
        display: none;
    }
    .st-key-caixa_formulario [data-testid="stFormSubmitButton"] button {
        min-height: 44px;
        padding: 0 32px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    .st-key-caixa_formulario [data-testid="stFormSubmitButton"] button:hover {
        background: #163A66;
        color: #FFFFFF;
    }
    .st-key-caixa_formulario [data-testid="stFormSubmitButton"] button p {
        font-size: 15px;
        font-weight: 600;
    }
    /* Barra da cota com o caminhão */
    .cota {
        margin-top: 16px;
        font-size: 13px;
        color: #5B6B82;
    }
    .cota-topo {
        display: flex;
        justify-content: space-between;
    }
    .cota-topo b {
        font-weight: 600;
        color: #0F2A4A;
    }
    .cota-trilho {
        position: relative;
        margin: 22px 0 8px;
        height: 4px;
        border-radius: 2px;
        background: #FFFFFF;
    }
    .cota-trilho > div {
        height: 100%;
        border-radius: 2px;
        background: #3B82F6;
    }
    .cota-trilho > img {
        position: absolute;
        bottom: 3px;
        width: 30px;
        height: 18px;
        transform: translateX(-70%);
    }
    .cota-texto {
        color: #8A97A8;
    }
    /* Resultado da rota */
    .resultado-rota {
        color: #0F2A4A;
        line-height: normal;
    }
    .resultado-topo {
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px 24px;
        margin-top: clamp(40px, 5vw, 64px);
        padding-bottom: 20px;
    }
    .resultado-topo h2 {
        margin: 0;
        padding: 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: clamp(20px, 1rem + 0.8vw, 26px);
        font-weight: 600;
        color: #0F2A4A;
    }
    .situacao-rota {
        width: 267px;
        font-size: 15px;
        font-weight: 600;
        text-align: center;
        color: #0B5CA8;
        position: relative;
        left: 12px;
    }
    .situacao-rota.erro {
        color: #C0392B;
    }
    .numeros-rota {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 24px clamp(32px, 5vw, 72px);
        padding: 28px 0 36px;
    }
    .numero {
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 120px;
    }
    .numero > span:first-child {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: clamp(22px, 1.1rem + 1vw, 32px);
        font-weight: 600;
        line-height: 1;
        letter-spacing: -1px;
    }
    .numero > span:last-child {
        font-size: 14px;
        color: #5B6B82;
    }
    .botao-maps {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 267px;
        height: 50px;
        margin-left: auto;
        position: relative;
        left: 12px;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
        font-size: 15px;
        font-weight: 600;
        text-decoration: none;
    }
    .botao-maps:hover {
        background: #163A66;
        color: #FFFFFF;
    }
    .paradas-e-avisos {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-start;
        gap: 40px clamp(40px, 6vw, 88px);
    }
    .caixa-paradas {
        flex: 999 1 520px;
        position: relative;
        padding: 0 24px 12px;
        border-radius: 12px 0 12px 12px;
        background: linear-gradient(225deg, transparent 24px, #EFF2FD 100%);
        filter: drop-shadow(0 4px 10px rgba(15, 42, 74, 0.08));
    }
    .caixa-paradas::before {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 34px;
        height: 34px;
        background: linear-gradient(225deg, transparent 50%, #B8C6D8 50%, #D8E0EB 100%);
        border-bottom-left-radius: 8px;
    }
    .caixa-paradas ol {
        list-style: none;
        margin: 0;
        padding: 0;
    }
    .caixa-paradas li {
        display: grid;
        grid-template-columns: 56px 1fr;
        gap: 16px;
        margin: 0;
        padding: 14px 0;
        border-bottom: 1px solid #E3E8EF;
    }
    .caixa-paradas li.saida {
        align-items: baseline;
    }
    .rotulo-saida {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 15px;
        font-weight: 700;
        color: #0B5CA8;
    }
    .numero-parada {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 600;
        color: #0B5CA8;
    }
    .dados-parada {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .dados-parada b {
        font-size: 15px;
        font-weight: 600;
    }
    .dados-parada span, .hora-saida {
        font-size: 14px;
        color: #5B6B82;
    }
    .hora-saida {
        font-weight: 600;
        color: #0F2A4A;
    }
    .ficaram {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 267px;
        padding-top: 12px;
        font-size: 14px;
        line-height: 1.5;
        text-align: center;
        color: #5B6B82;
        position: relative;
        left: 11px;
    }
    .ficaram strong {
        font-size: 15px;
        font-weight: 600;
        color: #0F2A4A;
    }
    .ficaram b {
        color: #0F2A4A;
    }
    .retorno-previsto {
        display: flex;
        align-items: baseline;
        gap: 8px;
        padding: 14px 0;
        border-bottom: 1px solid #E3E8EF;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 13px;
        font-weight: 700;
    }
    .retorno-previsto span:first-child {
        color: #0B5CA8;
    }
    /* Caixa Paradas extras */
    div.st-key-caixa_extras {
        margin-top: 16px;
        gap: 16px;
        padding: 20px 24px;
        border-radius: 12px;
        background: #EDF1F7;
        box-shadow: 0 4px 16px rgba(15, 42, 74, 0.08);
    }
    div.st-key-topo_extras {
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 8px 24px;
    }
    div.st-key-topo_extras > div {
        width: auto;
    }
    .titulo-extras {
        margin: 0;
        padding: 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 17px;
        font-weight: 600;
        line-height: normal;
        color: #0F2A4A;
    }
    .st-key-abrir_extras button {
        min-height: 44px;
        padding: 0 16px;
        border: none;
        border-radius: 8px;
        background: transparent;
        color: #0B5CA8;
    }
    .st-key-abrir_extras button:hover, .st-key-abrir_extras button:focus {
        border: none;
        background: transparent;
        color: #0B5CA8;
    }
    .st-key-abrir_extras button p {
        font-size: 15px;
        font-weight: 600;
    }
    /* Painel de busca */
    div.st-key-painel_extras {
        padding-top: 16px;
        border-top: 1px solid #D5DCE5;
    }
    .st-key-painel_extras [data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    div.st-key-campos_busca {
        flex-wrap: wrap;
        align-items: flex-end;
        gap: 16px;
    }
    div.st-key-campos_busca > div {
        width: auto;
    }
    div.st-key-campos_busca > div:first-child {
        flex: 0 1 280px;
    }
    .st-key-caixa_extras [data-testid="stWidgetLabel"] {
        min-height: 0;
        margin-bottom: 6px;
    }
    .st-key-caixa_extras label p {
        font-size: 13px;
        font-weight: 600;
        color: #5B6B82;
    }
    .st-key-caixa_extras [data-testid="stTextInputRootElement"], .st-key-caixa_extras [data-baseweb="select"] > div {
        min-height: 44px;
        border: 1px solid #E3E8EF;
        border-radius: 8px;
        background: #FFFFFF;
    }
    .st-key-caixa_extras input {
        padding: 0 14px;
        font-size: 15px;
        color: #0F2A4A;
    }
    .st-key-caixa_extras [data-baseweb="select"] {
        font-size: 15px;
        color: #0F2A4A;
    }
    .st-key-caixa_extras [data-testid="InputInstructions"] {
        display: none;
    }
    .st-key-buscar_extra button {
        min-height: 44px;
        padding: 0 24px;
        border: 1px solid #0F2A4A;
        border-radius: 8px;
        background: #FFFFFF;
        color: #0F2A4A;
    }
    .st-key-buscar_extra button:hover, .st-key-buscar_extra button:focus {
        border: 1px solid #0F2A4A;
        background: #FFFFFF;
        color: #0F2A4A;
    }
    .st-key-buscar_extra button p, .st-key-adicionar_extra button p {
        font-size: 15px;
        font-weight: 600;
    }
    .st-key-cancelar_extra button {
        min-height: 44px;
        padding: 0 12px;
        border: none;
        background: transparent;
        color: #5B6B82;
    }
    .st-key-cancelar_extra button:hover, .st-key-cancelar_extra button:focus {
        border: none;
        background: transparent;
        color: #5B6B82;
    }
    .st-key-cancelar_extra button p {
        font-size: 14px;
        font-weight: 500;
    }
    /* Aviso da busca */
    .aviso-extras {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 14px;
        line-height: 1.5;
        color: #5B6B82;
    }
    .aviso-extras strong {
        font-size: 15px;
        font-weight: 600;
        color: #C0392B;
    }
    /* Cartão do cliente encontrado */
    div.st-key-cartao_extra {
        gap: 16px;
        padding: 16px 20px;
        border: 1px solid #E3E8EF;
        border-radius: 10px;
        background: #FFFFFF;
    }
    div.st-key-cartao_cliente {
        flex-wrap: wrap;
        align-items: flex-end;
        gap: 16px 24px;
    }
    div.st-key-cartao_cliente > div:first-child {
        flex: 1 1 320px;
    }
    div.st-key-cartao_cliente > .st-key-motivo_extra {
        flex: 1 1 240px;
    }
    div.st-key-cartao_cliente > .st-key-nf_extra {
        flex: 0 1 160px;
    }
    div.st-key-cartao_cliente > .st-key-volume_extra {
        flex: 0 1 120px;
    }
    /* Busca da transportadora da parada extra */
    div.st-key-busca_transportadora {
        flex-wrap: wrap;
        align-items: flex-end;
        gap: 16px;
    }
    div.st-key-busca_transportadora > div {
        width: auto;
    }
    div.st-key-busca_transportadora > .st-key-nome_transportadora {
        flex: 0 1 320px;
    }
    .st-key-buscar_transportadora button {
        min-height: 44px;
        padding: 0 24px;
        border: 1px solid #0F2A4A;
        border-radius: 8px;
        background: #FFFFFF;
        color: #0F2A4A;
    }
    .st-key-buscar_transportadora button:hover, .st-key-buscar_transportadora button:focus {
        border: 1px solid #0F2A4A;
        background: #FFFFFF;
        color: #0F2A4A;
    }
    .st-key-buscar_transportadora button p {
        font-size: 15px;
        font-weight: 600;
    }
    .st-key-limpar_transportadora button {
        min-height: 44px;
        padding: 0 12px;
        border: none;
        background: transparent;
        color: #5B6B82;
    }
    .st-key-limpar_transportadora button:hover, .st-key-limpar_transportadora button:focus {
        border: none;
        background: transparent;
        color: #5B6B82;
    }
    .st-key-limpar_transportadora button p {
        font-size: 14px;
        font-weight: 500;
    }
    .ajuda-extras {
        margin: 0;
        font-size: 13px;
        line-height: 1.5;
        color: #8A97A8;
    }
    .st-key-escolha_transportadora label p {
        font-size: 14px;
        font-weight: 400;
        color: #0F2A4A;
    }
    div.st-key-rodape_cartao {
        justify-content: flex-end;
    }
    div.st-key-rodape_cartao > div {
        width: auto;
    }
    .dados-cliente {
        display: flex;
        flex-direction: column;
        gap: 2px;
        line-height: normal;
    }
    .dados-cliente .rotulo-cliente {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.4px;
        color: #5B6B82;
    }
    .dados-cliente b {
        font-size: 15px;
        font-weight: 600;
        color: #0F2A4A;
    }
    .dados-cliente span {
        font-size: 14px;
        color: #5B6B82;
    }
    .st-key-adicionar_extra button {
        min-height: 44px;
        padding: 0 24px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    .st-key-adicionar_extra button:hover, .st-key-adicionar_extra button:focus {
        border: none;
        background: #163A66;
        color: #FFFFFF;
    }
    /* Paradas extras adicionadas */
    [class*="st-key-linha_extra_"] {
        flex-wrap: wrap;
        align-items: center;
        gap: 8px 16px;
        padding: 12px 0;
        border-top: 1px solid #D5DCE5;
    }
    [class*="st-key-linha_extra_"] > div:first-child {
        flex: 1 1 300px;
        min-width: 0;
    }
    [class*="st-key-linha_extra_"] > div:last-child {
        width: auto;
    }
    .linha-extra {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px 16px;
        line-height: normal;
    }
    .textos-extra {
        flex: 1 1 300px;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .textos-extra b {
        font-size: 15px;
        font-weight: 600;
        color: #0F2A4A;
    }
    .textos-extra span {
        font-size: 14px;
        color: #5B6B82;
    }
    .etiqueta-extra.lista {
        padding: 1px 8px;
        font-size: 11px;
    }
    [class*="st-key-remover_extra_"] button {
        min-height: 44px;
        padding: 0 12px;
        border: none;
        background: transparent;
    }
    [class*="st-key-remover_extra_"] button:hover, [class*="st-key-remover_extra_"] button:focus {
        border: none;
        background: transparent;
    }
    [class*="st-key-remover_extra_"] button p {
        font-size: 14px;
        font-weight: 600;
        color: #C0392B;
    }
    /* Parada extra no resultado da rota */
    .dados-parada .titulo-extra {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .dados-parada .etiqueta-extra {
        font-size: 11px;
        color: #0B5CA8;
    }
    .dados-parada .motivo-parada {
        color: #0F2A4A;
    }
    /* Parada de transportadora no resultado da rota: etiqueta e itens de dentro */
    .dados-parada .etiqueta-transportadora {
        font-size: 11px;
        color: #42536B;
    }
    .dados-parada .volumes-parada {
        color: #0F2A4A;
    }
    .caixa-paradas .itens-parada {
        display: flex;
        flex-direction: column;
        gap: 8px;
        list-style: none;
        margin: 8px 0 0;
        padding: 0 0 0 12px;
        border-left: 2px solid #D5DCE5;
    }
    .caixa-paradas .itens-parada li {
        display: flex;
        flex-direction: column;
        gap: 2px;
        padding: 0;
        border-bottom: none;
    }
    .caixa-paradas .itens-parada b {
        font-size: 14px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Monta a barra da cota grátis (só números calculados pelo próprio código entram aqui)

def barra_cota(porcentagem, rotas_restantes):
    porcentagem = int(porcentagem)
    rotas_restantes = int(rotas_restantes)
    return f"""
    <div class="cota">
        <div class="cota-topo"><span>Cota grátis do mês</span><b>{porcentagem}%</b></div>
        <div class="cota-trilho">
            <div style="width: {porcentagem}%"></div>
            <img src="app/static/caminhao_cota.svg" alt="Caminhão na posição de {porcentagem}% da cota" style="left: {porcentagem}%">
        </div>
        <span class="cota-texto">Ainda cabem cerca de {rotas_restantes} rotas</span>
    </div>
    """
#______________________________________________________________________________________________________________________#
#Monta o aviso da busca, o cartão do cliente e a linha de cada parada extra (textos passam pelo escape)

def aviso_extras(titulo, texto):
    html = f'<div class="aviso-extras" role="alert"><strong>{escape(titulo)}</strong>'
    if texto != "":
        html += f"<span>{escape(texto)}</span>"
    html += "</div>"
    return html


def cliente_encontrado(nome, endereco):
    return f'''<div class="dados-cliente"><span class="rotulo-cliente">CLIENTE ENCONTRADO</span>
            <b>{escape(nome)}</b><span>{escape(endereco)}</span></div>'''


def linha_parada_extra(nome, motivo, detalhe):
    return f'''<div class="linha-extra"><span class="etiqueta-extra lista">Extra</span>
            <div class="textos-extra"><b>{escape(nome)} · {escape(motivo)}</b><span>{escape(detalhe)}</span></div></div>'''


def transportadora_escolhida(nome, endereco):
    return f'''<div class="dados-cliente"><span class="rotulo-cliente">TRANSPORTADORA ESCOLHIDA</span>
            <b>{escape(nome)}</b><span>{escape(endereco)}</span></div>'''


def ajuda_extras(texto):
    return f'<p class="ajuda-extras">{escape(texto)}</p>'
#______________________________________________________________________________________________________________________#
#Monta o resultado da rota (os textos vindos do GestãoClick passam pelo escape)

def resultado_rota(titulo, situacao, entregas, pedidas, minutos_deslocamento, minutos_disponiveis,
                   link_maps, hora_saida, paradas, nao_entraram, hora_retorno):
    entregas = int(entregas)
    pedidas = int(pedidas)
    minutos_deslocamento = int(minutos_deslocamento)
    minutos_disponiveis = int(minutos_disponiveis)

    deslocamento_texto = f"{minutos_deslocamento // 60}h{minutos_deslocamento % 60:02d}"
    disponivel_texto = f"{minutos_disponiveis // 60}h{minutos_disponiveis % 60:02d}"

    botao_maps = ""
    if link_maps != "":
        botao_maps = f'<a class="botao-maps" href="{escape(link_maps)}" target="_blank" rel="noopener noreferrer">Abrir no Google Maps</a>'

    lista_paradas = f'<li class="saida"><span class="rotulo-saida">Saída</span><span class="hora-saida">{escape(hora_saida)}</span></li>'
    numero = 1
    for parada in paradas:
        if parada["tipo"] == "transportadora":
            itens_html = ""
            for item in parada["itens"]:
                itens_html += f"<li><b>{escape(item['titulo'])}</b>"
                if item["detalhe"] != "":
                    itens_html += f"<span>{escape(item['detalhe'])}</span>"
                itens_html += "</li>"
            lista_paradas += f"""<li><span class="numero-parada">{numero}</span>
                <div class="dados-parada"><b class="titulo-extra">{escape(parada["titulo"])}<span class="etiqueta-transportadora">Transportadora</span></b>
                <span>{escape(parada["endereco"])}</span><ul class="itens-parada">{itens_html}</ul></div></li>"""
        elif parada["tipo"] == "extra":
            lista_paradas += f"""<li><span class="numero-parada">{numero}</span>
                <div class="dados-parada"><b class="titulo-extra">{escape(parada["titulo"])}<span class="etiqueta-extra">Extra</span></b>
                <span class="motivo-parada">{escape(parada["detalhe"])}</span><span>{escape(parada["endereco"])}</span></div></li>"""
        else:
            linhas = ""
            if parada["detalhe"] != "":
                linhas += f'<span class="volumes-parada">{escape(parada["detalhe"])}</span>'
            if parada["cliente"] != "":
                linhas += f'<span>{escape(parada["cliente"])}</span>'
            lista_paradas += f"""<li><span class="numero-parada">{numero}</span>
                <div class="dados-parada"><b>{escape(parada["titulo"])}</b>{linhas}<span>{escape(parada["endereco"])}</span></div></li>"""
        numero += 1

    bloco_ficaram = ""
    if len(nao_entraram) > 0:
        bloco_ficaram = '<div class="ficaram"><strong>Ficaram para a próxima:</strong>'
        for codigo, motivo in nao_entraram:
            bloco_ficaram += f"<span><b>{escape(codigo)}</b> {escape(motivo)}</span>"
        bloco_ficaram += "</div>"

    return f"""
    <div class="resultado-rota">
        <div class="resultado-topo"><h2>{escape(titulo)}</h2>{situacao}</div>
        <div class="numeros-rota">
            <div class="numero"><span><span class="so-leitor">{entregas}</span><span class="conta" style="--alvo:{entregas}" aria-hidden="true"></span></span><span>entregas de {pedidas}</span></div>
            <div class="numero"><span><span class="so-leitor">{deslocamento_texto}</span><span class="conta hora" style="--alvo:{minutos_deslocamento}" aria-hidden="true"></span></span><span>de deslocamento</span></div>
            <div class="numero"><span><span class="so-leitor">{disponivel_texto}</span><span class="conta hora" style="--alvo:{minutos_disponiveis}" aria-hidden="true"></span></span><span>disponíveis</span></div>
            {botao_maps}
        </div>
        <div class="paradas-e-avisos">
            <div class="caixa-paradas"><ol>{lista_paradas}</ol></div>
            {bloco_ficaram}
        </div>
        <div class="retorno-previsto"><span>Retorno previsto:</span><span>{escape(hora_retorno)}</span></div>
    </div>
    """
#______________________________________________________________________________________________________________________#
#Visual da tela Confirmar entregas

def estilo_confirmar_entregas():
    css = """
    <style>
    .subtitulo-pagina {
        margin: 0;
        padding-bottom: 8px;
        font-size: clamp(17px, 0.95rem + 0.35vw, 21px);
        line-height: 1.4;
        color: #5B6B82;
    }
    .subtitulo-pagina b {
        color: #0B5CA8;
    }
    div.st-key-caixa_confirmar {
        padding: 8px 24px 12px;
    }
    div.st-key-topo_confirmar {
        flex-wrap: nowrap;
        justify-content: space-between;
        padding: 6px 40px 6px 0;
        border-bottom: 1px solid #E3E8EF;
    }
    div.st-key-topo_confirmar > div {
        width: auto;
    }
    .instrucao {
        font-size: 14px;
        color: #5B6B82;
    }
    .st-key-marcar_todos button p {
        font-size: 14px;
        font-weight: 600;
        color: #0B5CA8;
    }
    [class*="st-key-item_"] {
        flex-wrap: nowrap;
        gap: 16px;
        padding: 12px 0;
        border-bottom: 1px solid #E3E8EF;
    }
    [class*="st-key-item_"] > div:first-child {
        flex: 0 0 auto;
        width: auto;
    }
    [class*="st-key-item_"] > div:last-child {
        flex: 1 1 0;
    }
    .item-entrega {
        display: grid;
        grid-template-columns: 40px 1fr;
        align-items: center;
        line-height: normal;
        color: #0F2A4A;
    }
    .numero-entrega {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 600;
        color: #0B5CA8;
    }
    .item-entrega b {
        display: block;
        font-size: 15px;
        font-weight: 600;
    }
    .item-entrega span:not(.numero-entrega) {
        font-size: 14px;
        color: #5B6B82;
    }
    div.st-key-rodape_confirmar {
        flex-wrap: nowrap;
        justify-content: space-between;
        gap: 24px;
        padding-top: 8px;
    }
    div.st-key-rodape_confirmar > div:first-child {
        flex: 0 1 560px;
    }
    .explicacao-confirmar {
        margin: 0;
        font-size: 14px;
        line-height: 1.5;
        color: #5B6B82;
    }
    .st-key-enviar_confirmacao button {
        min-height: 48px;
        padding: 0 28px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    .st-key-enviar_confirmacao button:hover {
        background: #163A66;
        color: #FFFFFF;
    }
    .st-key-enviar_confirmacao button p {
        font-size: 15px;
        font-weight: 600;
    }
    /* Parada extra na lista de confirmação */
    .item-entrega b.titulo-extra {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .item-entrega span.etiqueta-extra {
        font-size: 11px;
        color: #0B5CA8;
    }
    .item-entrega span.motivo-parada {
        display: block;
        color: #0F2A4A;
    }
    /* Parada de transportadora: cabeçalho sem caixinha e uma caixinha por item */
    [class*="st-key-cabeca_grupo_"] {
        padding: 12px 0 4px 36px;
    }
    .item-entrega span.etiqueta-transportadora {
        font-size: 11px;
        color: #42536B;
    }
    .item-entrega span.linha-item {
        display: block;
    }
    .item-entrega span.volumes-item {
        display: block;
        color: #0F2A4A;
    }
    [class*="st-key-itens_grupo_"] [class*="st-key-item_"] {
        padding: 8px 0;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Visual da página Histórico: abas, tabelas e números desde o início

def estilo_historico():
    css = """
    <style>
    /* Contador animado: o número sobe de 0 até o valor final (--alvo) */
    @property --n {
        syntax: '<integer>';
        inherits: false;
        initial-value: 0;
    }
    @counter-style tres-digitos {
        system: extends decimal;
        pad: 3 "0";
    }
    @keyframes conta {
        from { --n: 0; }
        to { --n: var(--alvo); }
    }
    .conta {
        animation: conta 1.4s cubic-bezier(.2, .7, .2, 1) forwards;
        counter-reset: v var(--n);
    }
    .conta::after {
        content: counter(v);
    }
    .conta.mil {
        counter-reset: a round(down, var(--n) / 1000, 1) b mod(var(--n), 1000);
    }
    .conta.mil::after {
        content: counter(a) "." counter(b, tres-digitos);
    }
    .so-leitor {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0 0 0 0);
        white-space: nowrap;
    }
    @media (prefers-reduced-motion: reduce) {
        .conta { animation: none; --n: var(--alvo); }
    }
    /* Abas */
    div.st-key-abas_historico {
        gap: 28px;
        margin-bottom: 8px;
        border-bottom: 1px solid #E3E8EF;
    }
    div.st-key-abas_historico > div {
        width: auto;
    }
    .st-key-abas_historico button {
        min-height: 44px;
        padding: 0;
        border: none;
        border-radius: 0;
        background: transparent;
    }
    .st-key-abas_historico button:hover {
        background: transparent;
    }
    .st-key-abas_historico button p {
        font-size: 15px;
        font-weight: 500;
        color: #5B6B82;
    }
    .st-key-abas_historico [data-testid="stBaseButton-primary"] {
        box-shadow: inset 0 -2px 0 #3B82F6;
    }
    .st-key-abas_historico [data-testid="stBaseButton-primary"] p {
        font-weight: 600;
        color: #0F2A4A;
    }
    /* Colunas das tabelas */
    .linha-tabela.historico {
        grid-template-columns: 316fr 216fr 235fr 276fr;
    }
    .linha-tabela.historico > div:nth-child(3), .linha-tabela.historico > div:nth-child(4) {
        text-align: right;
    }
    .linha-tabela.atividades {
        grid-template-columns: 316fr 216fr 511fr;
    }
    .linha-tabela.entregas {
        grid-template-columns: 170fr 230fr 140fr 110fr 393fr;
    }
    .celula-dupla {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
    }
    .celula-dupla .titulo-destino {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
    }
    .celula-dupla .cinza {
        font-size: 13px;
    }
    .tabela-vazia {
        margin: 0;
        padding: 16px;
        font-size: 14px;
        color: #8A97A8;
    }
    .nota-historico {
        margin: 0;
        font-size: 13px;
        color: #8A97A8;
    }
    /* Números desde o início */
    .desde-inicio {
        padding-top: 24px;
        color: #0F2A4A;
        line-height: normal;
    }
    .desde-inicio h2 {
        margin: 0 0 20px;
        padding: 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 30px;
        font-weight: 600;
        color: #0F2A4A;
    }
    .grade-numeros {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
    }
    .grade-numeros > div {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .grade-numeros > div:nth-child(1) {
        align-items: flex-start;
    }
    .grade-numeros > div:nth-child(2) {
        align-items: center;
    }
    .grade-numeros > div:nth-child(3) {
        align-items: flex-end;
    }
    .numero-grande {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: clamp(36px, 1.8rem + 1.8vw, 54px);
        font-weight: 600;
        line-height: 1;
        letter-spacing: -1.5px;
    }
    .grade-numeros > div > span:last-child {
        font-size: clamp(15px, 0.85rem + 0.3vw, 18px);
        color: #5B6B82;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Monta os números de "Desde o início" (só números calculados pelo próprio código entram aqui)

def numeros_desde_o_inicio(numeros):
    blocos = ""
    for valor, legenda in numeros:
        valor = int(valor)
        texto = f"{valor:,}".replace(",", ".")
        classe = "conta"
        if valor >= 1000:
            classe = "conta mil"
        blocos += f"""<div><span class="numero-grande"><span class="so-leitor">{texto}</span><span class="{classe}" style="--alvo:{valor}" aria-hidden="true"></span></span>
            <span>{legenda}</span></div>"""
    return f'<div class="desde-inicio"><h2>Desde o início</h2><div class="grade-numeros">{blocos}</div></div>'
#______________________________________________________________________________________________________________________#
#Visual da página Minha conta: os dois blocos, o formulário de senha e os avisos

def estilo_minha_conta():
    css = """
    <style>
    div.st-key-blocos_conta {
        flex-wrap: wrap;
        align-items: stretch;
        gap: 32px;
    }
    div.st-key-blocos_conta > div {
        flex: 1 1 380px;
    }
    .st-key-perfil_conta, .st-key-senha_conta {
        padding: 24px;
        border-radius: 12px;
        background: #EDF1F7;
        box-shadow: 0 4px 16px rgba(15, 42, 74, 0.08);
    }
    .st-key-perfil_conta [data-testid="stElementContainer"], .st-key-perfil_conta [data-testid="stHtml"] {
        height: 100%;
    }
    .titulo-bloco {
        margin: 0;
        padding: 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 600;
        line-height: normal;
        color: #0F2A4A;
    }
    /* Meu perfil */
    .perfil-conta {
        display: flex;
        flex-direction: column;
        gap: 18px;
        height: 100%;
        line-height: normal;
        color: #0F2A4A;
    }
    .identidade {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 8px 0;
    }
    .inicial {
        width: 52px;
        height: 52px;
        flex-shrink: 0;
        border-radius: 50%;
        background: #3B82F6;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 700;
    }
    .identidade > span:last-child {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 600;
    }
    .dados-perfil {
        margin: auto 0 0;
        display: flex;
        flex-direction: column;
        border-top: 1px solid #E3E8EF;
        min-height: 194px;
    }
    .dados-perfil > div {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 16px;
        padding: 14px 0;
        border-bottom: 1px solid #E3E8EF;
    }
    .dados-perfil > div:last-child {
        border-bottom: none;
    }
    .dados-perfil dt {
        font-size: 14px;
        color: #5B6B82;
    }
    .dados-perfil dd {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
        color: #0F2A4A;
        text-align: right;
    }
    /* Minha senha */
    .st-key-senha_conta [data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    .st-key-senha_conta [data-testid="stForm"] [data-testid="stVerticalBlock"] {
        gap: 18px;
    }
    .st-key-senha_conta [data-testid="stWidgetLabel"] {
        min-height: 0;
        margin-bottom: 6px;
    }
    .st-key-senha_conta label p {
        font-size: 13px;
        font-weight: 600;
        color: #5B6B82;
    }
    .st-key-senha_conta [data-testid="stTextInputRootElement"] {
        min-height: 44px;
        border: 1px solid #E3E8EF;
        border-radius: 8px;
        background: #FFFFFF;
    }
    .st-key-senha_conta [data-testid="stTextInputRootElement"]:focus-within {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
    }
    .st-key-senha_conta input {
        padding: 0 12px;
        font-size: 15px;
        color: #0F2A4A;
    }
    .st-key-senha_conta [data-testid="stTextInputRootElement"] button, .st-key-senha_conta [data-testid="InputInstructions"] {
        display: none;
    }
    .st-key-senha_conta [data-testid="stFormSubmitButton"] button {
        min-height: 44px;
        margin-top: 6px;
        padding: 0 32px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    .st-key-senha_conta [data-testid="stFormSubmitButton"] button:hover {
        background: #163A66;
        color: #FFFFFF;
    }
    .st-key-senha_conta [data-testid="stFormSubmitButton"] button p {
        font-size: 15px;
        font-weight: 600;
    }
    /* Avisos */
    .aviso-conta {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 14px;
        line-height: 1.5;
        color: #5B6B82;
    }
    .aviso-conta strong {
        font-size: 15px;
        font-weight: 600;
        color: #0B5CA8;
    }
    .aviso-conta.erro strong {
        color: #C0392B;
    }
    .bloco-admin {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    .bloco-admin .aviso-conta {
        gap: 8px;
    }
    /* Troca obrigatória: meia largura e botão Continuar */
    div.st-key-troca_conta {
        width: max(calc(50% - 16px), min(380px, 100%));
    }
    .st-key-continuar_troca button {
        min-height: 44px;
        padding: 0 32px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    .st-key-continuar_troca button:hover, .st-key-continuar_troca button:focus {
        background: #163A66;
        color: #FFFFFF;
    }
    .st-key-continuar_troca button p {
        font-size: 15px;
        font-weight: 600;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Monta o bloco Meu perfil (o nome passa pelo escape)

def perfil_conta(nome, rotas):
    rotas = int(rotas)
    inicial = escape(nome[:1].upper())
    nome = escape(nome)
    return f"""
    <div class="perfil-conta">
        <h2 class="titulo-bloco">Meu perfil</h2>
        <div class="identidade"><span class="inicial" aria-hidden="true">{inicial}</span><span>{nome}</span></div>
        <dl class="dados-perfil">
            <div><dt>Nome</dt><dd>{nome}</dd></div>
            <div><dt>Rotas geradas</dt><dd>{rotas}</dd></div>
        </dl>
    </div>
    """
#______________________________________________________________________________________________________________________#
#Monta um aviso da página Minha conta (vermelho quando é erro, azul quando não é)

def aviso_conta(titulo, texto, erro):
    classes = "aviso-conta"
    papel = "status"
    if erro:
        classes += " erro"
        papel = "alert"
    return f'<div class="{classes}" role="{papel}"><strong>{escape(titulo)}</strong><span>{escape(texto)}</span></div>'
#______________________________________________________________________________________________________________________#
#Visual da página Usuários: caixa da lista, painel de novo usuário, tabela, confirmações e avisos

def estilo_usuarios():
    css = """
    <style>
    /* Caixa com o canto dobrado */
    div.st-key-lista_contas {
        position: relative;
        gap: 0;
        padding: 24px;
        border-radius: 12px 0 12px 12px;
        background: linear-gradient(225deg, transparent 24px, #EFF2FD 100%);
        filter: drop-shadow(0 4px 10px rgba(15, 42, 74, 0.08));
    }
    div.st-key-lista_contas::before {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 34px;
        height: 34px;
        background: linear-gradient(225deg, transparent 50%, #B8C6D8 50%, #D8E0EB 100%);
        border-bottom-left-radius: 8px;
    }
    /* Título Contas e botão Novo usuário */
    div.st-key-topo_contas {
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 12px 24px;
        margin: 0 40px 8px 0;
    }
    div.st-key-topo_contas > div {
        width: auto;
    }
    .titulo-contas {
        margin: 0;
        padding: 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 600;
        line-height: normal;
        color: #0F2A4A;
    }
    .st-key-abrir_novo button, .st-key-painel_novo [data-testid="stFormSubmitButton"] button,
    .st-key-confirmar_nova_senha button {
        min-height: 44px;
        padding: 0 24px;
        border: none;
        border-radius: 8px;
        background: #0F2A4A;
        color: #FFFFFF;
    }
    .st-key-abrir_novo button:hover, .st-key-abrir_novo button:focus,
    .st-key-painel_novo [data-testid="stFormSubmitButton"] button:hover,
    .st-key-painel_novo [data-testid="stFormSubmitButton"] button:focus,
    .st-key-confirmar_nova_senha button:hover, .st-key-confirmar_nova_senha button:focus {
        border: none;
        background: #163A66;
        color: #FFFFFF;
    }
    .st-key-abrir_novo button p, .st-key-painel_novo [data-testid="stFormSubmitButton"] button p,
    .st-key-confirmar_nova_senha button p, .st-key-confirmar_excluir button p, .st-key-cancelar_acao button p {
        font-size: 15px;
        font-weight: 600;
    }
    /* Painel Novo usuário */
    div.st-key-painel_novo {
        margin: 8px 0 16px;
        padding: 20px;
        border: 1px solid #E3E8EF;
        border-radius: 10px;
        background: #FFFFFF;
    }
    .st-key-painel_novo [data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    .st-key-painel_novo [data-testid="stForm"] [data-testid="stVerticalBlock"] {
        gap: 16px;
    }
    div.st-key-campos_novo {
        flex-wrap: wrap;
        align-items: flex-end;
        gap: 16px 24px;
    }
    div.st-key-campos_novo > div:first-child {
        flex: 1 1 260px;
    }
    div.st-key-campos_novo > div:last-child {
        width: auto;
    }
    .st-key-painel_novo [data-testid="stFormSubmitButton"] button {
        padding: 0 32px;
    }
    .st-key-painel_novo [data-testid="stWidgetLabel"] {
        min-height: 0;
        margin-bottom: 6px;
    }
    .st-key-painel_novo label p {
        font-size: 13px;
        font-weight: 600;
        color: #5B6B82;
    }
    .st-key-painel_novo [data-testid="stTextInputRootElement"] {
        min-height: 44px;
        border: 1px solid #E3E8EF;
        border-radius: 8px;
        background: #FFFFFF;
    }
    .st-key-painel_novo [data-testid="stTextInputRootElement"]:focus-within {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
    }
    .st-key-painel_novo input {
        padding: 0 12px;
        font-size: 15px;
        color: #0F2A4A;
    }
    .st-key-painel_novo [data-testid="InputInstructions"] {
        display: none;
    }
    /* Tabela de contas: cada linha tem as células em HTML e os botões de ação */
    div.st-key-tabela_contas {
        gap: 0;
        overflow-x: auto;
    }
    .cabecalho-contas {
        display: grid;
        grid-template-columns: 1fr 1fr 210px;
        min-width: 480px;
        border-bottom: 1px solid #E3E8EF;
        line-height: normal;
    }
    .cabecalho-contas > div {
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 700;
        color: #0B5CA8;
    }
    .cabecalho-contas > div:last-child {
        text-align: right;
    }
    [class*="st-key-conta_"] {
        flex-wrap: nowrap;
        align-items: center;
        gap: 0;
        min-width: 480px;
        border-bottom: 1px solid #E3E8EF;
    }
    [class*="st-key-conta_"] > div:first-child {
        flex: 1 1 0;
        min-width: 0;
    }
    .celulas-conta {
        display: grid;
        grid-template-columns: 1fr 1fr;
        font-size: 15px;
        line-height: normal;
        color: #0F2A4A;
    }
    .celulas-conta > div {
        padding: 12px 16px;
    }
    .celulas-conta > div:first-child {
        font-weight: 600;
    }
    .celulas-conta > div:last-child {
        color: #5B6B82;
    }
    [class*="st-key-acoes_"] {
        flex: 0 0 210px;
        width: 210px;
        justify-content: flex-end;
        gap: 0;
        padding: 8px 16px;
        box-sizing: border-box;
    }
    [class*="st-key-acoes_"] > div {
        width: auto;
    }
    [class*="st-key-nova_senha_"] button, [class*="st-key-excluir_"] button {
        min-height: 36px;
        padding: 0 12px;
        border: none;
        background: transparent;
    }
    [class*="st-key-nova_senha_"] button:hover, [class*="st-key-nova_senha_"] button:focus,
    [class*="st-key-excluir_"] button:hover, [class*="st-key-excluir_"] button:focus {
        border: none;
        background: transparent;
    }
    [class*="st-key-nova_senha_"] button p, [class*="st-key-excluir_"] button p {
        font-size: 14px;
        font-weight: 600;
        color: #0B5CA8;
    }
    [class*="st-key-excluir_"] button p {
        color: #C0392B;
    }
    /* Confirmação de Excluir e de Nova senha */
    div.st-key-confirmacao_contas {
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 12px 24px;
        padding-top: 20px;
    }
    div.st-key-confirmacao_contas > div {
        width: auto;
    }
    div.st-key-botoes_confirmacao {
        gap: 12px;
    }
    div.st-key-botoes_confirmacao > div {
        width: auto;
    }
    .st-key-cancelar_acao button {
        min-height: 44px;
        padding: 0 20px;
        border: 1px solid #B8C6D8;
        border-radius: 8px;
        background: transparent;
        color: #0F2A4A;
    }
    .st-key-cancelar_acao button:hover, .st-key-cancelar_acao button:focus {
        border: 1px solid #B8C6D8;
        background: transparent;
        color: #0F2A4A;
    }
    .st-key-confirmar_excluir button {
        min-height: 44px;
        padding: 0 20px;
        border: none;
        border-radius: 8px;
        background: #C0392B;
        color: #FFFFFF;
    }
    .st-key-confirmar_excluir button:hover, .st-key-confirmar_excluir button:focus {
        border: none;
        background: #C0392B;
        color: #FFFFFF;
    }
    .st-key-confirmar_nova_senha button {
        padding: 0 20px;
    }
    /* Avisos */
    .aviso-usuarios {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 14px;
        line-height: 1.5;
        color: #5B6B82;
    }
    .aviso-usuarios.separado {
        padding-top: 20px;
    }
    .aviso-usuarios strong {
        font-size: 15px;
        font-weight: 600;
        color: #0B5CA8;
    }
    .aviso-usuarios.erro strong {
        color: #C0392B;
    }
    .senha-temporaria {
        font-family: ui-monospace, Consolas, monospace;
        font-size: 15px;
        color: #0F2A4A;
        letter-spacing: 0.5px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Monta o cabeçalho e as células de uma linha da tabela de contas (o nome passa pelo escape)

def cabecalho_contas():
    return '<div class="cabecalho-contas"><div>Usuário</div><div>Situação</div><div>Ações</div></div>'


def celulas_conta(nome, situacao):
    return f'<div class="celulas-conta"><div>{escape(nome)}</div><div>{escape(situacao)}</div></div>'


def destacar_conta(posicao):
    posicao = int(posicao)
    st.markdown(f"<style>div.st-key-conta_{posicao} {{ background: #DBEAFE; }}</style>", unsafe_allow_html=True)
#______________________________________________________________________________________________________________________#
#Monta os avisos e as perguntas da página Usuários (todos os textos passam pelo escape)

def aviso_usuarios(titulo, textos, erro, separado=False):
    classes = "aviso-usuarios"
    papel = "status"
    if erro:
        classes += " erro"
        papel = "alert"
    if separado:
        classes += " separado"

    html = f'<div class="{classes}" role="{papel}"><strong>{escape(titulo)}</strong>'
    for texto in textos:
        html += f"<span>{escape(texto)}</span>"
    html += "</div>"
    return html


def aviso_senha_temporaria(titulo, senha, observacao, separado=False):
    classes = "aviso-usuarios"
    if separado:
        classes += " separado"

    html = f'<div class="{classes}" role="status"><strong>{escape(titulo)}</strong>'
    html += f'<span>Senha temporária: <b class="senha-temporaria">{escape(senha)}</b></span>'
    if observacao != "":
        html += f"<span>{escape(observacao)}</span>"
    html += "</div>"
    return html
#______________________________________________________________________________________________________________________#