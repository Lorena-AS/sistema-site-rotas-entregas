import math
import sqlite3 # banco de dados SQLite
from pathlib import Path # montar caminhos de arquivos no computador
from datetime import datetime, timedelta # biblioteca para pegar a data e a hora atual e somar tempo a ela
import bcrypt # transforma a senha em hash (texto embaralhado)
import textos

CAMINHO_BANCO = Path(__file__).parent / "dados.db" # o banco fica na mesma pasta deste arquivo, com o nome dados.db
MAX_TENTATIVAS = 5 # sequencia de senhas erradas seguidas antes de bloquear
MINUTOS_BLOQUEIO = 15 # tempo que o usuário fica bloqueado, em minutos
DIAS_GUARDAR_DADOS = 60 # o log/histórico guarda só os últimos 2 meses
TAMANHO_MAXIMO_MOTIVO = 60
MOTIVOS_PARADA_EXTRA = ["Retirada de material", "Entrega de material", "Retirada de amostra", "Entrega de amostra",
                        "Troca de mercadoria"]
TAMANHO_MAXIMO_NF = 9
VOLUME_MAXIMO = 9999
DESTINOS_VALIDOS = ("transportadora", "cliente")
TAMANHO_MAXIMO_NOME = 120
TAMANHO_MAXIMO_CODIGO = 18
MENSAGEM_LISTA_ALTERADA = "A lista foi alterada em outro lugar. Recarregue antes de salvar."
MENSAGEM_ROTA_JA_GERADA = "Outra pessoa acabou de gerar uma rota. Confirme as entregas dela antes de gerar outra."
MENSAGEM_BANCO_OCUPADO = "O sistema está gravando outra alteração agora. Tente de novo em alguns segundos."
COLUNAS_COM_NOME = (("rota_pendente", "cliente_nome"),
                    ("rota_pendente", "destino_nome"),
                    ("rota_pendente_extras", "cliente_nome"),
                    ("rota_pendente_extras", "destino_nome"),
                    ("ultima_rota_pedidos", "cliente_nome"),
                    ("ultima_rota_pedidos", "destino_nome"),
                    ("ultima_rota_extras", "cliente_nome"),
                    ("ultima_rota_extras", "destino_nome"),
                    ("historico_entregas", "cliente_nome"),
                    ("historico_entregas", "destino_nome"))
MIGRACOES = (("pedidos", "nf", "INTEGER"),
             ("pedidos", "volume", "INTEGER"),
             ("pedidos", "entregar_no", "TEXT"),
             ("rota_pendente", "nf", "INTEGER"),
             ("rota_pendente", "volume", "INTEGER"),
             ("rota_pendente", "destino_tipo", "TEXT"),
             ("rota_pendente", "destino_nome", "TEXT"),
             ("rota_pendente", "cliente_nome", "TEXT"),
             ("rota_pendente", "transportadora_id", "INTEGER"),
             ("ultima_rota", "nf", "INTEGER"),
             ("ultima_rota", "volume", "INTEGER"),
             ("ultima_rota", "destino_tipo", "TEXT"),
             ("ultima_rota", "destino_nome", "TEXT"),
             ("ultima_rota", "cliente_nome", "TEXT"),
             ("rota_pendente_extras", "nf", "INTEGER"),
             ("rota_pendente_extras", "volume", "INTEGER"),
             ("rota_pendente_extras", "transportadora_id", "INTEGER"),
             ("rota_pendente_extras", "destino_tipo", "TEXT"),
             ("rota_pendente_extras", "destino_nome", "TEXT"),
             ("rota_pendente_extras", "cliente_nome", "TEXT"),
             ("ultima_rota_extras", "nf", "INTEGER"),
             ("ultima_rota_extras", "volume", "INTEGER"),
             ("ultima_rota_extras", "transportadora_id", "INTEGER"),
             ("ultima_rota_extras", "destino_tipo", "TEXT"),
             ("ultima_rota_extras", "destino_nome", "TEXT"),
             ("ultima_rota_extras", "cliente_nome", "TEXT"))
#______________________________________________________________________________________________________________________#
#Abre a conexão com o banco de dados

def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO) # abre o banco. Se o arquivo não existir, ele é criado
    return conexao


def banco_ocupado(erro):
    """
    Recebe o erro que aconteceu numa gravação.
    Retorna True se foi o banco travado por outra gravação (esperou e não conseguiu) / False, se foi outro erro.
    """
    return isinstance(erro, sqlite3.OperationalError) and "locked" in str(erro).lower()
#______________________________________________________________________________________________________________________#
#Cria as tabelas, se ainda não existirem

def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()

    # tabela de usuários: guarda o nome de login e o hash da senha (nunca a senha real)
    cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          usuario TEXT UNIQUE NOT NULL,
                          senha_hash TEXT NOT NULL,
                          criado_em TEXT NOT NULL)""")

    # tabela de tentativas: conta as senhas erradas e guarda até quando o usuário fica bloqueado
    cursor.execute("""CREATE TABLE IF NOT EXISTS tentativas_login (
                          usuario TEXT PRIMARY KEY,
                          erros INTEGER NOT NULL,
                          bloqueado_ate TEXT)""")

    # tabela de configurações: guarda ajustes do sistema
    cursor.execute("""CREATE TABLE IF NOT EXISTS configuracoes (
                          chave TEXT PRIMARY KEY,
                          valor TEXT NOT NULL)""")

    # tabela de histórico: guarda cada rota gerada
    cursor.execute("""CREATE TABLE IF NOT EXISTS historico (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          data_hora TEXT NOT NULL,
                          usuario TEXT NOT NULL,
                          qtd_entregas INTEGER NOT NULL,
                          elementos INTEGER NOT NULL)""")

    # tabela de log: registra quem fez o quê e quando
    cursor.execute("""CREATE TABLE IF NOT EXISTS log_atividades (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          data_hora TEXT NOT NULL,
                          usuario TEXT NOT NULL,
                          acao TEXT NOT NULL)""")

    # tabela de pedidos: a lista de pedidos prontos, com a prioridade de entrega
    cursor.execute("""CREATE TABLE IF NOT EXISTS pedidos (
                          codigo INTEGER PRIMARY KEY,
                          prioridade INTEGER NOT NULL,
                          adicionado_em TEXT NOT NULL)""")

    # tabela da rota pendente: pedidos da última rota, esperando a confirmação de entrega
    cursor.execute("""CREATE TABLE IF NOT EXISTS rota_pendente (
                          codigo INTEGER PRIMARY KEY,
                          gerada_em TEXT NOT NULL)""")

    # tabela da última rota: uma linha só (id sempre 1), com códigos e tempos, sem endereços de clientes
    cursor.execute("""CREATE TABLE IF NOT EXISTS ultima_rota (
                          id INTEGER PRIMARY KEY CHECK (id = 1),
                          gerada_em TEXT NOT NULL,
                          usuario TEXT NOT NULL,
                          hora_saida TEXT NOT NULL,
                          pedidos TEXT NOT NULL,
                          tempo_de_entrega INTEGER NOT NULL,
                          tempo_disponivel INTEGER NOT NULL,
                          quantidade_pedida INTEGER NOT NULL,
                          problemas TEXT NOT NULL)""")

    # tabela de cidades atendidas: cada cidade com o total de entregas confirmadas (nunca é apagada)
    cursor.execute("""CREATE TABLE IF NOT EXISTS cidades_atendidas (
                          cidade TEXT PRIMARY KEY,
                          entregas INTEGER NOT NULL)""")

    # tabela de clientes atendidos: só o número interno do cliente no GestãoClick, sem nome ou endereço (nunca é apagada)
    cursor.execute("""CREATE TABLE IF NOT EXISTS clientes_atendidos (
                          cliente_id INTEGER PRIMARY KEY)""")

    # tabela de rotas por usuário: total de rotas geradas por cada um (nunca é apagada)
    cursor.execute("""CREATE TABLE IF NOT EXISTS rotas_por_usuario (
                          usuario TEXT PRIMARY KEY,
                          rotas INTEGER NOT NULL)""")

    # tabela de troca de senha obrigatória: quem precisa trocar a senha temporária no próximo acesso
    cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios_trocar_senha (
                          usuario TEXT PRIMARY KEY,
                          desde TEXT NOT NULL)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS rota_pendente_extras (
                          posicao INTEGER PRIMARY KEY CHECK (posicao >= 1),
                          cliente_id INTEGER NOT NULL CHECK (typeof(cliente_id) = 'integer' AND cliente_id > 0),
                          motivo TEXT NOT NULL CHECK (length(motivo) BETWEEN 1 AND 60),
                          gerada_em TEXT NOT NULL)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS ultima_rota_extras (
                          posicao INTEGER PRIMARY KEY CHECK (posicao >= 1),
                          cliente_id INTEGER NOT NULL CHECK (typeof(cliente_id) = 'integer' AND cliente_id > 0),
                          motivo TEXT NOT NULL CHECK (length(motivo) BETWEEN 1 AND 60))""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS historico_entregas (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          data_hora TEXT NOT NULL,
                          usuario TEXT NOT NULL,
                          pedido_id INTEGER,
                          eh_extra INTEGER NOT NULL CHECK (eh_extra IN (0, 1)),
                          motivo TEXT,
                          nf INTEGER,
                          volume INTEGER,
                          destino_tipo TEXT NOT NULL CHECK (destino_tipo IN ('cliente', 'transportadora')),
                          destino_nome TEXT NOT NULL,
                          cliente_nome TEXT NOT NULL)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS ultima_rota_pedidos (
                          codigo INTEGER PRIMARY KEY,
                          nf INTEGER,
                          volume INTEGER,
                          transportadora_id INTEGER,
                          destino_tipo TEXT CHECK (destino_tipo IN ('cliente', 'transportadora')),
                          destino_nome TEXT,
                          cliente_nome TEXT)""")

    migrar_colunas(cursor)
    esconder_cpf_dos_nomes_gravados(cursor)

    conexao.commit()
    conexao.close()
#______________________________________________________________________________________________________________________#
#Adiciona as colunas novas nas tabelas que já existem, sem apagar nada

def adicionar_coluna_se_faltar(cursor, tabela, coluna, tipo):
    """
    Recebe o cursor aberto, a tabela, a coluna e o tipo.
    Adiciona a coluna só se ela ainda não existir, sem fazer o commit (quem chama faz).
    Lança ValueError se o trio não estiver na lista MIGRACOES.
    """
    if (tabela, coluna, tipo) not in MIGRACOES:
        raise ValueError("Coluna fora da lista de migrações permitidas.")

    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = []
    for linha in cursor.fetchall():
        colunas_existentes.append(linha[1])

    if coluna not in colunas_existentes:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def migrar_colunas(cursor):
    """
    Recebe o cursor aberto.
    Adiciona todas as colunas da lista MIGRACOES que ainda faltam, sem fazer o commit (quem chama faz).
    """
    for tabela, coluna, tipo in MIGRACOES:
        adicionar_coluna_se_faltar(cursor, tabela, coluna, tipo)


def esconder_cpf_dos_nomes_gravados(cursor):
    """
    Recebe o cursor aberto.
    Passa limpar_nome (que tira o CPF) nos nomes já gravados das colunas de COLUNAS_COM_NOME e atualiza só as linhas
    que mudarem, sem fazer o commit (quem chama faz). Rodar de novo não muda nada.
    Retorna quantos valores foram alterados.
    """
    alterados = 0
    for tabela, coluna in COLUNAS_COM_NOME:
        cursor.execute(f"SELECT rowid, {coluna} FROM {tabela} WHERE {coluna} IS NOT NULL")
        for rowid, valor in cursor.fetchall():
            novo = limpar_nome(valor)
            if novo != valor:
                cursor.execute(f"UPDATE {tabela} SET {coluna} = ? WHERE rowid = ?", (novo, rowid))
                alterados += 1
    return alterados
#______________________________________________________________________________________________________________________#
#Cria um usuário novo com a senha em hash

def criar_usuario(usuario, senha):
    usuario = usuario.strip().lower() # tira espaços das pontas e deixa tudo minúsculo
    senha_em_bytes = senha.encode("utf-8") # o bcrypt trabalha com bytes, então converte o texto
    hash_em_bytes = bcrypt.hashpw(senha_em_bytes, bcrypt.gensalt()) # gera o hash com um sal aleatório
    senha_hash = hash_em_bytes.decode("utf-8") # converte o hash de volta para texto, para guardar no banco
    criado_em = datetime.now().strftime("%Y-%m-%d %H:%M") # data e hora de agora, no formato ano-mês-dia hora:minuto

    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (usuario, senha_hash, criado_em) VALUES (?, ?, ?)",
                       (usuario, senha_hash, criado_em))
        # insere o usuário novo (os ? são preenchidos com segurança)
        conexao.commit()
        criado = True
    except sqlite3.IntegrityError:
        criado = False # já existe um usuário com esse nome (a coluna usuario é UNIQUE)
    conexao.close()

    return criado # devolve True se criou ou False se o nome já existia
#______________________________________________________________________________________________________________________#
#Confere se a senha digitada combina com a senha guardada (hash)

def conferir_senha(usuario, senha):
    usuario = usuario.strip().lower()
    senha_em_bytes = senha.encode("utf-8") # converte a senha digitada em bytes
    if len(senha_em_bytes) > 72:
        return False # não aceita senhas maiores que 72 bytes

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT senha_hash FROM usuarios WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone() # pega o resultado (ou None, se o usuário não existir)
    conexao.close()

    if linha is None:
        return False # usuário não existe

    senha_hash = linha[0] # o resultado vem como uma tupla, e o hash está na posição 0
    senha_certa = bcrypt.checkpw(senha_em_bytes, senha_hash.encode("utf-8")) # compara a senha com o hash
    return senha_certa
#______________________________________________________________________________________________________________________#
#Controla o bloqueio após várias senhas erradas

def esta_bloqueado(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT bloqueado_ate FROM tentativas_login WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone()
    conexao.close()

    if linha is None or linha[0] is None:
        return False # não errou a senha ou não está bloqueado

    bloqueado_ate = datetime.strptime(linha[0], "%Y-%m-%d %H:%M:%S") # transforma o texto do banco em data e hora
    return datetime.now() < bloqueado_ate


def registrar_erro(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT erros FROM tentativas_login WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone()

    if linha is None:
        erros = 1 # primeiro erro
    else:
        erros = linha[0] + 1 # soma mais um erro

    bloqueado_ate = None # começa sem bloqueio
    if erros >= MAX_TENTATIVAS:
        fim_do_bloqueio = datetime.now() + timedelta(minutes=MINUTOS_BLOQUEIO) # agora + 15 minutos
        bloqueado_ate = fim_do_bloqueio.strftime("%Y-%m-%d %H:%M:%S") # transforma em texto para guardar no banco
        erros = 0 # zera a contagem para recomeçar depois do bloqueio

    cursor.execute("INSERT OR REPLACE INTO tentativas_login (usuario, erros, bloqueado_ate) VALUES (?, ?, ?)",
                   (usuario, erros, bloqueado_ate)) # cria ou atualiza a linha desse usuário
    conexao.commit()
    conexao.close()


def limpar_erros(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM tentativas_login WHERE usuario = ?", (usuario,))
    # apaga os erros desse usuário
    conexao.commit()
    conexao.close()
#______________________________________________________________________________________________________________________#
#Gerencia os usuários: listar, remover e trocar a senha

def listar_usuarios():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT usuario, criado_em FROM usuarios ORDER BY usuario") # busca todos, em ordem alfabética
    linhas = cursor.fetchall() # pega todas as linhas do resultado
    conexao.close()
    return linhas


def remover_usuario(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (usuario,)) # apaga só esse usuário
    removido = cursor.rowcount > 0
    conexao.commit()
    conexao.close()
    return removido


def trocar_senha(usuario, senha_nova):
    usuario = usuario.strip().lower()
    senha_em_bytes = senha_nova.encode("utf-8") # o bcrypt trabalha com bytes, e converte o texto
    hash_em_bytes = bcrypt.hashpw(senha_em_bytes, bcrypt.gensalt()) # gera o hash com um 'sal' aleatório
    senha_hash = hash_em_bytes.decode("utf-8") # converte o hash de volta para texto

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE usuario = ?", (senha_hash, usuario))
    # troca só o hash desse usuário
    trocada = cursor.rowcount > 0 # rowcount diz quantas linhas foram alteradas
    conexao.commit()
    conexao.close()
    return trocada
#______________________________________________________________________________________________________________________#
#Cria, gera nova senha e exclui usuários pela página Usuários (cada função grava tudo de uma vez)

def transformar_em_hash(senha):
    hash_em_bytes = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
    return hash_em_bytes.decode("utf-8")


def criar_usuario_temporario(usuario, senha_temporaria):
    usuario = usuario.strip().lower()
    senha_hash = transformar_em_hash(senha_temporaria)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")

    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (usuario, senha_hash, criado_em) VALUES (?, ?, ?)",
                       (usuario, senha_hash, agora))
        cursor.execute("INSERT OR REPLACE INTO usuarios_trocar_senha (usuario, desde) VALUES (?, ?)",
                       (usuario, agora))
        conexao.commit()
        criado = True
    except sqlite3.IntegrityError:
        conexao.rollback()
        criado = False
    conexao.close()
    return criado


def gerar_nova_senha_temporaria(usuario, senha_temporaria):
    usuario = usuario.strip().lower()
    senha_hash = transformar_em_hash(senha_temporaria)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE usuario = ?", (senha_hash, usuario))
    if cursor.rowcount == 0:
        conexao.close()
        return False

    cursor.execute("INSERT OR REPLACE INTO usuarios_trocar_senha (usuario, desde) VALUES (?, ?)", (usuario, agora))
    cursor.execute("DELETE FROM tentativas_login WHERE usuario = ?", (usuario,))
    conexao.commit()
    conexao.close()
    return True


def excluir_usuario(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (usuario,))
    excluido = cursor.rowcount > 0
    cursor.execute("DELETE FROM tentativas_login WHERE usuario = ?", (usuario,))
    cursor.execute("DELETE FROM usuarios_trocar_senha WHERE usuario = ?", (usuario,))
    cursor.execute("DELETE FROM rotas_por_usuario WHERE usuario = ?", (usuario,))
    conexao.commit()
    conexao.close()
    return excluido


def usuario_existe(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone()
    conexao.close()
    return linha is not None
#______________________________________________________________________________________________________________________#
#Controla quem precisa trocar a senha temporária

def precisa_trocar_senha(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT 1 FROM usuarios_trocar_senha WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone()
    conexao.close()
    return linha is not None


def liberar_troca_de_senha(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios_trocar_senha WHERE usuario = ?", (usuario,))
    conexao.commit()
    conexao.close()


def listar_aguardando_troca():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT usuario FROM usuarios_trocar_senha")
    linhas = cursor.fetchall()
    conexao.close()

    nomes = []
    for linha in linhas:
        nomes.append(linha[0])
    return nomes
#______________________________________________________________________________________________________________________#
#Salva e lê as configurações do sistema (como o caminho da planilha)

def salvar_configuracao(chave, valor):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
                   (chave, valor)) # cria ou atualiza a configuração
    conexao.commit()
    conexao.close()


def ler_configuracao(chave, valor_padrao=""):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
    linha = cursor.fetchone()
    conexao.close()

    if linha is None:
        return valor_padrao # a configuração ainda não foi salva, então devolve o valor padrão
    return linha[0]
#______________________________________________________________________________________________________________________#
#Registra as rotas geradas e calcula o uso da cota do mês

def gravar_uso_da_cota(cursor, usuario, qtd_entregas, elementos, data_hora):
    """
    Recebe o cursor aberto, o usuário, a quantidade de entregas, os elementos usados e a data e hora.
    Grava o uso da cota no histórico, sem fazer o commit (quem chama faz).
    """
    cursor.execute("INSERT INTO historico (data_hora, usuario, qtd_entregas, elementos) VALUES (?, ?, ?, ?)",
                   (data_hora, usuario.strip().lower(), qtd_entregas, elementos))


def somar_rota_do_usuario(cursor, usuario):
    """
    Recebe o cursor aberto e o usuário.
    Soma 1 rota gerada para o usuário, sem fazer o commit (quem chama faz).
    """
    usuario = usuario.strip().lower()
    cursor.execute("SELECT rotas FROM rotas_por_usuario WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone()
    if linha is None:
        cursor.execute("INSERT INTO rotas_por_usuario (usuario, rotas) VALUES (?, 1)", (usuario,))
    else:
        cursor.execute("UPDATE rotas_por_usuario SET rotas = ? WHERE usuario = ?", (linha[0] + 1, usuario))


def total_rotas_do_usuario(usuario):
    usuario = usuario.strip().lower()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT rotas FROM rotas_por_usuario WHERE usuario = ?", (usuario,))
    linha = cursor.fetchone()
    conexao.close()

    if linha is None:
        return 0
    return linha[0]


def elementos_usados_no_mes():
    mes_atual = datetime.now().strftime("%Y-%m") # exemplo: "2026-11"
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT SUM(elementos) FROM historico WHERE data_hora LIKE ?",
                   (mes_atual + "%",)) # soma só as rotas que começam com o mês atual
    linha = cursor.fetchone()
    conexao.close()

    total = linha[0]
    if total is None:
        total = 0 # nenhuma rota gerada neste mês
    return total


def listar_historico(limite=50):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT data_hora, usuario, qtd_entregas, elementos FROM historico ORDER BY data_hora DESC LIMIT ?",
                   (limite,)) # as mais recentes primeiro
    linhas = cursor.fetchall()
    conexao.close()
    return linhas
#______________________________________________________________________________________________________________________#
#Registra e lista as atividades dos usuários (log)

def gravar_atividade(cursor, data_hora, usuario, acao):
    """
    Recebe o cursor aberto, a data e hora, o usuário e a ação.
    Grava a ação no log, sem fazer o commit (quem chama faz).
    """
    cursor.execute("INSERT INTO log_atividades (data_hora, usuario, acao) VALUES (?, ?, ?)",
                   (data_hora, usuario, acao))


def registrar_atividade(usuario, acao):
    conferir_usuario(usuario)
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conexao = conectar()
    try:
        cursor = conexao.cursor()
        gravar_atividade(cursor, data_hora, usuario, acao)
        conexao.commit()
    finally:
        conexao.close()


def listar_atividades(limite=100):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT data_hora, usuario, acao FROM log_atividades ORDER BY data_hora DESC LIMIT ?",
                   (limite,)) # as mais recentes primeiro
    linhas = cursor.fetchall()
    conexao.close()
    return linhas
#______________________________________________________________________________________________________________________#
#Apaga os registros do log e do histórico mais antigos que o limite de dias

def limpar_dados_antigos():
    data_limite = datetime.now() - timedelta(days=DIAS_GUARDAR_DADOS) # hoje - 60 dias
    texto_limite = data_limite.strftime("%Y-%m-%d") # só a data, para valer para as duas tabelas
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM log_atividades WHERE data_hora < ?", (texto_limite,))
    cursor.execute("DELETE FROM historico WHERE data_hora < ?", (texto_limite,))
    cursor.execute("DELETE FROM historico_entregas WHERE data_hora < ?", (texto_limite,))
    conexao.commit()
    conexao.close()
#______________________________________________________________________________________________________________________#
#Salva e lista os pedidos prontos para entrega

def tem_transportadora(valor):
    """
    Recebe o número da transportadora da venda (ou None).
    Retorna True se for um número válido / False, se a venda não tiver transportadora.
    """
    try:
        conferir_transportadora_id(valor)
    except ValueError:
        return False
    return True


def conferir_lista_pedidos(pedidos, transportadoras_das_vendas):
    """
    Recebe a lista de pedidos (dicionários com codigo, nf, volume e entregar_no) e o dicionário com o número da
    transportadora de cada venda (código do pedido -> número / None).
    Retorna a lista conferida, pronta para gravar. NF, volume e entregar_no vazios ficam como None (pedidos antigos).
    Lança ValueError se algum dado for inválido ou se algum pedido for para a transportadora sem a venda ter uma.
    """
    conferidos = []
    codigos_usados = []
    sem_transportadora = []
    for pedido in pedidos:
        codigo = converter_inteiro_positivo(pedido.get("codigo"), TAMANHO_MAXIMO_CODIGO, "Código de pedido inválido.")
        if codigo in codigos_usados:
            raise ValueError(f"O pedido {codigo} aparece mais de uma vez na lista.")
        nf = conferir_nf_opcional(pedido.get("nf"))
        volume = conferir_volume_opcional(pedido.get("volume"))
        entregar_no = pedido.get("entregar_no")
        if entregar_no is not None:
            entregar_no = conferir_entregar_no(entregar_no)
        if entregar_no == "transportadora" and not tem_transportadora(transportadoras_das_vendas.get(codigo)):
            sem_transportadora.append(str(codigo))

        codigos_usados.append(codigo)
        conferidos.append({"codigo": codigo, "nf": nf, "volume": volume, "entregar_no": entregar_no})

    if len(sem_transportadora) == 1:
        raise ValueError(f"O pedido {sem_transportadora[0]} está marcado para entregar na transportadora, "
                         f"mas a venda não tem transportadora no GestãoClick.")
    if len(sem_transportadora) > 1:
        raise ValueError(f"Os pedidos {', '.join(sem_transportadora)} estão marcados para entregar na transportadora, "
                         f"mas as vendas não têm transportadora no GestãoClick.")
    return conferidos


def salvar_lista_pedidos(pedidos, transportadoras_das_vendas=None, lista_base=None):
    """
    Recebe a lista de pedidos na ordem de prioridade (dicionários com codigo, nf, volume e entregar_no), o
    dicionário com o número da transportadora de cada venda e a lista_base (códigos, na ordem, que a página leu do
    banco antes das alterações; None = sem conferência, usado só pelos testes antigos).
    Troca a lista gravada pela nova num único commit (BEGIN IMMEDIATE), mantendo a data em que cada pedido foi
    adicionado.
    Lança ValueError (sem gravar nada) se algum dado for inválido ou se a lista do banco não for mais a lista_base.
    """
    if transportadoras_das_vendas is None:
        transportadoras_das_vendas = {}
    conferidos = conferir_lista_pedidos(pedidos, transportadoras_das_vendas)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")

    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT codigo, adicionado_em FROM pedidos ORDER BY prioridade")
        codigos_no_banco = []
        datas_antigas = {}
        for linha in cursor.fetchall():
            codigos_no_banco.append(linha[0])
            datas_antigas[linha[0]] = linha[1] # guarda a data em que cada pedido foi adicionado
        if lista_base is not None and codigos_no_banco != list(lista_base):
            raise ValueError(MENSAGEM_LISTA_ALTERADA)

        cursor.execute("DELETE FROM pedidos") # apaga a lista antiga para gravar a nova no lugar
        prioridade = 1
        for pedido in conferidos:
            adicionado_em = datas_antigas.get(pedido["codigo"], agora) # mantém a data antiga ou usa a de agora
            cursor.execute("""INSERT INTO pedidos (codigo, prioridade, adicionado_em, nf, volume, entregar_no)
                              VALUES (?, ?, ?, ?, ?, ?)""",
                           (pedido["codigo"], prioridade, adicionado_em, pedido["nf"], pedido["volume"],
                            pedido["entregar_no"]))
            prioridade += 1
        conexao.commit()
    except Exception as erro:
        conexao.rollback()
        if banco_ocupado(erro):
            raise ValueError(MENSAGEM_BANCO_OCUPADO) from erro
        raise
    finally:
        conexao.close()


def listar_codigos_pedidos():
    """
    Retorna os códigos dos pedidos gravados, na ordem de prioridade.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT codigo FROM pedidos ORDER BY prioridade")
    linhas = cursor.fetchall()
    conexao.close()

    codigos = []
    for linha in linhas:
        codigos.append(linha[0])
    return codigos


def listar_pedidos_completos():
    """
    Retorna a lista de pedidos na ordem de prioridade, cada um como dicionário com codigo, prioridade,
    adicionado_em, nf, volume e entregar_no (os três últimos podem ser None em pedidos antigos).
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT codigo, prioridade, adicionado_em, nf, volume, entregar_no FROM pedidos ORDER BY prioridade")
    linhas = cursor.fetchall()
    conexao.close()

    pedidos = []
    for linha in linhas:
        pedidos.append({"codigo": linha[0], "prioridade": linha[1], "adicionado_em": linha[2],
                        "nf": linha[3], "volume": linha[4], "entregar_no": linha[5]})
    return pedidos


def pedidos_sem_nf_ou_volume():
    """
    Retorna os códigos dos pedidos da lista que ainda estão sem NF ou sem volume, na ordem de prioridade.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT codigo FROM pedidos WHERE nf IS NULL OR volume IS NULL ORDER BY prioridade")
    linhas = cursor.fetchall()
    conexao.close()

    codigos = []
    for linha in linhas:
        codigos.append(linha[0])
    return codigos


def listar_pedidos():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT codigo, prioridade, adicionado_em FROM pedidos ORDER BY prioridade")
    linhas = cursor.fetchall()
    conexao.close()
    return linhas
#______________________________________________________________________________________________________________________#
#Confere as paradas extras antes de gravar e remonta a ordem completa da rota

def conferir_usuario(usuario):
    """
    Recebe o nome do usuário que fez a ação.
    Lança ValueError se estiver vazio, para nenhuma ação ficar sem nome no histórico.
    """
    if usuario is None or str(usuario).strip() == "":
        raise ValueError("O usuário é obrigatório para registrar a ação.")


def preparar_itens_da_rota(itens):
    """
    Recebe a lista de itens da rota, na ordem (dicionários de pedido ou de parada extra).
    Retorna a lista conferida, com a posição de cada parada extra na ordem completa e os nomes sem espaços sobrando.
    Lança ValueError se algum pedido, parada extra, NF, volume ou destino for inválido, ou se algo se repetir.
    """
    preparados = []
    codigos_usados = []
    clientes_usados = []
    posicao = 1
    for item in itens:
        destino_tipo, transportadora_id = conferir_destino(item.get("destino_tipo"), item.get("transportadora_id"))
        preparado = {"tipo": item.get("tipo"),
                     "destino_tipo": destino_tipo,
                     "transportadora_id": transportadora_id,
                     "destino_nome": limpar_nome(item.get("destino_nome")),
                     "cliente_nome": limpar_nome(item.get("cliente_nome"))}

        if item.get("tipo") == "pedido":
            codigo = converter_inteiro_positivo(item.get("codigo"), TAMANHO_MAXIMO_CODIGO, "Código de pedido inválido.")
            if codigo in codigos_usados:
                raise ValueError(f"O pedido {codigo} aparece mais de uma vez na rota.")
            codigos_usados.append(codigo)
            preparado["codigo"] = codigo
            preparado["motivo"] = ""
            preparado["nf"] = conferir_nf(item.get("nf"))
            preparado["volume"] = conferir_volume(item.get("volume"))
        elif item.get("tipo") == "extra":
            cliente_id, motivo = conferir_cliente_e_motivo(item.get("cliente_id"), item.get("motivo"), clientes_usados)
            clientes_usados.append(cliente_id)
            preparado["posicao"] = posicao
            preparado["cliente_id"] = cliente_id
            preparado["motivo"] = motivo
            preparado["nf"] = conferir_nf_opcional(item.get("nf"))
            preparado["volume"] = conferir_volume_opcional(item.get("volume"))
        else:
            raise ValueError("Item da rota inválido.")

        preparados.append(preparado)
        posicao += 1
    return preparados


def agrupar_em_paradas(itens):
    """
    Recebe a lista de itens na ordem da rota.
    Retorna a lista de paradas: itens seguidos que vão para a mesma transportadora ficam numa parada só.
    Cada parada tem destino_tipo, transportadora_id, destino_nome e a lista de itens.
    """
    paradas = []
    for item in itens:
        ultima = None
        if len(paradas) > 0:
            ultima = paradas[-1]

        mesma_transportadora = (item["destino_tipo"] == "transportadora" and ultima is not None
                                and ultima["destino_tipo"] == "transportadora"
                                and ultima["transportadora_id"] == item["transportadora_id"])
        if mesma_transportadora:
            ultima["itens"].append(item)
        else:
            paradas.append({"destino_tipo": item["destino_tipo"],
                            "transportadora_id": item["transportadora_id"],
                            "destino_nome": item["destino_nome"],
                            "itens": [item]})
    return paradas


def conferir_cliente_e_motivo(cliente_id, motivo, clientes_usados):
    """
    Recebe o número do cliente, o motivo e a lista de clientes que já estão na rota.
    Retorna o número do cliente e o motivo conferidos, com o motivo sem espaços sobrando.
    Lança ValueError se o cliente for inválido ou repetido, ou se o motivo estiver fora da lista.
    """
    try:
        cliente_id = int(cliente_id)
    except (TypeError, ValueError):
        raise ValueError("Cliente inválido para a parada extra.")
    motivo = " ".join(str(motivo).split())

    if cliente_id <= 0:
        raise ValueError("Cliente inválido para a parada extra.")
    if cliente_id in clientes_usados:
        raise ValueError(f"O cliente {cliente_id} aparece mais de uma vez nas paradas extras.")
    if motivo not in MOTIVOS_PARADA_EXTRA:
        raise ValueError("Motivo da parada extra fora da lista permitida.")
    if len(motivo) > TAMANHO_MAXIMO_MOTIVO:
        raise ValueError(f"O motivo precisa ter no máximo {TAMANHO_MAXIMO_MOTIVO} caracteres.")
    return cliente_id, motivo


def conferir_paradas_extras_antes_da_rota(paradas_extras):
    """
    Recebe a lista de paradas extras da página (dicionários com cliente_id, motivo e, se houver, nf, volume e
    transportadora_id).
    Retorna uma cópia da lista com o cliente, o motivo, a NF, o volume e a transportadora conferidos.
    Lança ValueError se algum motivo estiver fora da lista, se algum cliente se repetir ou se a NF, o volume ou a
    transportadora forem inválidos.
    """
    conferidas = []
    clientes_usados = []
    for parada in paradas_extras:
        cliente_id, motivo = conferir_cliente_e_motivo(parada.get("cliente_id"), parada.get("motivo"), clientes_usados)
        clientes_usados.append(cliente_id)
        transportadora_id = parada.get("transportadora_id")
        if transportadora_id is not None:
            transportadora_id = conferir_transportadora_id(transportadora_id)

        conferida = dict(parada)
        conferida["cliente_id"] = cliente_id
        conferida["motivo"] = motivo
        conferida["nf"] = conferir_nf_opcional(parada.get("nf"))
        conferida["volume"] = conferir_volume_opcional(parada.get("volume"))
        conferida["transportadora_id"] = transportadora_id
        conferidas.append(conferida)
    return conferidas


def tempo_e_valido(tempo):
    """
    Recebe um tempo em segundos.
    Retorna True se for um número finito e não negativo / False, se for infinito, vazio ou inválido.
    """
    if isinstance(tempo, bool) or not isinstance(tempo, (int, float)):
        return False
    return math.isfinite(tempo) and tempo >= 0


def montar_ordem_completa(pedidos, paradas_extras):
    """
    Recebe a lista de pedidos na ordem da rota e a lista de (posição, número do cliente, motivo).
    Retorna a ordem completa, com um dicionário por parada (pedido ou parada extra).
    """
    extras_por_posicao = {}
    for posicao, cliente_id, motivo in paradas_extras:
        extras_por_posicao[posicao] = (cliente_id, motivo)

    ordem = []
    colocadas = []
    proximo_pedido = 0
    total = len(pedidos) + len(paradas_extras)
    for posicao in range(1, total + 1):
        if posicao in extras_por_posicao:
            cliente_id, motivo = extras_por_posicao[posicao]
            ordem.append({"tipo": "extra", "posicao": posicao, "cliente_id": cliente_id, "motivo": motivo})
            colocadas.append(posicao)
        elif proximo_pedido < len(pedidos):
            ordem.append({"tipo": "pedido", "codigo": pedidos[proximo_pedido]})
            proximo_pedido += 1

    for posicao, cliente_id, motivo in paradas_extras:
        if posicao not in colocadas:
            ordem.append({"tipo": "extra", "posicao": posicao, "cliente_id": cliente_id, "motivo": motivo})
    while proximo_pedido < len(pedidos):
        ordem.append({"tipo": "pedido", "codigo": pedidos[proximo_pedido]})
        proximo_pedido += 1

    return ordem


def somar_cidade(cursor, cidade):
    """
    Recebe o cursor aberto e o nome da cidade.
    Soma 1 entrega na cidade, sem fazer o commit (quem chama faz).
    """
    cidade = " ".join(str(cidade).split()).upper()
    if cidade == "":
        cidade = "NÃO INFORMADA"
    cursor.execute("SELECT entregas FROM cidades_atendidas WHERE cidade = ?", (cidade,))
    linha = cursor.fetchone()
    if linha is None:
        cursor.execute("INSERT INTO cidades_atendidas (cidade, entregas) VALUES (?, 1)", (cidade,))
    else:
        cursor.execute("UPDATE cidades_atendidas SET entregas = ? WHERE cidade = ?", (linha[0] + 1, cidade))
#______________________________________________________________________________________________________________________#
#Guarda os pedidos da última rota e confirma quais foram entregues

def gravar_rota_pendente(cursor, itens, usuario, gerada_em, data_hora_log):
    """
    Recebe o cursor aberto, os itens da rota já conferidos (preparar_itens_da_rota), o usuário e as datas.
    Troca a rota pendente pela nova, com NF, volume e destino de cada item, e registra no log cada parada extra,
    sem fazer o commit (quem chama faz).
    """
    cursor.execute("DELETE FROM rota_pendente")
    cursor.execute("DELETE FROM rota_pendente_extras")
    for item in itens:
        if item["tipo"] == "pedido":
            cursor.execute("""INSERT INTO rota_pendente (codigo, gerada_em, nf, volume, destino_tipo, destino_nome,
                              cliente_nome, transportadora_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                           (item["codigo"], gerada_em, item["nf"], item["volume"], item["destino_tipo"],
                            item["destino_nome"], item["cliente_nome"], item["transportadora_id"]))
        else:
            cursor.execute("""INSERT INTO rota_pendente_extras (posicao, cliente_id, motivo, gerada_em, nf, volume,
                              transportadora_id, destino_tipo, destino_nome, cliente_nome)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (item["posicao"], item["cliente_id"], item["motivo"], gerada_em, item["nf"], item["volume"],
                            item["transportadora_id"], item["destino_tipo"], item["destino_nome"], item["cliente_nome"]))
            gravar_atividade(cursor, data_hora_log, usuario,
                             f"Parada extra adicionada à rota: cliente {item['cliente_id']} ({item['motivo']})")


def listar_rota_pendente():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT codigo FROM rota_pendente")
    linhas = cursor.fetchall()
    conexao.close()

    codigos = []
    for linha in linhas:
        codigos.append(linha[0]) # transforma [(1032,), (1040,)] em [1032, 1040]
    return codigos


def listar_extras_pendentes():
    """
    Retorna a lista de (posição, número do cliente, motivo) das paradas extras da rota pendente, em ordem.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT posicao, cliente_id, motivo FROM rota_pendente_extras ORDER BY posicao")
    linhas = cursor.fetchall()
    conexao.close()

    extras = []
    for linha in linhas:
        extras.append((linha[0], linha[1], linha[2]))
    return extras


def montar_item(tipo, nf, volume, transportadora_id, destino_tipo, destino_nome, cliente_nome):
    """
    Recebe os dados de um item como estão no banco (rotas antigas podem ter tudo vazio).
    Retorna o dicionário do item. Sem destino gravado, o destino é o cliente.
    """
    if destino_tipo not in DESTINOS_VALIDOS:
        destino_tipo = "cliente"
    if destino_tipo == "cliente":
        transportadora_id = None
    cliente_nome = limpar_nome(cliente_nome)
    destino_nome = limpar_nome(destino_nome)
    if destino_nome == "" and destino_tipo == "cliente":
        destino_nome = cliente_nome

    return {"tipo": tipo, "nf": nf, "volume": volume, "transportadora_id": transportadora_id,
            "destino_tipo": destino_tipo, "destino_nome": destino_nome, "cliente_nome": cliente_nome}


def item_de_pedido(codigo, linha):
    """
    Recebe o código do pedido e a linha (codigo, nf, volume, transportadora_id, destino_tipo, destino_nome,
    cliente_nome) / None, se o pedido não tiver os dados gravados.
    Retorna o dicionário do item do pedido.
    """
    if linha is None:
        linha = (codigo, None, None, None, None, None, None)
    item = montar_item("pedido", linha[1], linha[2], linha[3], linha[4], linha[5], linha[6])
    item["codigo"] = codigo
    item["cliente_id"] = None
    item["motivo"] = ""
    return item


def item_de_extra(linha):
    """
    Recebe a linha (posicao, cliente_id, motivo, nf, volume, transportadora_id, destino_tipo, destino_nome,
    cliente_nome) de uma parada extra.
    Retorna o dicionário do item da parada extra.
    """
    item = montar_item("extra", linha[3], linha[4], linha[5], linha[6], linha[7], linha[8])
    item["posicao"] = linha[0]
    item["cliente_id"] = linha[1]
    item["motivo"] = linha[2]
    return item


def montar_itens_detalhados(ordem, linhas_pedidos, linhas_extras):
    """
    Recebe a ordem completa (montar_ordem_completa), as linhas dos pedidos e as linhas das paradas extras.
    Retorna a lista de itens na ordem, cada um com NF, volume e destino.
    """
    detalhes_pedidos = {}
    for linha in linhas_pedidos:
        detalhes_pedidos[linha[0]] = linha
    detalhes_extras = {}
    for linha in linhas_extras:
        detalhes_extras[linha[0]] = linha

    itens = []
    for parada in ordem:
        if parada["tipo"] == "pedido":
            itens.append(item_de_pedido(parada["codigo"], detalhes_pedidos.get(parada["codigo"])))
        elif parada["posicao"] in detalhes_extras:
            itens.append(item_de_extra(detalhes_extras[parada["posicao"]]))
    return itens


def listar_itens_pendentes():
    """
    Retorna os itens da rota pendente (pedidos e paradas extras) na ordem da rota, com NF, volume e destino.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""SELECT codigo, nf, volume, transportadora_id, destino_tipo, destino_nome, cliente_nome
                      FROM rota_pendente""")
    linhas_pedidos = cursor.fetchall()
    cursor.execute("""SELECT posicao, cliente_id, motivo, nf, volume, transportadora_id, destino_tipo, destino_nome,
                      cliente_nome FROM rota_pendente_extras ORDER BY posicao""")
    linhas_extras = cursor.fetchall()
    cursor.execute("SELECT pedidos FROM ultima_rota WHERE id = 1")
    linha_ultima = cursor.fetchone()
    conexao.close()

    pendentes = []
    for linha in linhas_pedidos:
        pendentes.append(linha[0])

    codigos = []
    if linha_ultima is not None and linha_ultima[0] != "":
        for codigo_texto in linha_ultima[0].split(","):
            codigo = int(codigo_texto)
            if codigo in pendentes and codigo not in codigos:
                codigos.append(codigo)
    for codigo in pendentes:
        if codigo not in codigos:
            codigos.append(codigo)

    extras = []
    for linha in linhas_extras:
        extras.append((linha[0], linha[1], linha[2]))

    ordem = montar_ordem_completa(codigos, extras)
    return montar_itens_detalhados(ordem, linhas_pedidos, linhas_extras)


def existe_rota_pendente(cursor):
    """
    Recebe o cursor aberto.
    Retorna True se houver pedido ou parada extra esperando confirmação / False, se não houver.
    """
    cursor.execute("SELECT 1 FROM rota_pendente UNION ALL SELECT 1 FROM rota_pendente_extras LIMIT 1")
    return cursor.fetchone() is not None


def ultima_rota_valendo(hoje=None):
    """
    Recebe a data de hoje (os testes passam outra data) / None, para usar a data local do computador.
    Retorna a última rota (ler_ultima_rota) só se ela ainda está valendo: há rota pendente, gerada hoje, e ela é
    a mesma da última rota / None, se foi confirmada, se é de outro dia ou se não há rota.
    """
    if hoje is None:
        hoje = datetime.now().date()
    pendente = data_rota_pendente()
    if pendente is None:
        return None
    if datetime.strptime(pendente, "%Y-%m-%d %H:%M").date() != hoje:
        return None
    salva = ler_ultima_rota()
    if salva is None or salva["gerada_em"][:16] != pendente:
        return None
    return salva


def data_rota_pendente():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""SELECT MIN(gerada_em) FROM (SELECT gerada_em FROM rota_pendente
                      UNION ALL SELECT gerada_em FROM rota_pendente_extras)""")
    linha = cursor.fetchone()
    conexao.close()
    return linha[0]


def gravar_entrega_no_historico(cursor, data_hora, usuario, item):
    """
    Recebe o cursor aberto, a data e hora, o usuário e o item entregue (item_de_pedido ou item_de_extra).
    Grava a entrega em historico_entregas, sem fazer o commit (quem chama faz).
    """
    if item["tipo"] == "pedido":
        pedido_id = item["codigo"]
        eh_extra = 0
        motivo = None
    else:
        pedido_id = None
        eh_extra = 1
        motivo = item["motivo"]

    cursor.execute("""INSERT INTO historico_entregas (data_hora, usuario, pedido_id, eh_extra, motivo, nf, volume,
                      destino_tipo, destino_nome, cliente_nome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (data_hora, usuario, pedido_id, eh_extra, motivo, item["nf"], item["volume"], item["destino_tipo"],
                    item["destino_nome"], item["cliente_nome"]))


def confirmar_entregas(entregas_confirmadas, usuario, extras_entregues=None):
    """
    Recebe uma lista de (código do pedido, cidade do cliente, número do cliente) dos pedidos entregues,
    o usuário que confirmou e uma lista de (posição, cidade do cliente) das paradas extras entregues.
    Tira os pedidos entregues da lista, soma nas cidades e nos clientes atendidos, grava cada item entregue em
    historico_entregas (com os dados guardados na rota pendente), registra no log as paradas extras não entregues
    e o total confirmado, e encerra a rota pendente, tudo num único commit.
    Pedidos que não estão na rota pendente são ignorados.
    Retorna (quantidade marcada, total de itens da rota).
    """
    conferir_usuario(usuario)
    if extras_entregues is None:
        extras_entregues = []
    cidades_extras = {}
    for posicao, cidade in extras_entregues:
        cidades_extras[int(posicao)] = cidade
    agora_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute("""SELECT codigo, nf, volume, transportadora_id, destino_tipo, destino_nome, cliente_nome
                          FROM rota_pendente""")
        itens_pendentes = {}
        for linha in cursor.fetchall():
            itens_pendentes[linha[0]] = item_de_pedido(linha[0], linha)
        total_pedidos = len(itens_pendentes)

        pedidos_confirmados = 0
        for codigo, cidade, cliente_id in entregas_confirmadas:
            if codigo not in itens_pendentes:
                continue
            item = itens_pendentes.pop(codigo)
            cursor.execute("DELETE FROM pedidos WHERE codigo = ?", (codigo,))
            somar_cidade(cursor, cidade)
            if cliente_id is not None:
                cursor.execute("INSERT OR IGNORE INTO clientes_atendidos (cliente_id) VALUES (?)", (int(cliente_id),))
            gravar_entrega_no_historico(cursor, agora_log, usuario, item)
            pedidos_confirmados += 1

        extras_confirmadas = 0
        cursor.execute("""SELECT posicao, cliente_id, motivo, nf, volume, transportadora_id, destino_tipo, destino_nome,
                          cliente_nome FROM rota_pendente_extras ORDER BY posicao""")
        linhas_extras = cursor.fetchall()
        for linha in linhas_extras:
            posicao, cliente_id, motivo = linha[0], linha[1], linha[2]
            if posicao in cidades_extras:
                somar_cidade(cursor, cidades_extras[posicao])
                cursor.execute("INSERT OR IGNORE INTO clientes_atendidos (cliente_id) VALUES (?)", (cliente_id,))
                gravar_entrega_no_historico(cursor, agora_log, usuario, item_de_extra(linha))
                extras_confirmadas += 1
            else:
                gravar_atividade(cursor, agora_log, usuario, f"Parada extra não entregue: cliente {cliente_id} ({motivo})")

        total_marcadas = pedidos_confirmados + extras_confirmadas
        total_paradas = total_pedidos + len(linhas_extras)
        gravar_atividade(cursor, agora_log, usuario, f"Confirmou {total_marcadas} de {total_paradas} entregas")

        cursor.execute("DELETE FROM rota_pendente_extras")
        cursor.execute("DELETE FROM rota_pendente")
        conexao.commit()
    finally:
        conexao.close()
    return total_marcadas, total_paradas


def totais_desde_o_inicio():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT SUM(entregas) FROM cidades_atendidas")
    entregas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cidades_atendidas WHERE cidade != 'NÃO INFORMADA'")
    cidades = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM clientes_atendidos")
    clientes = cursor.fetchone()[0]
    conexao.close()

    if entregas is None:
        entregas = 0
    return entregas, cidades, clientes
#______________________________________________________________________________________________________________________#
#Guarda e lê a última rota gerada (só códigos, horários e motivos, sem endereços)

def gravar_ultima_rota(cursor, gerada_em, usuario, hora_saida, itens, tempo_de_entrega, tempo_disponivel,
                       quantidade_pedida, problemas):
    """
    Recebe o cursor aberto e os dados da rota, com os itens já conferidos (preparar_itens_da_rota).
    Troca a última rota pela nova, com NF, volume e destino de cada item, sem fazer o commit (quem chama faz).
    """
    codigos_texto = []
    for item in itens:
        if item["tipo"] == "pedido":
            codigos_texto.append(str(item["codigo"]))

    cursor.execute("""INSERT OR REPLACE INTO ultima_rota (id, gerada_em, usuario, hora_saida, pedidos,
                      tempo_de_entrega, tempo_disponivel, quantidade_pedida, problemas)
                      VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (gerada_em, usuario, hora_saida, ",".join(codigos_texto), int(tempo_de_entrega),
                    int(tempo_disponivel), int(quantidade_pedida), "\n".join(problemas)))
    cursor.execute("DELETE FROM ultima_rota_pedidos")
    cursor.execute("DELETE FROM ultima_rota_extras")
    for item in itens:
        if item["tipo"] == "pedido":
            cursor.execute("""INSERT INTO ultima_rota_pedidos (codigo, nf, volume, transportadora_id, destino_tipo,
                              destino_nome, cliente_nome) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (item["codigo"], item["nf"], item["volume"], item["transportadora_id"], item["destino_tipo"],
                            item["destino_nome"], item["cliente_nome"]))
        else:
            cursor.execute("""INSERT INTO ultima_rota_extras (posicao, cliente_id, motivo, nf, volume, transportadora_id,
                              destino_tipo, destino_nome, cliente_nome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (item["posicao"], item["cliente_id"], item["motivo"], item["nf"], item["volume"],
                            item["transportadora_id"], item["destino_tipo"], item["destino_nome"], item["cliente_nome"]))


def ler_ultima_rota():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""SELECT gerada_em, usuario, hora_saida, pedidos, tempo_de_entrega, tempo_disponivel,
                      quantidade_pedida, problemas FROM ultima_rota WHERE id = 1""")
    linha = cursor.fetchone()
    cursor.execute("""SELECT posicao, cliente_id, motivo, nf, volume, transportadora_id, destino_tipo, destino_nome,
                      cliente_nome FROM ultima_rota_extras ORDER BY posicao""")
    linhas_extras = cursor.fetchall()
    cursor.execute("""SELECT codigo, nf, volume, transportadora_id, destino_tipo, destino_nome, cliente_nome
                      FROM ultima_rota_pedidos""")
    linhas_pedidos = cursor.fetchall()
    conexao.close()

    if linha is None:
        return None

    pedidos = []
    if linha[3] != "":
        for codigo in linha[3].split(","):
            pedidos.append(int(codigo))

    problemas = []
    if linha[7] != "":
        problemas = linha[7].split("\n")

    paradas_extras = []
    for extra in linhas_extras:
        paradas_extras.append((extra[0], extra[1], extra[2]))
    ordem = montar_ordem_completa(pedidos, paradas_extras)

    return {"gerada_em": linha[0],
            "usuario": linha[1],
            "hora_saida": linha[2],
            "pedidos": pedidos,
            "tempo_de_entrega": linha[4],
            "tempo_disponivel": linha[5],
            "quantidade_pedida": linha[6],
            "problemas": problemas,
            "paradas_extras": paradas_extras,
            "ordem": ordem,
            "itens": montar_itens_detalhados(ordem, linhas_pedidos, linhas_extras)}
#______________________________________________________________________________________________________________________#
#Grava a rota gerada inteira num commit só

def salvar_rota_gerada(usuario, hora_saida, itens_na_rota, tempo_de_entrega, tempo_disponivel,
                       quantidade_pedida, problemas, elementos_usados):
    """
    Recebe o usuário e os dados da rota gerada, com os itens (pedidos e paradas extras) na ordem da rota.
    Grava tudo num único commit: histórico, rotas por usuário, rota pendente, log e última rota.
    A transação começa com BEGIN IMMEDIATE (ninguém mais grava ao mesmo tempo) e confere de novo se já existe rota
    pendente antes de gravar.
    Se o tempo for inválido, grava só o uso da cota e o log, sem rota pendente e sem trocar a última rota.
    Se a rota for recusada (outra pessoa já gerou uma, ou o banco está ocupado), a rota não é gravada, mas o uso da
    cota do Google Maps (que já foi consultado) é gravado numa transação separada, uma vez só.
    Retorna a data e hora em que a rota foi gravada / None, se o tempo for inválido.
    Lança ValueError se o usuário estiver vazio, se algum item (NF, volume, destino, cliente) for inválido (sem gravar
    nada), se outra pessoa já tiver gerado uma rota que ainda não foi confirmada ou se o banco estiver ocupado.
    """
    conferir_usuario(usuario)
    itens = preparar_itens_da_rota(itens_na_rota)
    total_de_paradas = len(agrupar_em_paradas(itens))
    rota_valida = tempo_e_valido(tempo_de_entrega) and tempo_e_valido(tempo_disponivel)
    agora = datetime.now()
    gerada_em = agora.strftime("%Y-%m-%d %H:%M:%S")
    data_hora_curta = agora.strftime("%Y-%m-%d %H:%M")
    recusa = None
    causa = None
    acao_recusa = ""

    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        if existe_rota_pendente(cursor):
            raise ValueError(MENSAGEM_ROTA_JA_GERADA)
        if rota_valida:
            if elementos_usados > 0:
                gravar_uso_da_cota(cursor, usuario, total_de_paradas, elementos_usados, data_hora_curta)
                somar_rota_do_usuario(cursor, usuario)
            if total_de_paradas > 0:
                gravar_rota_pendente(cursor, itens, usuario, data_hora_curta, gerada_em)
            gravar_atividade(cursor, gerada_em, usuario, "Gerou uma rota")
            gravar_ultima_rota(cursor, gerada_em, usuario, hora_saida, itens, tempo_de_entrega,
                               tempo_disponivel, quantidade_pedida, problemas)
        else:
            if elementos_usados > 0:
                gravar_uso_da_cota(cursor, usuario, 0, elementos_usados, data_hora_curta)
            gravar_atividade(cursor, gerada_em, usuario, "Rota não gerada: não foi possível calcular o tempo")
        conexao.commit()
    except Exception as erro:
        conexao.rollback()
        if banco_ocupado(erro):
            recusa = ValueError(MENSAGEM_BANCO_OCUPADO)
            causa = erro
            acao_recusa = "Rota recusada (banco ocupado); uso da cota registrado"
        elif isinstance(erro, ValueError) and str(erro) == MENSAGEM_ROTA_JA_GERADA:
            recusa = erro
            acao_recusa = "Rota recusada (outra rota já gerada); uso da cota registrado"
        else:
            raise
    finally:
        conexao.close()

    if recusa is not None:
        if elementos_usados > 0:
            entregas_da_cota = 0
            if rota_valida:
                entregas_da_cota = total_de_paradas
            try:
                registrar_cota_da_rota_recusada(usuario, entregas_da_cota, elementos_usados, data_hora_curta,
                                                gerada_em, acao_recusa)
            except Exception as erro_cota:
                if not banco_ocupado(erro_cota):
                    raise
        raise recusa from causa

    if rota_valida:
        return gerada_em
    return None


def registrar_cota_da_rota_recusada(usuario, qtd_entregas, elementos_usados, data_hora_cota, data_hora_log, acao):
    """
    Recebe o usuário, a quantidade de entregas, os elementos usados no Google Maps, as datas e o texto da atividade.
    Grava só o uso da cota e a atividade numa transação nova (BEGIN IMMEDIATE), com o próprio commit.
    Lança o erro do banco, sem esconder, se não conseguir gravar.
    """
    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        gravar_uso_da_cota(cursor, usuario, qtd_entregas, elementos_usados, data_hora_cota)
        gravar_atividade(cursor, data_hora_log, usuario, acao)
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()
#______________________________________________________________________________________________________________________#
#Confere a NF, o volume e o local de entrega antes de gravar

def converter_inteiro_positivo(valor, maximo_digitos, mensagem):
    """
    Recebe o valor (número inteiro ou texto só com dígitos), o máximo de dígitos e a mensagem de erro.
    Retorna o número inteiro conferido.
    Lança ValueError com a mensagem se o valor for vazio, decimal, negativo, zero, bool, com letras ou grande demais.
    """
    if isinstance(valor, bool):
        raise ValueError(mensagem)

    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, str):
        texto = valor.strip()
        if texto == "" or len(texto) > maximo_digitos:
            raise ValueError(mensagem)
        for caractere in texto:
            if caractere not in "0123456789":
                raise ValueError(mensagem)
        numero = int(texto)
    else:
        raise ValueError(mensagem)

    if numero <= 0 or len(str(numero)) > maximo_digitos:
        raise ValueError(mensagem)
    return numero


def conferir_nf(valor):
    """
    Recebe a NF digitada (número ou texto).
    Retorna a NF como número inteiro.
    Lança ValueError se não for um inteiro positivo com até TAMANHO_MAXIMO_NF dígitos.
    """
    mensagem = f"A NF precisa ser um número inteiro positivo com até {TAMANHO_MAXIMO_NF} dígitos."
    return converter_inteiro_positivo(valor, TAMANHO_MAXIMO_NF, mensagem)


def conferir_volume(valor):
    """
    Recebe o volume digitado (número ou texto).
    Retorna o volume como número inteiro.
    Lança ValueError se não for um inteiro de 1 a VOLUME_MAXIMO.
    """
    mensagem = f"O volume precisa ser um número inteiro de 1 a {VOLUME_MAXIMO}."
    volume = converter_inteiro_positivo(valor, len(str(VOLUME_MAXIMO)), mensagem)
    if volume > VOLUME_MAXIMO:
        raise ValueError(mensagem)
    return volume


def conferir_entregar_no(valor):
    """
    Recebe o local de entrega escolhido.
    Retorna o mesmo valor, se estiver em DESTINOS_VALIDOS.
    Lança ValueError se for diferente de "transportadora" ou "cliente".
    """
    if not isinstance(valor, str) or valor not in DESTINOS_VALIDOS:
        raise ValueError("O local de entrega precisa ser cliente ou transportadora.")
    return valor


def esta_vazio(valor):
    """
    Recebe um valor digitado.
    Retorna True se for None ou texto só com espaços / False, se tiver conteúdo.
    """
    return valor is None or (isinstance(valor, str) and valor.strip() == "")


def conferir_nf_opcional(valor):
    """
    Recebe a NF digitada (ou nada).
    Retorna None, se estiver vazia / a NF como número inteiro.
    Lança ValueError se estiver preenchida com um valor inválido.
    """
    if esta_vazio(valor):
        return None
    return conferir_nf(valor)


def conferir_volume_opcional(valor):
    """
    Recebe o volume digitado (ou nada).
    Retorna None, se estiver vazio / o volume como número inteiro.
    Lança ValueError se estiver preenchido com um valor inválido.
    """
    if esta_vazio(valor):
        return None
    return conferir_volume(valor)


def conferir_transportadora_id(valor):
    """
    Recebe o número da transportadora.
    Retorna o número como inteiro.
    Lança ValueError se não for um inteiro positivo.
    """
    return converter_inteiro_positivo(valor, TAMANHO_MAXIMO_CODIGO, "Transportadora inválida.")


def conferir_destino(destino_tipo, transportadora_id):
    """
    Recebe o tipo de destino e o número da transportadora.
    Retorna (tipo de destino, número da transportadora / None, quando o destino é o cliente).
    Lança ValueError se o destino for inválido ou se for transportadora sem número válido.
    """
    destino_tipo = conferir_entregar_no(destino_tipo)
    if destino_tipo == "transportadora":
        return destino_tipo, conferir_transportadora_id(transportadora_id)
    return destino_tipo, None


def limpar_nome(texto):
    """
    Recebe um nome (do cliente ou do destino).
    Retorna o nome sem CPF, sem espaços sobrando, com no máximo TAMANHO_MAXIMO_NOME caracteres / "", se vier vazio.
    Passar o resultado de novo por esta função não muda nada.
    """
    if texto is None:
        return ""
    nome = " ".join(str(texto).split())
    if nome == "":
        return ""
    return textos.esconder_cpf(textos.esconder_cpf(nome)[:TAMANHO_MAXIMO_NOME])
#______________________________________________________________________________________________________________________#
#Lista as entregas concluídas (aba Entregas do Histórico)

def listar_historico_entregas(limite=200):
    """
    Recebe o máximo de linhas.
    Retorna as entregas concluídas nos últimos DIAS_GUARDAR_DADOS dias, das mais recentes para as mais antigas,
    cada uma como dicionário.
    """
    data_limite = (datetime.now() - timedelta(days=DIAS_GUARDAR_DADOS)).strftime("%Y-%m-%d")
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""SELECT data_hora, pedido_id, eh_extra, motivo, nf, volume, destino_tipo, destino_nome, cliente_nome
                      FROM historico_entregas WHERE data_hora >= ? ORDER BY data_hora DESC, id DESC LIMIT ?""",
                   (data_limite, limite))
    linhas = cursor.fetchall()
    conexao.close()

    entregas = []
    for linha in linhas:
        entregas.append({"data_hora": linha[0], "pedido_id": linha[1], "eh_extra": linha[2] == 1, "motivo": linha[3],
                         "nf": linha[4], "volume": linha[5], "destino_tipo": linha[6], "destino_nome": linha[7],
                         "cliente_nome": linha[8]})
    return entregas
#______________________________________________________________________________________________________________________#