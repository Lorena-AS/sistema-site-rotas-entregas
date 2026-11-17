import re

PADRAO_CPF = re.compile(r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)")
PONTAS_SOLTAS = " -.–—"
CARACTERES_MARKDOWN = "\\`*_{}[]()#+-.!|>~<:"
#______________________________________________________________________________________________________________________#
#Tira o CPF dos nomes que vêm do GestãoClick (minimização de dados)

def esconder_cpf(texto, texto_se_vazio="Cliente sem nome"):
    """
    Recebe um nome vindo do GestãoClick e, se quiser, o texto para quando não sobrar nada.
    Retorna o nome sem CPF (exatamente 11 dígitos, com ou sem a pontuação ddd.ddd.ddd-dd, mesmo colado em letras),
    sem espaços duplicados e sem traços ou pontos soltos nas pontas / texto_se_vazio, se não sobrar nada.
    CNPJ (14 dígitos) e outros números ficam como estão.
    """
    if texto is None:
        texto = ""
    sem_cpf = PADRAO_CPF.sub(" ", str(texto))
    limpo = " ".join(sem_cpf.split()).strip(PONTAS_SOLTAS)
    if limpo == "":
        return texto_se_vazio
    return limpo
#______________________________________________________________________________________________________________________#
#Protege os textos que o Streamlit mostra como markdown (nenhum nome vira link ou formatação)

def escapar_markdown(texto):
    """
    Recebe um texto (por exemplo, nome e endereço de uma transportadora).
    Retorna o texto com uma barra invertida antes de cada caractere que o markdown usa.
    """
    escapado = []
    for caractere in str(texto):
        if caractere in CARACTERES_MARKDOWN:
            escapado.append("\\" + caractere)
        else:
            escapado.append(caractere)
    return "".join(escapado)
#______________________________________________________________________________________________________________________#
