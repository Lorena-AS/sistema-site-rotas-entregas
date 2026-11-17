import getpass
import bcrypt
from regras_senha import senha_segue_regras
#______________________________________________________________________________________________________________________#
#Pede a senha do administrador, confere as regras e mostra o hash para o secrets.toml

senha = getpass.getpass("Digite a senha do administrador: ")
confirmacao = getpass.getpass("Confirme a senha: ")

if senha != confirmacao:
    print("As senhas não conferem. Rode o programa de novo.")
elif senha_segue_regras(senha) == False:
    print("A senha deve ter pelo menos 12 caracteres, com letras e números, e no máximo 72 bytes.")
else:
    hash_senha = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
    print("Copie a linha abaixo para o secrets.toml:")
    print(hash_senha.decode("utf-8"))