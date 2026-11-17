import streamlit as st
import visual

visual.fundo_escuro()
visual.fundo_painel()

with st.container(key="painel"):
    visual.titulo_painel()

    if visual.card("card_lista.html", "lista"):
        st.switch_page("paginas/pedidos.py")

    if visual.card("card_rota.html", "rota"):
        st.switch_page("paginas/gerar_rota.py")

    coluna_esquerda, coluna_direita = st.columns(2)
    with coluna_esquerda:
        if visual.card("card_historico.html", "historico"):
            st.switch_page("paginas/historico.py")
    with coluna_direita:
        visual.card_link("card_maps.html", "maps", "https://www.google.com/maps")