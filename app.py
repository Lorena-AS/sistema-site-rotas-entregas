import streamlit as st
from datetime import datetime, date
import visual
import autenticacao
import banco
import marca

dados_marca = marca.ler_marca()
st.set_page_config(page_title=f"Expedição {dados_marca['nome_curto']}", page_icon=":material/local_shipping:", layout="wide")
visual.aplicar_estilo()

if "banco_preparado" not in st.session_state:
    banco.criar_tabelas()
    banco.limpar_dados_antigos()
    st.session_state["banco_preparado"] = True

autenticacao.iniciar_sessao()
autenticacao.verificar_inatividade()
#______________________________________________________________________________________________________________________#
#Antes do login: só a tela de entrada

if st.session_state["logado"] == False:
    visual.fundo_escuro()
    coluna_botao = visual.cabecalho()
    with coluna_botao:
        if st.button("Entrar", type="primary", icon=":material/login:"):
            autenticacao.janela_login()
    visual.tela_entrada()
#______________________________________________________________________________________________________________________#
#Depois do login: menu no topo com as páginas do sistema

else:
    visual.estilo_menu()
    endereco_logo = marca.logo_em_data_uri(dados_marca)
    if endereco_logo is not None:
        st.logo(endereco_logo, size="large")

    e_admin = st.session_state.get("admin") == True
    usuario = st.session_state["usuario"]

    if e_admin == False and banco.usuario_existe(usuario) == False:
        autenticacao.sair()

    troca_obrigatoria = e_admin == False and banco.precisa_trocar_senha(usuario)

    inicio = st.Page("paginas/inicio.py", title="Início", default=True)
    pedidos = st.Page("paginas/pedidos.py", title="Pedidos")
    gerar_rota = st.Page("paginas/gerar_rota.py", title="Gerar rota")
    historico = st.Page("paginas/historico.py", title="Histórico")
    confirmar = st.Page("paginas/confirmar_entregas.py", title="Confirmar entregas", visibility="hidden")
    minha_conta = st.Page("paginas/minha_conta.py", title="Minha conta", visibility="hidden")
    trocar_senha = st.Page("paginas/trocar_senha.py", title="Troque sua senha", visibility="hidden")
    usuarios = st.Page("paginas/usuarios.py", title="Usuários", visibility="hidden")

    pendente = banco.data_rota_pendente()
    rota_atrasada = False
    if pendente is not None:
        rota_atrasada = datetime.strptime(pendente, "%Y-%m-%d %H:%M").date() < date.today()

    if troca_obrigatoria:
        pagina_atual = st.navigation([trocar_senha], position="hidden")
    elif rota_atrasada:
        pagina_atual = st.navigation([confirmar], position="hidden")
    else:
        paginas = [inicio, pedidos, gerar_rota, historico, confirmar, minha_conta]
        if e_admin:
            paginas.append(usuarios)
        pagina_atual = st.navigation(paginas, position="top")

    site_liberado = troca_obrigatoria == False and rota_atrasada == False

    with st.container(key="usuario"):
        with st.popover(st.session_state["usuario"], icon=":material/account_circle:"):
            if site_liberado:
                if st.button("Minha conta", key="ir_minha_conta", icon=":material/person:", width="stretch"):
                    st.switch_page(minha_conta)
                if e_admin:
                    if st.button("Usuários", key="ir_usuarios", icon=":material/group:", width="stretch"):
                        st.switch_page(usuarios)
            if st.button("Sair", icon=":material/logout:", width="stretch"):
                autenticacao.sair()

    if pendente is not None and site_liberado and pagina_atual.title != "Confirmar entregas":
        with st.container(key="aviso_pendente", horizontal=True, vertical_alignment="center"):
            st.html('<span class="texto-aviso-pendente">A rota de hoje ainda não teve as entregas confirmadas.</span>')
            if st.button("Confirmar entregas", key="ir_confirmar", type="tertiary"):
                st.switch_page(confirmar)

    pagina_atual.run()

visual.rodape()