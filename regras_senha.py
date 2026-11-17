import secrets

CARACTERES_SENHA_TEMPORARIA = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
#______________________________________________________________________________________________________________________#
#Confere se a senha segue as regras: 12 caracteres ou mais, com letra e número, e no máximo 72 bytes

def senha_segue_regras(senha):
    if len(senha) < 12:
        return False

    if len(senha.encode("utf-8")) > 72:
        return False

    tem_letra = False
    tem_numero = False
    for caractere in senha:
        if caractere.isalpha():
            tem_letra = True
        if caractere in "0123456789":
            tem_numero = True

    return tem_letra and tem_numero
#______________________________________________________________________________________________________________________#
#Gera uma senha temporária com 3 grupos de 4 caracteres (exemplo: Rk4p-vT9q-2mWx)

def gerar_senha_temporaria():
    while True:
        grupos = []
        for numero_do_grupo in range(3):
            grupo = ""
            for posicao in range(4):
                grupo += secrets.choice(CARACTERES_SENHA_TEMPORARIA)
            grupos.append(grupo)

        senha = "-".join(grupos)
        if senha_segue_regras(senha):
            return senha
#______________________________________________________________________________________________________________________#
