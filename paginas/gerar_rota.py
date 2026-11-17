from datetime import datetime, time, timedelta
from urllib.parse import quote
import streamlit as st
import banco
import funcoes
import marca
import pdf_rota
import rota
import textos
import visual

if st.session_state.get("logado") != True:
    st.stop()

TOKEN_ACESSO = st.secrets["gestaoclick"]["access_token"]
TOKEN_SECRETO = st.secrets["gestaoclick"]["secret_access_token"]
CHAVE_MAPS = st.secrets["google_maps"]["api_key"]
ENDERECO_BASE = st.secrets["empresa"]["endereco_base"]

COTA_GRATIS_ELEMENTOS = rota.COTA_GRATIS_ELEMENTOS
MAXIMO_ENTREGAS = 10
FORMATO_ROTA = 2
DIAS_DA_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

visual.estilo_pagina_interna()
visual.estilo_gerar_rota()

if "gerando_rota" not in st.session_state:
    st.session_state["gerando_rota"] = False
    st.session_state["ultima_rota"] = None
if "paradas_extras" not in st.session_state:
    st.session_state["paradas_extras"] = []
    st.session_state["painel_extras_aberto"] = False
    st.session_state["cliente_encontrado"] = None
    st.session_state["aviso_extras"] = None
if "cache_transportadoras" not in st.session_state:
    st.session_state["cache_transportadoras"] = {}
if "transportadoras_encontradas" not in st.session_state:
    st.session_state["transportadoras_encontradas"] = []
    st.session_state["transportadora_escolhida"] = None
    st.session_state["aviso_transportadora"] = None

if "aviso_rota" in st.session_state:
    texto_aviso, icone_aviso = st.session_state.pop("aviso_rota")
    st.toast(texto_aviso, icon=icone_aviso)
#______________________________________________________________________________________________________________________#
#Transforma segundos em texto de horas, como 2h55

def segundos_em_horas(segundos):
    minutos = round(segundos / 60)
    return f"{minutos // 60}h{minutos % 60:02d}"


def pedir_rota():
    st.session_state["gerando_rota"] = True
#______________________________________________________________________________________________________________________#
#Abre e fecha o painel de paradas extras, adiciona e remove paradas

def limpar_transportadora():
    st.session_state["transportadoras_encontradas"] = []
    st.session_state["transportadora_escolhida"] = None
    st.session_state["aviso_transportadora"] = None
    st.session_state.pop("nome_transportadora", None)
    st.session_state.pop("escolha_transportadora", None)


def limpar_busca():
    st.session_state["cliente_encontrado"] = None
    st.session_state["aviso_extras"] = None
    st.session_state.pop("nf_extra", None)
    st.session_state.pop("volume_extra", None)
    limpar_transportadora()


def alternar_painel_extras():
    st.session_state["painel_extras_aberto"] = not st.session_state["painel_extras_aberto"]
    limpar_busca()


def cancelar_busca():
    st.session_state["painel_extras_aberto"] = False
    limpar_busca()


def cliente_ja_adicionado(cliente_id):
    for parada in st.session_state["paradas_extras"]:
        if parada["cliente_id"] == cliente_id:
            return True
    return False


def transportadora_da_parada():
    encontradas = st.session_state["transportadoras_encontradas"]
    if len(encontradas) > 1:
        return st.session_state.get("escolha_transportadora")
    return st.session_state["transportadora_escolhida"]


def adicionar_parada():
    encontrado = st.session_state["cliente_encontrado"]
    if encontrado is None:
        return
    if len(st.session_state["paradas_extras"]) >= MAXIMO_ENTREGAS:
        st.session_state["aviso_extras"] = ("Limite de paradas extras atingido!",
                                            f"A rota aceita no máximo {MAXIMO_ENTREGAS} entregas.")
        return
    if cliente_ja_adicionado(encontrado["cliente_id"]):
        st.session_state["cliente_encontrado"] = None
        st.session_state["aviso_extras"] = ("Esse cliente já está nas paradas extras.", "")
        return

    try:
        nf = banco.conferir_nf_opcional(st.session_state.get("nf_extra"))
        volume = banco.conferir_volume_opcional(st.session_state.get("volume_extra"))
    except ValueError as erro:
        st.session_state["aviso_extras"] = (str(erro), "")
        return

    transportadora_id = transportadora_da_parada()
    nome_digitado = st.session_state.get("nome_transportadora") or ""
    if transportadora_id is None and len(st.session_state["transportadoras_encontradas"]) > 1:
        st.session_state["aviso_extras"] = ("Escolha uma das transportadoras encontradas.",
                                            "Ou clique em Limpar para entregar no endereço do cliente.")
        return
    if transportadora_id is None and nome_digitado.strip() != "":
        st.session_state["aviso_extras"] = ("A transportadora ainda não foi buscada.",
                                            "Clique em Buscar transportadora ou apague o nome para entregar no cliente.")
        return

    nova = dict(encontrado)
    nova["motivo"] = st.session_state["motivo_extra"]
    nova["nf"] = nf
    nova["volume"] = volume
    nova["transportadora_id"] = transportadora_id
    st.session_state["paradas_extras"].append(nova)
    limpar_busca()


def remover_parada(cliente_id):
    restantes = []
    for parada in st.session_state["paradas_extras"]:
        if parada["cliente_id"] != cliente_id:
            restantes.append(parada)
    st.session_state["paradas_extras"] = restantes
#______________________________________________________________________________________________________________________#
#Busca o cliente da parada extra pelo CPF ou CNPJ (o documento e a ficha não ficam guardados)

def buscar_parada_extra(documento):
    if len(st.session_state["paradas_extras"]) >= MAXIMO_ENTREGAS:
        return ("Limite de paradas extras atingido!", f"A rota aceita no máximo {MAXIMO_ENTREGAS} entregas.")
    if funcoes.limpar_documento(documento) is None:
        return ("CPF ou CNPJ inválido!", "Digite os 11 números do CPF ou os 14 números do CNPJ.")

    try:
        with st.spinner("Buscando o cliente no GestãoClick..."):
            ficha = funcoes.buscar_cliente_por_documento(documento, TOKEN_ACESSO, TOKEN_SECRETO)
    except funcoes.ErroAPI as erro:
        return ("Não foi possível buscar o cliente!", str(erro))

    if ficha is None:
        return ("Cliente não encontrado!",
                "Confira o CPF ou CNPJ no GestãoClick. Se estiver certo, o cliente pode ter mais de um cadastro.")

    parada = funcoes.montar_parada_extra(ficha, "")
    if parada is None:
        return ("Cliente sem endereço cadastrado no GestãoClick.", "")
    if cliente_ja_adicionado(parada["cliente_id"]):
        return ("Esse cliente já está nas paradas extras.", "")

    st.session_state["cliente_encontrado"] = parada
    return None
#______________________________________________________________________________________________________________________#
#Busca a transportadora da parada extra pelo nome (guarda só o número dela na parada)

def buscar_transportadora():
    st.session_state["transportadoras_encontradas"] = []
    st.session_state["transportadora_escolhida"] = None
    st.session_state["aviso_transportadora"] = None
    st.session_state.pop("escolha_transportadora", None)

    try:
        encontradas = funcoes.procurar_transportadoras_por_nome(st.session_state.get("nome_transportadora") or "",
                                                                TOKEN_ACESSO, TOKEN_SECRETO)
    except ValueError as erro:
        st.session_state["aviso_transportadora"] = (str(erro), "")
        return
    except funcoes.ErroAPI as erro:
        st.session_state["aviso_transportadora"] = ("Não foi possível buscar a transportadora!", str(erro))
        return

    if len(encontradas) == 0:
        st.session_state["aviso_transportadora"] = ("Transportadora não encontrada", "")
        return

    for transportadora in encontradas:
        st.session_state["cache_transportadoras"][transportadora["id"]] = transportadora
    st.session_state["transportadoras_encontradas"] = encontradas
    if len(encontradas) == 1:
        st.session_state["transportadora_escolhida"] = encontradas[0]["id"]


def texto_da_transportadora(transportadora_id):
    transportadora = st.session_state["cache_transportadoras"].get(transportadora_id)
    if transportadora is None:
        return f"Transportadora {transportadora_id}"
    return textos.escapar_markdown(f"{transportadora['nome']} – {funcoes.enderecos_em_texto(transportadora['endereco'])}")


def detalhe_da_parada_extra(parada):
    if parada.get("transportadora_id") is None:
        destino = funcoes.enderecos_em_texto(parada["endereco"])
    else:
        transportadora = st.session_state["cache_transportadoras"].get(parada["transportadora_id"])
        nome = f"Transportadora {parada['transportadora_id']}"
        if transportadora is not None:
            nome = transportadora["nome"]
        destino = f"Transportadora: {nome}"
    return rota.juntar_partes([destino, rota.texto_nf(parada.get("nf")), rota.texto_volumes(parada.get("volume"))])
#______________________________________________________________________________________________________________________#
#Monta a lista de paradas que aparece na tela, no PDF e no Maps

def nome_da_parada_extra(nome, cliente_id):
    if nome != "":
        return nome
    return f"Cliente {cliente_id}"


def paradas_do_resultado(resultado):
    paradas = []
    for parada in resultado["paradas"]:
        paradas.append(rota.parada_para_exibir(parada, parada["endereco"]))
    return paradas
#______________________________________________________________________________________________________________________#
#Remonta a última rota salva no banco, buscando os endereços de novo no GestãoClick

def carregar_ultima_rota(salva):
    agrupadas = banco.agrupar_em_paradas(salva["itens"])
    paradas = []
    enderecos_ok = True
    try:
        for parada in agrupadas:
            endereco = rota.buscar_endereco_da_parada(parada, st.session_state["cache_transportadoras"],
                                                      TOKEN_ACESSO, TOKEN_SECRETO)
            if endereco == "":
                endereco = "Endereço não encontrado no GestãoClick"
                enderecos_ok = False
            paradas.append(rota.parada_para_exibir(parada, endereco))
    except funcoes.ErroAPI:
        paradas = []
        for parada in agrupadas:
            paradas.append(rota.parada_para_exibir(parada, "Endereço indisponível no momento"))
        enderecos_ok = False
        st.toast("Não foi possível buscar os endereços no GestãoClick agora.", icon=":material/error:")

    resultado = {"paradas": paradas,
                 "tempo_de_entrega": salva["tempo_de_entrega"],
                 "tempo_disponivel": salva["tempo_disponivel"],
                 "cabe_no_horario": salva["tempo_de_entrega"] <= salva["tempo_disponivel"],
                 "problemas": salva["problemas"],
                 "quantidade_pedida": salva["quantidade_pedida"],
                 "hora_saida": datetime.strptime(salva["hora_saida"], "%H:%M").time(),
                 "gerada_em": datetime.strptime(salva["gerada_em"], "%Y-%m-%d %H:%M:%S"),
                 "gerada_em_texto": salva["gerada_em"],
                 "enderecos_ok": enderecos_ok,
                 "formato": FORMATO_ROTA}
    return resultado
#______________________________________________________________________________________________________________________#
#Separa cada problema em (destaque, explicação) para o quadro "Ficaram para a próxima"

def separar_problema(problema):
    try:
        if problema.startswith("Parada extra "):
            cliente_e_motivo, explicacao = problema.removeprefix("Parada extra ").split(": ", 1)
            cliente_id, motivo = cliente_e_motivo.split(" ", 1)
            return ("Parada extra", f"cliente {cliente_id} · {motivo.strip('()')} · {explicacao.rstrip('.')}")
        codigo, motivo = problema.removeprefix("Pedido ").split(" ", 1)
        return (codigo.rstrip(":"), motivo.rstrip("."))
    except ValueError:
        return ("", problema)
#______________________________________________________________________________________________________________________#
#Carrega a rota que está valendo: pendente e gerada hoje, conferindo no banco a cada carregamento

salva = banco.ultima_rota_valendo()
if salva is None:
    st.session_state["ultima_rota"] = None
else:
    na_sessao = st.session_state["ultima_rota"]
    if (na_sessao is None or na_sessao.get("formato") != FORMATO_ROTA
            or na_sessao["gerada_em_texto"] != salva["gerada_em"]):
        with st.spinner("Carregando a última rota..."):
            st.session_state["ultima_rota"] = carregar_ultima_rota(salva)
#______________________________________________________________________________________________________________________#
#Título, botão do PDF e formulário

ultima = st.session_state["ultima_rota"]
dados_pdf = b""
nome_pdf = "rota.pdf"
if ultima is not None and len(ultima["paradas"]) > 0 and ultima["enderecos_ok"]:
    gerada = ultima["gerada_em"]
    retorno_pdf = datetime.combine(gerada.date(), ultima["hora_saida"]) + timedelta(seconds=ultima["tempo_de_entrega"])
    dados_pdf = pdf_rota.montar_pdf(DIAS_DA_SEMANA[gerada.weekday()], gerada.strftime("%d/%m/%Y"),
                                    ultima["hora_saida"].strftime("%H:%M"), retorno_pdf.strftime("%H:%M"),
                                    ultima["paradas"], st.session_state["usuario"],
                                    datetime.now().strftime("%d/%m/%Y %H:%M"), marca.ler_marca())
    nome_pdf = f"rota_{gerada.strftime('%d-%m-%Y')}.pdf"

with st.container(key="topo_rota", horizontal=True, horizontal_alignment="distribute", vertical_alignment="bottom"):
    visual.titulo_pagina("Gerar rota")
    if ultima is not None:
        st.download_button("Baixar PDF", data=dados_pdf, file_name=nome_pdf, mime="application/pdf",
                           key="baixar_pdf", help="Baixar PDF", on_click="ignore", disabled=(dados_pdf == b""))

with st.form("form_rota", border=False):
    with st.container(key="caixa_formulario", horizontal=True, vertical_alignment="bottom"):
        st.number_input("Entregas (1 a 10)", min_value=1, max_value=MAXIMO_ENTREGAS, value=8, step=1, key="quantidade_rota")
        st.time_input("Saída", value=time(8, 0), step=300, key="hora_saida")
        st.time_input("Retorno até", value=time(12, 0), step=300, key="hora_retorno")
        st.form_submit_button("Gerar rota", on_click=pedir_rota, disabled=st.session_state["gerando_rota"])

pedidos_incompletos = banco.pedidos_sem_nf_ou_volume()
if len(pedidos_incompletos) > 0:
    st.html(visual.aviso_extras("Há pedidos sem NF ou volume!", rota.mensagem_pedidos_incompletos(pedidos_incompletos)))
#______________________________________________________________________________________________________________________#
#Caixa Paradas extras (começa fechada)

with st.container(key="caixa_extras"):
    with st.container(key="topo_extras", horizontal=True, vertical_alignment="center"):
        st.html('<h2 class="titulo-extras">Paradas extras</h2>')
        if st.session_state["painel_extras_aberto"]:
            texto_botao_extras = "Fechar"
        else:
            texto_botao_extras = "\\+ Adicionar parada extra"
        st.button(texto_botao_extras, key="abrir_extras", on_click=alternar_painel_extras)

    if st.session_state["painel_extras_aberto"]:
        with st.container(key="painel_extras"):
            with st.form("form_busca_extra", clear_on_submit=True, border=False):
                with st.container(key="campos_busca", horizontal=True, vertical_alignment="bottom"):
                    documento = st.text_input("CPF ou CNPJ do cliente", placeholder="Só números", max_chars=20,
                                              autocomplete="off")
                    buscar = st.form_submit_button("Buscar", key="buscar_extra")
                    st.form_submit_button("Cancelar", key="cancelar_extra", on_click=cancelar_busca)

        if buscar:
            limpar_busca()
            st.session_state["aviso_extras"] = buscar_parada_extra(documento)
        documento = ""

        aviso = st.session_state["aviso_extras"]
        if aviso is not None:
            st.html(visual.aviso_extras(aviso[0], aviso[1]))

        encontrado = st.session_state["cliente_encontrado"]
        if encontrado is not None:
            with st.container(key="cartao_extra"):
                with st.container(key="cartao_cliente", horizontal=True, vertical_alignment="bottom"):
                    st.html(visual.cliente_encontrado(nome_da_parada_extra(encontrado["nome"], encontrado["cliente_id"]),
                                                      funcoes.enderecos_em_texto(encontrado["endereco"])))
                    st.selectbox("Motivo", banco.MOTIVOS_PARADA_EXTRA, key="motivo_extra")
                    st.text_input("Nº da NF (opcional)", key="nf_extra", max_chars=banco.TAMANHO_MAXIMO_NF,
                                  autocomplete="off")
                    st.text_input("Volume (opcional)", key="volume_extra", max_chars=len(str(banco.VOLUME_MAXIMO)),
                                  autocomplete="off")

                with st.container(key="busca_transportadora", horizontal=True, vertical_alignment="bottom"):
                    st.text_input("Nome da transportadora (opcional)", key="nome_transportadora", max_chars=60,
                                  placeholder="Pelo menos 3 letras", autocomplete="off")
                    st.button("Buscar transportadora", key="buscar_transportadora", on_click=buscar_transportadora)
                    if st.session_state["transportadora_escolhida"] is not None or len(st.session_state["transportadoras_encontradas"]) > 0:
                        st.button("Limpar", key="limpar_transportadora", on_click=limpar_transportadora)
                st.html(visual.ajuda_extras("Sem transportadora, a entrega é feita no endereço do cliente."))

                aviso_transportadora = st.session_state["aviso_transportadora"]
                if aviso_transportadora is not None:
                    st.html(visual.aviso_extras(aviso_transportadora[0], aviso_transportadora[1]))

                encontradas = st.session_state["transportadoras_encontradas"]
                if len(encontradas) > 1:
                    opcoes = []
                    for transportadora in encontradas:
                        opcoes.append(transportadora["id"])
                    st.radio("Escolha a transportadora", opcoes, index=None, format_func=texto_da_transportadora,
                             key="escolha_transportadora")
                elif st.session_state["transportadora_escolhida"] is not None:
                    escolhida = st.session_state["cache_transportadoras"][st.session_state["transportadora_escolhida"]]
                    st.html(visual.transportadora_escolhida(escolhida["nome"],
                                                            funcoes.enderecos_em_texto(escolhida["endereco"])))

                with st.container(key="rodape_cartao", horizontal=True):
                    st.button("Adicionar à rota", key="adicionar_extra", on_click=adicionar_parada)

    posicao = 0
    for parada in st.session_state["paradas_extras"]:
        with st.container(key=f"linha_extra_{posicao}", horizontal=True, vertical_alignment="center"):
            st.html(visual.linha_parada_extra(nome_da_parada_extra(parada["nome"], parada["cliente_id"]),
                                              parada["motivo"], detalhe_da_parada_extra(parada)))
            st.button("Remover", key=f"remover_extra_{posicao}", on_click=remover_parada, args=(parada["cliente_id"],))
        posicao += 1
#______________________________________________________________________________________________________________________#
#Barra da cota grátis do mês

usados = banco.elementos_usados_no_mes()
porcentagem = int(min(100, usados * 100 / COTA_GRATIS_ELEMENTOS))
elementos_por_rota = (st.session_state["quantidade_rota"] + 1) ** 2
rotas_restantes = max(0, (COTA_GRATIS_ELEMENTOS - usados) // elementos_por_rota)
st.html(visual.barra_cota(porcentagem, rotas_restantes))
#______________________________________________________________________________________________________________________#
#Gera a rota (só roda depois do clique, com o botão bloqueado)

if st.session_state["gerando_rota"]:
    pedidos_salvos = banco.listar_pedidos_completos()
    paradas_extras = st.session_state["paradas_extras"]
    quantidade = st.session_state["quantidade_rota"]
    hora_saida = st.session_state["hora_saida"]
    hora_retorno = st.session_state["hora_retorno"]
    quantidade_extras = rota.contar_paradas_extras(paradas_extras)
    previstos = rota.elementos_previstos(len(pedidos_salvos), quantidade_extras, quantidade)
    bloqueio = rota.conferir_antes_de_gerar(len(pedidos_salvos), quantidade_extras, quantidade)
    incompletos = banco.pedidos_sem_nf_ou_volume()

    if banco.data_rota_pendente() is not None:
        st.session_state["aviso_rota"] = ("Confirme as entregas da rota anterior antes de gerar uma nova.", ":material/block:")
    elif len(incompletos) > 0:
        st.session_state["aviso_rota"] = (rota.mensagem_pedidos_incompletos(incompletos), ":material/error:")
    elif bloqueio is not None:
        st.session_state["aviso_rota"] = (bloqueio, ":material/error:")
    elif hora_retorno <= hora_saida:
        st.session_state["aviso_rota"] = ("A hora de retorno precisa ser depois da hora de saída.", ":material/error:")
    elif usados + previstos > COTA_GRATIS_ELEMENTOS:
        st.session_state["aviso_rota"] = ("A cota grátis do mês acabou. A rota não foi gerada para evitar cobrança.", ":material/block:")
    else:
        with st.status("Gerando a rota...", expanded=True) as status:
            st.write("Buscando endereços no GestãoClick e calculando as distâncias no Google Maps.")
            try:
                resultado = rota.gerar_rota(pedidos_salvos, quantidade, hora_saida, hora_retorno,
                                            TOKEN_ACESSO, TOKEN_SECRETO, CHAVE_MAPS, ENDERECO_BASE, paradas_extras,
                                            st.session_state["cache_transportadoras"])
                gerada_em_texto = banco.salvar_rota_gerada(
                    st.session_state["usuario"], hora_saida.strftime("%H:%M"), resultado["itens_na_rota"],
                    resultado["tempo_de_entrega"], resultado["tempo_disponivel"], resultado["quantidade_pedida"],
                    resultado["problemas"], resultado["elementos_usados"])
            except (funcoes.ErroAPI, ValueError) as erro:
                status.update(label=str(erro), state="error", expanded=False)
                st.session_state["aviso_rota"] = (str(erro), ":material/error:")
                resultado = None
                gerada_em_texto = None

            if resultado is not None and gerada_em_texto is None:
                status.update(label=rota.MENSAGEM_TEMPO_INVALIDO, state="error", expanded=False)
                st.session_state["aviso_rota"] = (rota.MENSAGEM_TEMPO_INVALIDO, ":material/error:")
            elif gerada_em_texto is not None:
                st.session_state["ultima_rota"] = {"paradas": paradas_do_resultado(resultado),
                                                   "tempo_de_entrega": resultado["tempo_de_entrega"],
                                                   "tempo_disponivel": resultado["tempo_disponivel"],
                                                   "cabe_no_horario": resultado["cabe_no_horario"],
                                                   "problemas": resultado["problemas"],
                                                   "quantidade_pedida": resultado["quantidade_pedida"],
                                                   "hora_saida": hora_saida,
                                                   "gerada_em": datetime.strptime(gerada_em_texto, "%Y-%m-%d %H:%M:%S"),
                                                   "gerada_em_texto": gerada_em_texto,
                                                   "enderecos_ok": True,
                                                   "formato": FORMATO_ROTA}
                st.session_state["paradas_extras"] = []
                st.session_state["painel_extras_aberto"] = False
                limpar_busca()
                status.update(label="Rota gerada.", state="complete", expanded=False)
                if len(resultado["paradas"]) == 0:
                    texto_vazia = "Nenhuma entrega pôde entrar na rota."
                    if len(resultado["problemas"]) > 0:
                        texto_vazia += " " + " ".join(resultado["problemas"])
                    st.session_state["aviso_rota"] = (texto_vazia, ":material/error:")

    st.session_state["gerando_rota"] = False
    st.rerun()
#______________________________________________________________________________________________________________________#
#Resultado da última rota

resultado = st.session_state["ultima_rota"]
if resultado is not None:
    gerada_em = resultado["gerada_em"]
    if gerada_em.date() == datetime.now().date():
        inicio_titulo = "Rota de hoje"
    else:
        inicio_titulo = "Última rota"
    titulo = f"{inicio_titulo}, {DIAS_DA_SEMANA[gerada_em.weekday()]}, {gerada_em.strftime('%d/%m/%Y')}"

    paradas = resultado["paradas"]
    sobra = resultado["tempo_disponivel"] - resultado["tempo_de_entrega"]
    if len(paradas) == 0:
        situacao = '<span class="situacao-rota erro">Nenhuma entrega pôde entrar na rota</span>'
    elif resultado["cabe_no_horario"]:
        situacao = f'<span class="situacao-rota">Dentro do horário, sobram {segundos_em_horas(sobra)}</span>'
    else:
        situacao = f'<span class="situacao-rota erro">Passa do horário em {segundos_em_horas(-sobra)}</span>'

    enderecos = []
    for parada in paradas:
        enderecos.append(parada["endereco"])

    link_maps = ""
    if len(enderecos) > 0 and resultado["enderecos_ok"]:
        link_maps = "https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=" + quote(enderecos[-1])
        if len(enderecos) > 1:
            link_maps += "&waypoints=" + quote("|".join(enderecos[:-1]))

    nao_entraram = []
    for problema in resultado["problemas"]:
        nao_entraram.append(separar_problema(problema))

    retorno = datetime.combine(gerada_em.date(), resultado["hora_saida"]) + timedelta(seconds=resultado["tempo_de_entrega"])

    st.html(visual.resultado_rota(titulo, situacao, len(paradas), resultado["quantidade_pedida"],
                                  round(resultado["tempo_de_entrega"] / 60), round(resultado["tempo_disponivel"] / 60),
                                  link_maps, resultado["hora_saida"].strftime("%H:%M"), paradas, nao_entraram,
                                  retorno.strftime("%H:%M")))
