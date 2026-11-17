import streamlit as st
import autenticacao
import banco
import visual
from regras_senha import gerar_senha_temporaria

if st.session_state.get("logado") != True:
    st.stop()

if st.session_state.get("admin") != True:
    st.stop()

visual.estilo_pagina_interna()
visual.estilo_usuarios()

CARACTERES_NOME = "abcdefghijklmnopqrstuvwxyz0123456789._"

admin = st.session_state["usuario"]

if "painel_novo_aberto" not in st.session_state:
    st.session_state["painel_novo_aberto"] = False
if "acao_tipo" not in st.session_state:
    st.session_state["acao_tipo"] = ""
    st.session_state["acao_usuario"] = ""
#______________________________________________________________________________________________________________________#
#Abre e fecha o painel, escolhe e cancela a ação de uma linha

def alternar_painel():
    st.session_state["painel_novo_aberto"] = not st.session_state["painel_novo_aberto"]


def escolher_acao(tipo, nome):
    st.session_state["acao_tipo"] = tipo
    st.session_state["acao_usuario"] = nome


def cancelar_acao():
    st.session_state["acao_tipo"] = ""
    st.session_state["acao_usuario"] = ""
#______________________________________________________________________________________________________________________#
#Confere o nome e cria o usuário com uma senha temporária (devolve o aviso que deve aparecer)

def nome_valido(nome):
    if len(nome) < 3 or len(nome) > 30:
        return False
    for caractere in nome:
        if caractere not in CARACTERES_NOME:
            return False
    return True


def criar_conta(nome):
    nome = nome.strip().lower()

    if nome_valido(nome) == False:
        return visual.aviso_usuarios("Não foi possível criar!",
                                     ["Use de 3 a 30 caracteres: letras sem acento, números, ponto ou sublinhado."], erro=True)

    if autenticacao.e_nome_do_admin(nome) or banco.usuario_existe(nome):
        return visual.aviso_usuarios("Não foi possível criar!", ["Já existe um usuário com esse nome."], erro=True)

    senha_temporaria = gerar_senha_temporaria()
    if banco.criar_usuario_temporario(nome, senha_temporaria) == False:
        return visual.aviso_usuarios("Não foi possível criar!", ["Já existe um usuário com esse nome."], erro=True)

    banco.registrar_atividade(admin, f"Criou usuário {nome}")
    return visual.aviso_senha_temporaria(f'Usuário "{nome}" criado!', senha_temporaria,
                                         "Troca de senha obrigatória no próximo login.")
#______________________________________________________________________________________________________________________#
#Faz a ação confirmada (Excluir ou Salvar nova senha) antes de montar a tabela, para a lista já aparecer atualizada

aviso_acao = ""
acao_tipo = st.session_state["acao_tipo"]
acao_usuario = st.session_state["acao_usuario"]

if acao_tipo == "excluir" and st.session_state.get("confirmar_excluir") == True:
    if banco.excluir_usuario(acao_usuario):
        banco.registrar_atividade(admin, f"Excluiu usuário {acao_usuario}")
        aviso_acao = visual.aviso_usuarios(f'Conta "{acao_usuario}" excluída.', [], erro=False, separado=True)
    else:
        aviso_acao = visual.aviso_usuarios("Não foi possível concluir!", ["Esse usuário não existe mais."],
                                           erro=True, separado=True)
    cancelar_acao()

elif acao_tipo == "senha" and st.session_state.get("confirmar_nova_senha") == True:
    senha_temporaria = gerar_senha_temporaria()
    if banco.gerar_nova_senha_temporaria(acao_usuario, senha_temporaria):
        banco.registrar_atividade(admin, f"Gerou nova senha para {acao_usuario}")
        aviso_acao = visual.aviso_senha_temporaria(f'Nova senha temporária para "{acao_usuario}"', senha_temporaria, "",
                                                   separado=True)
    else:
        aviso_acao = visual.aviso_usuarios("Não foi possível concluir!", ["Esse usuário não existe mais."],
                                           erro=True, separado=True)
    cancelar_acao()
#______________________________________________________________________________________________________________________#
#Título, botão Novo usuário e painel de criação

visual.titulo_pagina("Usuários")

with st.container(key="lista_contas"):
    with st.container(key="topo_contas", horizontal=True, vertical_alignment="center"):
        st.html('<h2 class="titulo-contas">Contas</h2>')
        if st.session_state["painel_novo_aberto"]:
            texto_botao = "Fechar"
        else:
            texto_botao = "\\+ Novo usuário"
        st.button(texto_botao, key="abrir_novo", on_click=alternar_painel)

    if st.session_state["painel_novo_aberto"]:
        with st.container(key="painel_novo"):
            with st.form("formulario_novo_usuario", clear_on_submit=True, border=False):
                with st.container(key="campos_novo", horizontal=True, vertical_alignment="bottom"):
                    nome_novo = st.text_input("Nome do novo usuário", placeholder="nome.sobrenome", autocomplete="off")
                    criar = st.form_submit_button("Criar usuário")
                espaco_aviso_novo = st.empty()

            if criar:
                espaco_aviso_novo.html(criar_conta(nome_novo))
#______________________________________________________________________________________________________________________#
#Tabela de contas (a linha escolhida fica destacada)

    contas = banco.listar_usuarios()
    aguardando = banco.listar_aguardando_troca()

    nomes = []
    for nome, criado_em in contas:
        nomes.append(nome)

    acao_tipo = st.session_state["acao_tipo"]
    acao_usuario = st.session_state["acao_usuario"]
    if acao_tipo != "" and acao_usuario not in nomes:
        cancelar_acao()
        acao_tipo = ""

    if acao_tipo != "":
        visual.destacar_conta(nomes.index(acao_usuario))

    with st.container(key="tabela_contas"):
        st.html(visual.cabecalho_contas())
        posicao = 0
        for nome in nomes:
            situacao = "Ativa"
            if nome in aguardando:
                situacao = "Aguardando troca de senha"

            with st.container(key=f"conta_{posicao}", horizontal=True, vertical_alignment="center"):
                st.html(visual.celulas_conta(nome, situacao))
                with st.container(key=f"acoes_{posicao}", horizontal=True):
                    st.button("Nova senha", key=f"nova_senha_{posicao}", on_click=escolher_acao, args=("senha", nome))
                    st.button("Excluir", key=f"excluir_{posicao}", on_click=escolher_acao, args=("excluir", nome))
            posicao += 1

    if len(nomes) == 0:
        st.html(visual.aviso_usuarios("Nenhum usuário cadastrado.", [], erro=False, separado=True))
#______________________________________________________________________________________________________________________#
#Confirmação da ação escolhida e aviso do resultado

    if acao_tipo == "excluir":
        with st.container(key="confirmacao_contas", horizontal=True):
            st.html(visual.aviso_usuarios(f'Excluir a conta "{acao_usuario}"?',
                                          ["O usuário perderá o acesso. Isso não pode ser desfeito."], erro=True))
            with st.container(key="botoes_confirmacao", horizontal=True):
                st.button("Cancelar", key="cancelar_acao", on_click=cancelar_acao)
                st.button("Excluir", key="confirmar_excluir")

    elif acao_tipo == "senha":
        with st.container(key="confirmacao_contas", horizontal=True):
            st.html(visual.aviso_usuarios(f'Gerar uma nova senha temporária para "{acao_usuario}"?', [], erro=False))
            with st.container(key="botoes_confirmacao", horizontal=True):
                st.button("Cancelar", key="cancelar_acao", on_click=cancelar_acao)
                st.button("Salvar nova senha", key="confirmar_nova_senha")

    if aviso_acao != "":
        st.html(aviso_acao)
