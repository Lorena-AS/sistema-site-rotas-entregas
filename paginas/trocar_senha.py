import streamlit as st
import autenticacao
import visual

if st.session_state.get("logado") != True:
    st.stop()

visual.estilo_pagina_interna()
visual.estilo_minha_conta()

usuario = st.session_state["usuario"]
#______________________________________________________________________________________________________________________#
#Título e o formulário Minha senha (o site só é liberado depois da troca)

visual.titulo_pagina("Troque sua senha")

with st.container(key="troca_conta"):
    with st.container(key="senha_conta"):
        trocou = autenticacao.mostrar_formulario_senha(usuario)
        if trocou:
            st.button("Continuar", key="continuar_troca")
