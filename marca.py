import base64
from html import escape
from pathlib import Path
import streamlit as st

PASTA_PROJETO = Path(__file__).parent.resolve()
NOME_PADRAO = "Empresa Exemplo"
RAZAO_SOCIAL_PADRAO = "Empresa Exemplo Ltda."
TIPOS_LOGO = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
#______________________________________________________________________________________________________________________#
#Valores usados quando o secrets não tem a seção [marca]

def marca_padrao():
    return {"nome_curto": NOME_PADRAO, "razao_social": RAZAO_SOCIAL_PADRAO, "caminho_logo": None}
#______________________________________________________________________________________________________________________#
#Aceita a logo só se o arquivo existir, estiver dentro da pasta do projeto e tiver extensão de imagem permitida

def validar_caminho_logo(caminho):
    if not isinstance(caminho, str) or caminho.strip() == "":
        return None
    try:
        completo = (PASTA_PROJETO / caminho.strip()).resolve()
        if not completo.is_relative_to(PASTA_PROJETO):
            return None
        if completo.suffix.lower() not in TIPOS_LOGO:
            return None
        if not completo.is_file():
            return None
    except Exception:
        return None
    return str(completo)
#______________________________________________________________________________________________________________________#
#Lê a seção [marca] do st.secrets (campos vazios ou ausentes ficam com o valor padrão)

def ler_marca():
    dados = marca_padrao()
    try:
        secao = st.secrets.get("marca", {})
        nome = secao.get("nome_curto", "")
        razao = secao.get("razao_social", "")
        caminho = secao.get("caminho_logo", "")
    except Exception:
        return dados

    if isinstance(nome, str) and nome.strip() != "":
        dados["nome_curto"] = nome.strip()
    if isinstance(razao, str) and razao.strip() != "":
        dados["razao_social"] = razao.strip()
    dados["caminho_logo"] = validar_caminho_logo(caminho)
    return dados
#______________________________________________________________________________________________________________________#
#Transforma a logo em data URI base64 (o SVG nunca vai colado no HTML, só dentro de um <img>)

def logo_em_data_uri(dados=None):
    if dados is None:
        dados = ler_marca()
    caminho = dados["caminho_logo"]
    if caminho is None:
        return None
    try:
        conteudo = Path(caminho).read_bytes()
    except Exception:
        return None
    tipo = TIPOS_LOGO[Path(caminho).suffix.lower()]
    return f"data:{tipo};base64,{base64.b64encode(conteudo).decode('ascii')}"


def logo_em_img(altura, dados=None):
    if dados is None:
        dados = ler_marca()
    nome = escape(dados["nome_curto"])
    endereco = logo_em_data_uri(dados)
    if endereco is None:
        return nome
    return f'<img src="{endereco}" alt="{nome}" style="height: {int(altura)}px; width: auto">'
#______________________________________________________________________________________________________________________#
#Texto do rodapé com a razão social (já escapada)

def texto_rodape(ano, dados=None):
    if dados is None:
        dados = ler_marca()
    razao = dados["razao_social"].rstrip(".")
    return f"© {int(ano)} {escape(razao)}. Todos os direitos reservados."
