import time
import bcrypt
import streamlit as st
import banco
import visual
from regras_senha import senha_segue_regras

MINUTOS_INATIVIDADE = 30
#______________________________________________________________________________________________________________________#
#Prepara as informações da sessão (quem está logado)

def iniciar_sessao():
    if "logado" not in st.session_state:
        st.session_state["logado"] = False
        st.session_state["usuario"] = ""
        st.session_state["admin"] = False
        st.session_state["ultima_atividade"] = time.time()
#______________________________________________________________________________________________________________________#
#Confere a senha do administrador, guardada no secrets.toml

def conferir_admin(usuario, senha):
    usuario_admin = st.secrets["admin"]["usuario"].strip().lower()
    if usuario != usuario_admin:
        return False

    senha_em_bytes = senha.encode("utf-8")
    if len(senha_em_bytes) > 72:
        return False

    hash_admin = st.secrets["admin"]["senha_hash"].encode("utf-8")
    return bcrypt.checkpw(senha_em_bytes, hash_admin)
#______________________________________________________________________________________________________________________#
#Confere o login e devolve "ok", "bloqueado" ou "invalido"

def verificar_login(usuario, senha):
    usuario = usuario.strip().lower()
    if usuario == "":
        return "invalido"

    if banco.esta_bloqueado(usuario):
        return "bloqueado"

    if conferir_admin(usuario, senha):
        e_admin = True
    elif banco.conferir_senha(usuario, senha):
        e_admin = False
    else:
        banco.registrar_erro(usuario)
        banco.registrar_atividade(usuario, "Senha errada")
        return "invalido"

    banco.limpar_erros(usuario)
    banco.registrar_atividade(usuario, "Entrou no sistema")
    st.session_state["logado"] = True
    st.session_state["usuario"] = usuario
    st.session_state["admin"] = e_admin
    st.session_state["ultima_atividade"] = time.time()
    return "ok"
#______________________________________________________________________________________________________________________#
#Mostra a janela de login

@st.dialog("Entrar no sistema")
def janela_login():
    with st.form("formulario_login"):
        usuario = st.text_input("Usuário", placeholder="seu.usuario")
        senha = st.text_input("Senha", type="password")
        enviar = st.form_submit_button("Entrar", type="primary", width="stretch")
        st.markdown('<div class="aviso-senha">Esqueceu a senha? Fale com o administrador.</div>', unsafe_allow_html=True)

    if enviar:
        if usuario == "" or senha == "":
            st.warning("Preencha o usuário e a senha.")
        else:
            resultado = verificar_login(usuario, senha)
            if resultado == "ok":
                st.rerun()
            elif resultado == "bloqueado":
                st.error("Muitas tentativas erradas. Aguarde 15 minutos e tente novamente.", icon=":material/lock:")
            else:
                st.error("Usuário ou senha incorretos.", icon=":material/error:")
#______________________________________________________________________________________________________________________#
#Sai do sistema e apaga as informações da sessão

def sair():
    banco.registrar_atividade(st.session_state["usuario"], "Saiu do sistema")
    st.session_state["logado"] = False
    st.session_state["usuario"] = ""
    st.session_state["admin"] = False
    st.rerun()
#______________________________________________________________________________________________________________________#
#Sai do sistema se a pessoa ficou muito tempo sem usar

def verificar_inatividade():
    agora = time.time()
    if st.session_state["logado"] == True:
        tempo_parado = agora - st.session_state["ultima_atividade"]
        if tempo_parado > MINUTOS_INATIVIDADE * 60:
            banco.registrar_atividade(st.session_state["usuario"], "Saiu por inatividade")
            st.session_state["logado"] = False
            st.session_state["usuario"] = ""
            st.session_state["admin"] = False
            st.toast("Tempo de inatividade atingido.", icon=":material/timer_off:")
    st.session_state["ultima_atividade"] = agora
#______________________________________________________________________________________________________________________#
#Diz se o nome é o mesmo do administrador (compara com o st.secrets)

def e_nome_do_admin(nome):
    usuario_admin = st.secrets["admin"]["usuario"].strip().lower()
    return nome.strip().lower() == usuario_admin
#______________________________________________________________________________________________________________________#
#Formulário Minha senha (usado na Minha conta e na troca obrigatória): devolve True quando a senha foi trocada

def conferir_troca_de_senha(usuario, senha_atual, senha_nova, confirmacao):
    if banco.esta_bloqueado(usuario):
        return visual.aviso_conta("Não foi possível trocar a senha!",
                                  "Muitas tentativas erradas. Aguarde 15 minutos e tente novamente.", erro=True), False

    if senha_atual == "":
        return visual.aviso_conta("Não foi possível trocar a senha!",
                                  "A senha atual não confere. Confira e tente de novo.", erro=True), False

    if banco.conferir_senha(usuario, senha_atual) == False:
        banco.registrar_erro(usuario)
        banco.registrar_atividade(usuario, "Senha errada")
        return visual.aviso_conta("Não foi possível trocar a senha!",
                                  "A senha atual não confere. Confira e tente de novo.", erro=True), False

    banco.limpar_erros(usuario)

    if senha_segue_regras(senha_nova) == False or senha_nova == senha_atual:
        return visual.aviso_conta("A senha nova ainda não segue as regras!",
                                  "Ela deve ter pelo menos 12 caracteres, com letras e números, e ser diferente da atual.",
                                  erro=True), False

    if confirmacao != senha_nova:
        return visual.aviso_conta("As senhas novas não são iguais!",
                                  "Digite a mesma senha nova nos dois campos.", erro=True), False

    if banco.trocar_senha(usuario, senha_nova) == False:
        return visual.aviso_conta("Não foi possível trocar a senha!",
                                  "Não foi possível salvar a senha nova. Tente de novo.", erro=True), False

    banco.liberar_troca_de_senha(usuario)
    banco.registrar_atividade(usuario, "Trocou a senha")
    return visual.aviso_conta("Senha trocada!", "Use a senha nova a partir do próximo login.", erro=False), True


def mostrar_formulario_senha(usuario):
    with st.form("formulario_senha", clear_on_submit=True, border=False):
        st.html('<h2 class="titulo-bloco">Minha senha</h2>')
        senha_atual = st.text_input("Senha atual", type="password", autocomplete="current-password")
        senha_nova = st.text_input("Senha nova", type="password", autocomplete="new-password")
        confirmacao = st.text_input("Confirme a senha nova", type="password", autocomplete="new-password")
        enviar = st.form_submit_button("Salvar nova senha")
        espaco_aviso = st.empty()

    trocou = False
    if enviar:
        aviso, trocou = conferir_troca_de_senha(usuario, senha_atual, senha_nova, confirmacao)
        espaco_aviso.html(aviso)
    return trocou
#______________________________________________________________________________________________________________________#