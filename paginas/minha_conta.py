import streamlit as st
import autenticacao
import banco
import visual

if st.session_state.get("logado") != True:
    st.stop()

visual.estilo_pagina_interna()
visual.estilo_minha_conta()

usuario = st.session_state["usuario"]
#______________________________________________________________________________________________________________________#
#Título e os dois blocos: Meu perfil e Minha senha

visual.titulo_pagina("Minha conta")

with st.container(key="blocos_conta", horizontal=True):
    with st.container(key="perfil_conta"):
        st.html(visual.perfil_conta(usuario, banco.total_rotas_do_usuario(usuario)))

    with st.container(key="senha_conta"):
        if st.session_state.get("admin") == True:
            st.html('<div class="bloco-admin"><h2 class="titulo-bloco">Minha senha</h2>'
                    + visual.aviso_conta("A senha do administrador é trocada fora do painel",
                                         "Por segurança, a senha desta conta fica guardada no servidor, separada das outras. "
                                         "Para trocá-la, siga o passo a passo do manual do sistema.", erro=False)
                    + "</div>")
        else:
            autenticacao.mostrar_formulario_senha(usuario)
