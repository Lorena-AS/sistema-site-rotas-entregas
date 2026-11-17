import time  # permite pausar o programa por alguns instantes
import requests  # faz chamadas HTTP para as APIs
import textos

TEMPO_LIMITE = 15  # segundos de espera máxima pela resposta de uma API
PAUSA_ENTRE_CHAMADAS = 0.35  # segundos entre consultas (limite do GestãoClick: 3 por segundo)
URL_GESTAOCLICK = "https://api.gestaoclick.com"
URL_ROUTES = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
SITUACAO_LIBERADA = "Concretizada"  # obriga o pedido a estar finalizado para entrar na lista
MAXIMO_PAGINAS_TRANSPORTADORA = 3
TAMANHO_MINIMO_NOME_TRANSPORTADORA = 3


class ErroAPI(Exception):
    """Erro de comunicação com uma API, com mensagem para o usuário."""

#______________________________________________________________________________________________________________________#
#Faz uma consulta ao GestãoClick respeitando o limite de requisições

def consultar_gestaoclick(caminho, token_acesso, token_secreta, params=None):
    """
    Faz um GET no GestãoClick e devolve a resposta.
    Lança ErroAPI se não conseguir conectar ou se o limite de consultas for atingido.
    """
    headers = {"Content-Type": "application/json",
               "access-token": token_acesso,
               "secret-access-token": token_secreta}

    time.sleep(PAUSA_ENTRE_CHAMADAS)  # espera um pouco antes de cada consulta
    try:
        resposta = requests.get(f"{URL_GESTAOCLICK}{caminho}",
                                headers=headers, params=params, timeout=TEMPO_LIMITE)
    except requests.RequestException:
        raise ErroAPI("Não foi possível conectar ao GestãoClick. Verifique a internet.")

    if resposta.status_code == 429:
        raise ErroAPI("Muitas consultas ao GestãoClick. Aguarde 1 minuto e tente novamente.")

    return resposta
#______________________________________________________________________________________________________________________#
#Busca os pedidos pela API do GestãoClick

def buscar_pedido(id_pd: int, token_acesso, token_secreta):
    """
    Procura o pedido em Produtos e, se não achar, em Serviços.
    Retorna o dicionário do pedido / None, se não existir em nenhuma das duas.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    categoria = ["Produtos",
                 "Serviços"]

    for tipo in categoria:
        params = {"tipo": tipo,
                  "codigo": id_pd}
        resposta = consultar_gestaoclick("/vendas", token_acesso, token_secreta, params)

        if resposta.status_code != 200:
            raise ErroAPI(f"O GestãoClick recusou a consulta (código {resposta.status_code}).")

        dados = resposta.json()
        if len(dados.get("data", [])) > 0:
            pedido = dados["data"][0]
            return pedido

    return None

#Confere se todos os pedidos estão com a situação liberada no GestãoClick

def verificar_situacao_pedidos(lista_de_codigos, token_acesso, token_secreta):
    erros = []
    for codigo in lista_de_codigos:
        pedido = buscar_pedido(codigo, token_acesso, token_secreta)
        if pedido is None:
            erros.append(f"PEDIDO {codigo} NÃO ENCONTRADO NO SISTEMA.")
        else:
            situacao = pedido.get("nome_situacao", "")
            if situacao != SITUACAO_LIBERADA:
                erros.append(f"PEDIDO {codigo} NÃO ESTÁ CONCLUÍDO NO SISTEMA. STATUS: {situacao}")

    return erros
#______________________________________________________________________________________________________________________#
#Busca a ficha do cliente pelo ID

def buscar_endereco(id_cl: int, token_acesso, token_secreta):
    """
    Recebe o ID do cliente e os tokens.
    Retorna a ficha do cliente / None, se não encontrar.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    resposta = consultar_gestaoclick(f"/clientes/{int(id_cl)}", token_acesso, token_secreta)

    if resposta.status_code == 404:
        return None
    if resposta.status_code != 200:
        raise ErroAPI(f"O GestãoClick recusou a consulta (código {resposta.status_code}).")

    dados = resposta.json()
    cliente = dados.get("data")
    if isinstance(cliente, dict) and cliente:
        return cliente

    return None
#______________________________________________________________________________________________________________________#
#Busca o endereço de cada pedido e avisa os que deram problema

def buscar_enderecos_dos_pedidos(lista_de_pedidos, token_acesso, token_secreta):
    """
      Recebe a lista de pedidos e os tokens.
      Retorna os pedidos encontrados, os endereços de entrega, a lista de problemas e o nome de cada cliente.
      """
    pedidos_encontrados = []
    enderecos_entrega = []
    problemas = []
    nomes_clientes = []

    for codigo in lista_de_pedidos:
        pedido = buscar_pedido(codigo, token_acesso, token_secreta)
        if pedido is None:
            problemas.append(f"Pedido {codigo} não encontrado no GestãoClick.")
        else:
            cliente = buscar_endereco(pedido["cliente_id"], token_acesso, token_secreta)
            if cliente is None or len(cliente.get("enderecos", [])) == 0:
                problemas.append(f"Pedido {codigo}: cliente sem endereço cadastrado.")
            else:
                pedidos_encontrados.append(codigo)
                enderecos_entrega.append(cliente["enderecos"][0]["endereco"])
                nome = cliente.get("nome") or pedido.get("nome_cliente") or ""
                nomes_clientes.append(textos.esconder_cpf(str(nome), ""))

    return pedidos_encontrados, enderecos_entrega, problemas, nomes_clientes
#______________________________________________________________________________________________________________________#
#Transformar endereços em uma lista (em formato de texto)

def enderecos_em_texto(endereco):
    chaves = ["cep", "logradouro", "bairro", "numero", "nome_cidade", "estado"]
    requisitos = []

    for valor in chaves:
        valor_conteudo = endereco.get(valor) or ""
        if valor_conteudo != "":
            requisitos.append(str(valor_conteudo))
    return ', '.join(requisitos)
#______________________________________________________________________________________________________________________#
#Calcular a distância e o tempo entre os endereços com a ROUTES API

def calcular_distancia(lista_enderecos, chave_maps):
    """
    Recebe a lista de endereços (base primeiro) e a chave do Google.
    Retorna a tabela de distâncias (metros) e a de tempos (segundos) / infinito, se não houver rota.
    """
    headers = {"Content-Type": "application/json",
               "X-Goog-Api-Key": chave_maps,
               "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters,duration,condition"}

    pontos = []
    for endereco in lista_enderecos:
        pontos.append({"waypoint": {"address": endereco}})

    corpo = {"origins": pontos,
             "destinations": pontos,
             "travelMode": "DRIVE",
             "routingPreference": "TRAFFIC_AWARE"}  # considera o trânsito do momento

    try:
        resposta = requests.post(URL_ROUTES, headers=headers, json=corpo, timeout=TEMPO_LIMITE)
    except requests.RequestException:
        raise ErroAPI("Não foi possível conectar ao Google Maps. Verifique a internet.")

    if resposta.status_code == 403:
        raise ErroAPI("A chave do Google Maps não tem permissão para a Routes API.")
    if resposta.status_code != 200:
        raise ErroAPI(f"O Google Maps recusou a consulta (código {resposta.status_code}).")

    total = len(lista_enderecos)
    distancias = []
    tempos = []
    for i in range(total):
        linha_distancia = []
        linha_tempo = []
        for j in range(total):
            linha_distancia.append(float("inf"))
            linha_tempo.append(float("inf"))
        distancias.append(linha_distancia)
        tempos.append(linha_tempo)

    dados = resposta.json()
    for elemento in dados:
        if elemento.get("condition") == "ROUTE_EXISTS":
            origem = elemento.get("originIndex", 0)
            destino = elemento.get("destinationIndex", 0)
            distancias[origem][destino] = elemento.get("distanceMeters", 0)
            texto_tempo = elemento.get("duration", "0s")
            tempos[origem][destino] = int(texto_tempo.replace("s", ""))

    return distancias, tempos
#______________________________________________________________________________________________________________________#
#Limitando a distância para 50km a partir da base

def filtrar_por_raio(distancias, limite_distancia_metros):
    """
    Recebe a tabela de distâncias e o limite em metros.
    Retorna as posições dentro do raio e as que ficaram de fora.
    """
    indice_entregas = []
    fora_do_raio = []

    for i in range(1, len(distancias)):
        if distancias[0][i] <= limite_distancia_metros:
            indice_entregas.append(i)
        else:
            fora_do_raio.append(i)

    return indice_entregas, fora_do_raio
#______________________________________________________________________________________________________________________#
#Comparando o vizinho mais próximo

def ordenar_vizinho_mais_proximo(distancias, indice_entregas):
    """
    Recebe a tabela de distâncias e as posições das entregas.
    Retorna a ordem da rota, saindo e voltando para a base (posição 0).
    """
    faltam_visitar = indice_entregas.copy()
    indice_rota = [0]
    inicio = 0
    while len(faltam_visitar) != 0:
        linha_matriz = distancias[inicio]
        entrega = min(faltam_visitar, key=lambda proximo: linha_matriz[proximo])
        # min(faltam_visitar, key=...): verifica cada candidato que ainda falta visitar
        # distancias[inicio]: linha da matriz referente ao ponto atual
        # linha_matriz[proximo]: distância até aquele candidato
        # o min() devolve o índice do candidato mais próximo
        indice_rota.append(entrega) # adiciona o indice mais proximo
        faltam_visitar.remove(entrega) # remove o ultimo indice
        inicio = entrega # atualiza o inicio pro último indice pesquisado
    indice_rota.append(0)

    return indice_rota
#______________________________________________________________________________________________________________________#
#Delimitando retorno dentro do tempo do expediente

def calcular_tempo_total(tempos, indice_rota):
    """
    Recebe a tabela de tempos e a ordem da rota.
    Retorna o tempo total de deslocamento, em segundos.
    """
    tempo_de_entrega = 0 # resultado do tempo (em segundos)
    for i in range(len(indice_rota) - 1): # -1 porque cada volta usa o ponto atual (i) e o próximo (i + 1);
        # o último ponto não tem próximo
        primeiro_ponto = indice_rota[i]
        segundo_ponto = indice_rota[i + 1]
        tempo = tempos[primeiro_ponto][segundo_ponto]
        tempo_de_entrega += tempo

    return tempo_de_entrega

def calcular_tempo_disponivel(hora_inicio, hora_retorno):
    segundos_inicio = hora_inicio.hour * 3600 + hora_inicio.minute * 60 # converte o horário de saída em segundos
    segundos_retorno = hora_retorno.hour * 3600 + hora_retorno.minute * 60 # converte o horário de retorno em segundos
    segundos_entrega_disponiveis = segundos_retorno - segundos_inicio # tempo disponível entre a saída e o retorno

    return segundos_entrega_disponiveis # devolve o tempo disponível em segundos
#______________________________________________________________________________________________________________________#
#Limpa e formata o CPF ou CNPJ digitado

def limpar_documento(texto):
    """
    Recebe o CPF ou CNPJ digitado, com ou sem pontuação.
    Retorna só os dígitos / None, se tiver caractere não permitido ou não tiver 11 ou 14 dígitos.
    """
    if texto is None:
        return None

    permitidos = "0123456789./- "
    digitos = []
    for caractere in str(texto):
        if caractere not in permitidos:
            return None
        if caractere in "0123456789":
            digitos.append(caractere)

    so_digitos = "".join(digitos)
    if len(so_digitos) == 11 or len(so_digitos) == 14:
        return so_digitos
    return None


def formatar_documento(digitos):
    """
    Recebe só os dígitos do CPF ou CNPJ.
    Retorna o documento com pontuação / None, se não tiver 11 ou 14 dígitos.
    """
    if len(digitos) == 11:
        return f"{digitos[0:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"
    if len(digitos) == 14:
        return f"{digitos[0:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:14]}"
    return None
#______________________________________________________________________________________________________________________#
#Busca o cliente pelo CPF ou CNPJ, aceitando só o documento exatamente igual

def procurar_clientes_por_filtro(filtro, token_acesso, token_secreta):
    """
    Recebe o filtro de CPF ou CNPJ e os tokens.
    Retorna a lista de clientes que o GestãoClick devolveu / lista vazia, se não encontrar.
    Lança ErroAPI se não conseguir falar com o GestãoClick ou se a resposta vier fora do esperado.
    """
    resposta = consultar_gestaoclick("/clientes", token_acesso, token_secreta, {"cpf_cnpj": filtro})

    if resposta.status_code == 404:
        return []
    if resposta.status_code != 200:
        raise ErroAPI(f"O GestãoClick recusou a consulta (código {resposta.status_code}).")

    try:
        dados = resposta.json()
    except ValueError:
        raise ErroAPI("O GestãoClick enviou uma resposta inesperada.")

    if not isinstance(dados, dict):
        raise ErroAPI("O GestãoClick enviou uma resposta inesperada.")

    clientes = dados.get("data") or []
    if not isinstance(clientes, list):
        raise ErroAPI("O GestãoClick enviou uma resposta inesperada.")

    return clientes


def buscar_cliente_por_documento(texto, token_acesso, token_secreta):
    """
    Recebe o CPF ou CNPJ digitado e os tokens.
    Retorna a ficha do cliente / None, se não encontrar ou se encontrar mais de um.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    digitos = limpar_documento(texto)
    if digitos is None:
        return None

    filtros = [digitos, formatar_documento(digitos)]
    for filtro in filtros:
        clientes = procurar_clientes_por_filtro(filtro, token_acesso, token_secreta)

        aceitos = []
        for cliente in clientes:
            if not isinstance(cliente, dict):
                continue
            if limpar_documento(cliente.get("cpf")) == digitos or limpar_documento(cliente.get("cnpj")) == digitos:
                aceitos.append(cliente)

        if len(aceitos) == 1:
            return aceitos[0]
        if len(aceitos) > 1:
            return None

    return None
#______________________________________________________________________________________________________________________#
#Separa da ficha do cliente só o que a parada extra precisa

def montar_parada_extra(ficha, motivo):
    """
    Recebe a ficha do cliente (do GestãoClick) e o motivo.
    Retorna o número do cliente, o motivo, o nome e o primeiro endereço / None, se faltar o número ou o endereço.
    """
    try:
        cliente_id = int(ficha.get("id"))
    except (TypeError, ValueError):
        return None

    enderecos = ficha.get("enderecos") or []
    if len(enderecos) == 0 or not isinstance(enderecos[0], dict):
        return None
    endereco = enderecos[0].get("endereco")
    if not isinstance(endereco, dict) or enderecos_em_texto(endereco) == "":
        return None

    return {"cliente_id": cliente_id,
            "motivo": motivo,
            "nome": textos.esconder_cpf(str(ficha.get("nome") or ""), ""),
            "endereco": endereco}
#______________________________________________________________________________________________________________________#
#Busca a transportadora da venda, pelo ID ou pelo nome

def ler_resposta_em_dicionario(resposta):
    """
    Recebe a resposta do GestãoClick.
    Retorna o conteúdo da resposta como dicionário.
    Lança ErroAPI se a resposta não for um JSON em formato de dicionário.
    """
    try:
        dados = resposta.json()
    except ValueError:
        raise ErroAPI("O GestãoClick enviou uma resposta inesperada.")

    if not isinstance(dados, dict):
        raise ErroAPI("O GestãoClick enviou uma resposta inesperada.")
    return dados


def converter_id(valor):
    """
    Recebe um ID vindo do GestãoClick (número ou texto).
    Retorna o ID como número inteiro / None, se for vazio, zero, bool ou tiver algo além de dígitos.
    """
    if isinstance(valor, bool):
        return None

    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, str):
        texto = valor.strip()
        if texto == "":
            return None
        for caractere in texto:
            if caractere not in "0123456789":
                return None
        numero = int(texto)
    else:
        return None

    if numero <= 0:
        return None
    return numero


def montar_transportadora(ficha):
    """
    Recebe a ficha da transportadora (do GestãoClick).
    Retorna o número, o nome e o primeiro endereço / None, se faltar o número ou o endereço.
    """
    if not isinstance(ficha, dict):
        return None

    id_transportadora = converter_id(ficha.get("id"))
    if id_transportadora is None:
        return None

    enderecos = ficha.get("enderecos") or []
    if not isinstance(enderecos, list) or len(enderecos) == 0 or not isinstance(enderecos[0], dict):
        return None
    endereco = enderecos[0].get("endereco")
    if not isinstance(endereco, dict) or enderecos_em_texto(endereco) == "":
        return None

    return {"id": id_transportadora,
            "nome": textos.esconder_cpf(str(ficha.get("nome") or ""), "Transportadora sem nome"),
            "endereco": endereco}


def transportadora_do_pedido(pedido):
    """
    Recebe o pedido que buscar_pedido devolveu (a venda do GestãoClick).
    Retorna o número da transportadora da venda / None, se a venda não tiver transportadora.
    """
    if not isinstance(pedido, dict):
        return None
    return converter_id(pedido.get("transportadora_id"))


def buscar_transportadora_da_venda(id_venda, token_acesso, token_secreta):
    """
    Reserva: o normal é usar transportadora_do_pedido, que lê a venda que buscar_pedido já trouxe.
    Recebe o ID interno da venda e os tokens.
    Retorna o número da transportadora da venda / None, se a venda não existir ou não tiver transportadora.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    resposta = consultar_gestaoclick(f"/vendas/{int(id_venda)}", token_acesso, token_secreta)

    if resposta.status_code == 404:
        return None
    if resposta.status_code != 200:
        raise ErroAPI(f"O GestãoClick recusou a consulta (código {resposta.status_code}).")

    dados = ler_resposta_em_dicionario(resposta)
    venda = dados.get("data")
    if not isinstance(venda, dict):
        return None
    return converter_id(venda.get("transportadora_id"))


def buscar_transportadora_por_id(id_transportadora, token_acesso, token_secreta):
    """
    Recebe o número da transportadora e os tokens.
    Retorna o número, o nome e o primeiro endereço / None, se não encontrar ou se não tiver endereço.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    resposta = consultar_gestaoclick(f"/transportadoras/{int(id_transportadora)}", token_acesso, token_secreta)

    if resposta.status_code == 404:
        return None
    if resposta.status_code != 200:
        raise ErroAPI(f"O GestãoClick recusou a consulta (código {resposta.status_code}).")

    dados = ler_resposta_em_dicionario(resposta)
    return montar_transportadora(dados.get("data"))


def tem_proxima_pagina(dados):
    """
    Recebe o conteúdo da resposta do GestãoClick.
    Retorna True se ainda houver uma próxima página / False, se não houver.
    """
    meta = dados.get("meta")
    if not isinstance(meta, dict):
        return False
    proxima = meta.get("proxima_pagina")
    return proxima is not None and proxima != ""


def procurar_transportadoras_por_nome(nome, token_acesso, token_secreta):
    """
    Recebe o nome (ou parte do nome) da transportadora e os tokens.
    Retorna a lista de transportadoras ativas com endereço / lista vazia, se não encontrar.
    Lança ValueError se o nome tiver menos de 3 letras ou se houver mais de MAXIMO_PAGINAS_TRANSPORTADORA páginas.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    if not isinstance(nome, str):
        raise ValueError(f"Digite pelo menos {TAMANHO_MINIMO_NOME_TRANSPORTADORA} letras do nome da transportadora.")
    nome = nome.strip()
    if len(nome) < TAMANHO_MINIMO_NOME_TRANSPORTADORA:
        raise ValueError(f"Digite pelo menos {TAMANHO_MINIMO_NOME_TRANSPORTADORA} letras do nome da transportadora.")

    encontradas = []
    for pagina in range(1, MAXIMO_PAGINAS_TRANSPORTADORA + 1):
        params = {"nome": nome,
                  "pagina": pagina}
        resposta = consultar_gestaoclick("/transportadoras", token_acesso, token_secreta, params)

        if resposta.status_code == 404:
            return encontradas
        if resposta.status_code != 200:
            raise ErroAPI(f"O GestãoClick recusou a consulta (código {resposta.status_code}).")

        dados = ler_resposta_em_dicionario(resposta)
        fichas = dados.get("data") or []
        if not isinstance(fichas, list):
            raise ErroAPI("O GestãoClick enviou uma resposta inesperada.")

        for ficha in fichas:
            if not isinstance(ficha, dict) or str(ficha.get("ativo")).strip() != "1":
                continue
            transportadora = montar_transportadora(ficha)
            if transportadora is not None:
                encontradas.append(transportadora)

        if not tem_proxima_pagina(dados):
            return encontradas

    raise ValueError("Muitos resultados. Digite um nome mais completo.")
#______________________________________________________________________________________________________________________#
#Busca o cliente de cada item na hora de confirmar as entregas (a cidade é sempre a do cliente)

def buscar_dados_do_pedido(codigo, token_acesso, token_secreta):
    """
    Recebe o código do pedido e os tokens.
    Retorna o nome, a cidade e o endereço do CLIENTE, o número do cliente e o número da transportadora da venda.
    A cidade é sempre a do cliente, mesmo quando a entrega é feita na transportadora.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    nome = ""
    cidade = ""
    cliente_id = None
    transportadora_id = None
    endereco = "Pedido não encontrado no GestãoClick"

    pedido = buscar_pedido(codigo, token_acesso, token_secreta)
    if pedido is not None:
        cliente_id = converter_id(pedido.get("cliente_id"))
        transportadora_id = transportadora_do_pedido(pedido)
        nome = pedido.get("nome_cliente") or ""
        endereco = "Cliente sem endereço cadastrado"
        if cliente_id is not None:
            ficha = buscar_endereco(cliente_id, token_acesso, token_secreta)
            if ficha is not None:
                nome = ficha.get("nome") or nome
                cliente = montar_parada_extra(ficha, "")
                if cliente is not None:
                    cidade = cliente["endereco"].get("nome_cidade") or ""
                    endereco = enderecos_em_texto(cliente["endereco"])

    return {"nome": textos.esconder_cpf(str(nome), ""), "cidade": str(cidade), "cliente_id": cliente_id,
            "transportadora_id": transportadora_id, "endereco": endereco}


def buscar_dados_da_parada_extra(cliente_id, token_acesso, token_secreta):
    """
    Recebe o número do cliente da parada extra e os tokens.
    Retorna o nome, a cidade e o endereço do cliente e o número do cliente.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    nome = f"Cliente {cliente_id}"
    cidade = ""
    endereco = "Cliente não encontrado no GestãoClick"

    ficha = buscar_endereco(cliente_id, token_acesso, token_secreta)
    if ficha is not None:
        endereco = "Cliente sem endereço cadastrado"
        if ficha.get("nome"):
            nome = textos.esconder_cpf(str(ficha.get("nome")), nome)
        cliente = montar_parada_extra(ficha, "")
        if cliente is not None:
            cidade = cliente["endereco"].get("nome_cidade") or ""
            endereco = enderecos_em_texto(cliente["endereco"])

    return {"nome": nome, "cidade": str(cidade), "cliente_id": cliente_id, "endereco": endereco}
#______________________________________________________________________________________________________________________#