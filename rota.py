import banco
import funcoes
import textos

limite_distancia_metros = 50000
COTA_GRATIS_ELEMENTOS = 5000 # limite grátis por mês da Routes API (Compute Route Matrix Pro)
MENSAGEM_TEMPO_INVALIDO = "Não foi possível calcular o tempo da rota. Confira os endereços e tente de novo."

#______________________________________________________________________________________________________________________#
#Confere a quantidade de entregas e calcula a cota prevista, antes de gerar

def conferir_antes_de_gerar(total_pedidos_salvos, quantidade_extras, quantidade):
    """
    Recebe quantos pedidos há na lista, quantas paradas as paradas extras ocupam e o total de entregas escolhido.
    Retorna a mensagem de bloqueio / None, se pode gerar.
    """
    if quantidade_extras > quantidade:
        return (f"Há {quantidade_extras} paradas extras, mais que o total de {quantidade} entregas. "
                f"Aumente o total ou tire paradas extras.")
    if total_pedidos_salvos == 0 and quantidade_extras == 0:
        return "A lista de pedidos está vazia e não há paradas extras. Adicione pedidos ou paradas extras."
    return None


def elementos_previstos(total_pedidos_salvos, quantidade_extras, quantidade):
    """
    Recebe quantos pedidos há na lista, quantas paradas as paradas extras ocupam e o total de entregas escolhido.
    Retorna quantos elementos da cota a rota vai usar, no máximo: (paradas + 1)².
    """
    pedidos_usados = min(quantidade - quantidade_extras, total_pedidos_salvos)
    if pedidos_usados < 0:
        pedidos_usados = 0
    return (pedidos_usados + quantidade_extras + 1) ** 2


def contar_paradas_extras(paradas_extras):
    """
    Recebe a lista de paradas extras.
    Retorna quantas paradas elas ocupam: as que vão para a mesma transportadora contam como uma só.
    """
    transportadoras = []
    total = 0
    for parada in paradas_extras:
        transportadora_id = parada.get("transportadora_id")
        if transportadora_id is None:
            total += 1
        elif transportadora_id not in transportadoras:
            transportadoras.append(transportadora_id)
            total += 1
    return total


def mensagem_pedidos_incompletos(codigos):
    """
    Recebe os códigos dos pedidos sem NF ou volume.
    Retorna a mensagem que explica o bloqueio da rota / "", se não houver nenhum.
    """
    if len(codigos) == 0:
        return ""
    textos = []
    for codigo in codigos:
        textos.append(str(codigo))
    if len(textos) == 1:
        return f"O pedido {textos[0]} está sem NF ou volume. Preencha na Lista de Pedidos para gerar a rota."
    return (f"Os pedidos {', '.join(textos[:-1])} e {textos[-1]} estão sem NF ou volume. "
            f"Preencha na Lista de Pedidos para gerar a rota.")


def conferir_pedidos_completos(lista_de_pedidos):
    """
    Recebe os pedidos salvos.
    Lança ValueError se algum pedido estiver sem NF ou volume.
    """
    incompletos = []
    for pedido in lista_de_pedidos:
        if pedido.get("nf") is None or pedido.get("volume") is None:
            incompletos.append(pedido["codigo"])
    if len(incompletos) > 0:
        raise ValueError(mensagem_pedidos_incompletos(incompletos))
#______________________________________________________________________________________________________________________#
#Busca a transportadora pelo número, guardando o resultado durante a sessão

def obter_transportadora(transportadora_id, cache, token_acesso, token_secreta):
    """
    Recebe o número da transportadora, o cache da sessão (dicionário) e os tokens.
    Retorna a transportadora ({id, nome, endereco}) / None, se não encontrar ou se não tiver endereço.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    if transportadora_id in cache:
        return cache[transportadora_id]
    transportadora = funcoes.buscar_transportadora_por_id(transportadora_id, token_acesso, token_secreta)
    if transportadora is not None:
        cache[transportadora_id] = transportadora
    return transportadora
#______________________________________________________________________________________________________________________#
#Monta as paradas: tudo que vai para a mesma transportadora fica numa parada só

def nova_parada(item, endereco):
    """
    Recebe o primeiro item da parada e o endereço do destino em texto.
    Retorna a parada nova.
    """
    return {"destino_tipo": item["destino_tipo"],
            "transportadora_id": item["transportadora_id"],
            "destino_nome": item["destino_nome"],
            "endereco": endereco,
            "itens": [item]}


def parada_da_transportadora(paradas, transportadora_id):
    """
    Recebe as paradas já montadas e o número da transportadora.
    Retorna a parada dessa transportadora / None, se ainda não existir.
    """
    if transportadora_id is None:
        return None
    for parada in paradas:
        if parada["destino_tipo"] == "transportadora" and parada["transportadora_id"] == transportadora_id:
            return parada
    return None


def colocar_na_transportadora(paradas, item, transportadora):
    """
    Recebe as paradas, o item e a transportadora de destino.
    Junta o item na parada da transportadora ou cria a parada, se ainda não existir.
    """
    item["destino_tipo"] = "transportadora"
    item["transportadora_id"] = transportadora["id"]
    item["destino_nome"] = transportadora["nome"]
    existente = parada_da_transportadora(paradas, transportadora["id"])
    if existente is None:
        paradas.append(nova_parada(item, funcoes.enderecos_em_texto(transportadora["endereco"])))
    else:
        existente["itens"].append(item)


def montar_paradas_extras(paradas_extras, paradas, problemas, cache, token_acesso, token_secreta):
    """
    Recebe as paradas extras conferidas, a lista de paradas, a lista de problemas, o cache e os tokens.
    Coloca cada parada extra no endereço do cliente ou na parada da transportadora escolhida.
    """
    for extra in paradas_extras:
        cliente_id = extra["cliente_id"]
        motivo = extra["motivo"]
        nome = textos.esconder_cpf(str(extra.get("nome") or ""), "") or f"Cliente {cliente_id}"
        item = {"tipo": "extra", "cliente_id": cliente_id, "motivo": motivo, "nf": extra.get("nf"),
                "volume": extra.get("volume"), "cliente_nome": nome, "destino_tipo": "cliente",
                "transportadora_id": None, "destino_nome": nome}

        if extra.get("transportadora_id") is None:
            endereco = funcoes.enderecos_em_texto(extra.get("endereco") or {})
            if endereco == "":
                problemas.append(f"Parada extra {cliente_id} ({motivo}): cliente sem endereço cadastrado.")
            else:
                paradas.append(nova_parada(item, endereco))
        else:
            transportadora = obter_transportadora(extra["transportadora_id"], cache, token_acesso, token_secreta)
            if transportadora is None:
                problemas.append(f"Parada extra {cliente_id} ({motivo}): transportadora sem endereço cadastrado.")
            else:
                colocar_na_transportadora(paradas, item, transportadora)


def montar_paradas_pedidos(lista_de_pedidos, quantidade, paradas, problemas, cache, token_acesso, token_secreta):
    """
    Recebe os pedidos salvos (na ordem de prioridade), o total de paradas, a lista de paradas, a lista de problemas,
    o cache e os tokens.
    Percorre os pedidos na ordem: cada destino novo ocupa uma parada; o pedido que vai para uma transportadora que já
    tem parada entra nela sem contar de novo. Quando as paradas acabam, os outros pedidos ficam para a próxima rota.
    """
    for pedido_salvo in lista_de_pedidos:
        codigo = pedido_salvo["codigo"]
        entregar_no = pedido_salvo.get("entregar_no")
        cheia = len(paradas) >= quantidade
        if cheia and entregar_no == "cliente":
            continue

        pedido = funcoes.buscar_pedido(codigo, token_acesso, token_secreta)
        if pedido is None:
            if not cheia:
                problemas.append(f"Pedido {codigo} não encontrado no GestãoClick.")
            continue

        transportadora_id = funcoes.transportadora_do_pedido(pedido)
        if entregar_no is None:
            entregar_no = "cliente"
            if transportadora_id is not None:
                entregar_no = "transportadora"

        item = {"tipo": "pedido", "codigo": codigo, "cliente_id": funcoes.converter_id(pedido.get("cliente_id")),
                "motivo": "", "nf": pedido_salvo.get("nf"), "volume": pedido_salvo.get("volume"),
                "cliente_nome": textos.esconder_cpf(str(pedido.get("nome_cliente") or ""), ""), "destino_tipo": "cliente",
                "transportadora_id": None, "destino_nome": ""}

        if entregar_no == "transportadora":
            if cheia and parada_da_transportadora(paradas, transportadora_id) is None:
                continue
            if transportadora_id is None:
                problemas.append(f"Pedido {codigo}: a venda não tem transportadora no GestãoClick.")
                continue
            transportadora = obter_transportadora(transportadora_id, cache, token_acesso, token_secreta)
            if transportadora is None:
                problemas.append(f"Pedido {codigo}: transportadora sem endereço cadastrado.")
                continue
            colocar_na_transportadora(paradas, item, transportadora)
        else:
            if cheia:
                continue
            ficha = None
            if item["cliente_id"] is not None:
                ficha = funcoes.buscar_endereco(item["cliente_id"], token_acesso, token_secreta)
            cliente = None
            if ficha is not None:
                cliente = funcoes.montar_parada_extra(ficha, "")
            if cliente is None:
                problemas.append(f"Pedido {codigo}: cliente sem endereço cadastrado.")
                continue
            item["cliente_nome"] = cliente["nome"] or item["cliente_nome"]
            item["destino_nome"] = item["cliente_nome"]
            paradas.append(nova_parada(item, funcoes.enderecos_em_texto(cliente["endereco"])))
#______________________________________________________________________________________________________________________#
#Tira da rota o que ficou fora do raio de 50 km (o raio vale para o destino: cliente ou transportadora)

def separar_fora_do_raio(paradas, distancias, indice_entregas, fora_do_raio, problemas):
    """
    Recebe as paradas, a tabela de distâncias, as posições dentro do raio, as de fora e a lista de problemas.
    Pedidos fora do raio ficam para a próxima. Paradas extras fora do raio continuam, se houver caminho.
    Retorna as posições que entram na rota.
    """
    entram = indice_entregas.copy()
    for indice in fora_do_raio:
        parada = paradas[indice - 1]
        tem_caminho = distancias[0][indice] != float("inf")
        extras_que_ficam = []
        for item in parada["itens"]:
            if item["tipo"] == "pedido":
                problemas.append(f"Pedido {item['codigo']}: fora do raio de 50 km ou sem rota.")
            elif tem_caminho:
                extras_que_ficam.append(item)
            else:
                problemas.append(f"Parada extra {item['cliente_id']} ({item['motivo']}): sem caminho no Google Maps.")
        parada["itens"] = extras_que_ficam
        if len(extras_que_ficam) > 0:
            entram.append(indice)
    return entram
#______________________________________________________________________________________________________________________#
#Código principal - gera a rota de entregas!

def gerar_rota(lista_de_pedidos, quantidade, hora_inicio, hora_retorno,
               token_acesso, token_secreta, chave_maps, endereco_base, paradas_extras=None, cache_transportadoras=None):
    """
    Recebe os pedidos salvos (dicionários com codigo, nf, volume e entregar_no, na ordem de prioridade), o total de
    paradas, os horários, os tokens, a chave do Google, o endereço da base, as paradas extras e o cache de
    transportadoras da sessão.
    Retorna o resultado: paradas na ordem (cada uma com seus itens), itens na ordem, tempos e problemas.
    Lança ValueError se algum dado for inválido / ErroAPI se não conseguir falar com as APIs.
    """
    if paradas_extras is None:
        paradas_extras = []
    if cache_transportadoras is None:
        cache_transportadoras = {}

    paradas_extras = banco.conferir_paradas_extras_antes_da_rota(paradas_extras)
    mensagem = conferir_antes_de_gerar(len(lista_de_pedidos), contar_paradas_extras(paradas_extras), quantidade)
    if mensagem is not None:
        raise ValueError(mensagem)
    conferir_pedidos_completos(lista_de_pedidos)

    paradas = []
    problemas = []
    montar_paradas_extras(paradas_extras, paradas, problemas, cache_transportadoras, token_acesso, token_secreta)
    montar_paradas_pedidos(lista_de_pedidos, quantidade, paradas, problemas, cache_transportadoras,
                           token_acesso, token_secreta)
    quantidade_pedida = len(paradas)

    if len(paradas) == 0:
        resultado = {"paradas": [],
                     "itens_na_rota": [],
                     "pedidos_na_rota": [],
                     "tempo_de_entrega": 0,
                     "tempo_disponivel": 0,
                     "cabe_no_horario": False,
                     "problemas": problemas,
                     "quantidade_pedida": quantidade_pedida,
                     "elementos_usados": 0}
        return resultado

    base_e_destinos = [endereco_base]
    for parada in paradas:
        base_e_destinos.append(parada["endereco"])

    distancias, tempos = funcoes.calcular_distancia(base_e_destinos, chave_maps)

    indice_entregas, fora_do_raio = funcoes.filtrar_por_raio(distancias, limite_distancia_metros)
    indice_entregas = separar_fora_do_raio(paradas, distancias, indice_entregas, fora_do_raio, problemas)

    indice_rota = funcoes.ordenar_vizinho_mais_proximo(distancias, indice_entregas)

    paradas_na_rota = []
    itens_na_rota = []
    pedidos_na_rota = []
    for indice in indice_rota:
        if indice != 0:
            parada = paradas[indice - 1]
            paradas_na_rota.append(parada)
            for item in parada["itens"]:
                itens_na_rota.append(item)
                if item["tipo"] == "pedido":
                    pedidos_na_rota.append(item["codigo"])

    tempo_de_entrega = funcoes.calcular_tempo_total(tempos, indice_rota)
    segundos_entrega_disponiveis = funcoes.calcular_tempo_disponivel(hora_inicio, hora_retorno)

    resultado = {"paradas": paradas_na_rota,
                 "itens_na_rota": itens_na_rota,
                 "pedidos_na_rota": pedidos_na_rota,
                 "tempo_de_entrega": tempo_de_entrega,
                 "tempo_disponivel": segundos_entrega_disponiveis,
                 "cabe_no_horario": tempo_de_entrega <= segundos_entrega_disponiveis,
                 "problemas": problemas,
                 "quantidade_pedida": quantidade_pedida,
                 "elementos_usados": len(base_e_destinos) * len(base_e_destinos)}

    return resultado
#______________________________________________________________________________________________________________________#
#Textos de cada parada, iguais na tela e no PDF

def texto_nf(nf):
    """
    Recebe a NF (ou None).
    Retorna "NF 4540" / "", se não houver NF.
    """
    if nf is None:
        return ""
    return f"NF {nf}"


def texto_volumes(volume):
    """
    Recebe a quantidade de volumes (ou None).
    Retorna "1 volume", "5 volumes" / "", se não houver volume.
    """
    if volume is None:
        return ""
    if volume == 1:
        return "1 volume"
    return f"{volume} volumes"


def juntar_partes(partes):
    """
    Recebe uma lista de textos.
    Retorna os textos preenchidos separados por " · ".
    """
    preenchidas = []
    for parte in partes:
        if parte is not None and str(parte) != "":
            preenchidas.append(str(parte))
    return " · ".join(preenchidas)


def nome_para_exibir(nome):
    """
    Recebe um nome (do cliente ou do destino).
    Retorna o nome sem CPF / "", se vier vazio ou se só tiver o CPF.
    """
    return textos.esconder_cpf(nome, "")


def parada_para_exibir(parada, endereco):
    """
    Recebe a parada (com destino e itens) e o endereço do destino em texto.
    Retorna o dicionário com os textos da tela e do PDF: tipo, titulo, detalhe, cliente, endereco e itens.
    Os nomes passam por esconder_cpf.
    """
    itens = parada["itens"]
    if parada["destino_tipo"] == "transportadora":
        itens_texto = []
        for item in itens:
            if item["tipo"] == "pedido":
                itens_texto.append({"titulo": juntar_partes([f"Pedido {item['codigo']}", texto_nf(item["nf"]),
                                                             nome_para_exibir(item["cliente_nome"])]),
                                    "detalhe": texto_volumes(item["volume"])})
            else:
                itens_texto.append({"titulo": juntar_partes(["Parada extra", nome_para_exibir(item["cliente_nome"]),
                                                             item["motivo"], texto_nf(item["nf"]),
                                                             texto_volumes(item["volume"])]),
                                    "detalhe": ""})
        titulo = nome_para_exibir(parada["destino_nome"]) or f"Transportadora {parada['transportadora_id']}"
        return {"tipo": "transportadora", "titulo": titulo, "detalhe": "", "cliente": "", "endereco": endereco,
                "itens": itens_texto}

    item = itens[0]
    if item["tipo"] == "pedido":
        return {"tipo": "pedido", "titulo": juntar_partes([f"Pedido {item['codigo']}", texto_nf(item["nf"])]),
                "detalhe": texto_volumes(item["volume"]), "cliente": nome_para_exibir(item["cliente_nome"]),
                "endereco": endereco, "itens": []}
    return {"tipo": "extra", "titulo": juntar_partes(["Parada extra", nome_para_exibir(item["cliente_nome"])]),
            "detalhe": juntar_partes([item["motivo"], texto_nf(item["nf"]), texto_volumes(item["volume"])]),
            "cliente": "", "endereco": endereco, "itens": []}
#______________________________________________________________________________________________________________________#
#Busca de novo o endereço de cada parada da última rota (os endereços não ficam no banco)

def buscar_endereco_da_parada(parada, cache, token_acesso, token_secreta):
    """
    Recebe a parada da última rota, o cache de transportadoras e os tokens.
    Retorna o endereço do destino em texto / "", se não encontrar.
    Lança ErroAPI se não conseguir falar com o GestãoClick.
    """
    if parada["destino_tipo"] == "transportadora":
        transportadora = obter_transportadora(parada["transportadora_id"], cache, token_acesso, token_secreta)
        if transportadora is None:
            return ""
        return funcoes.enderecos_em_texto(transportadora["endereco"])

    item = parada["itens"][0]
    cliente_id = item["cliente_id"]
    if item["tipo"] == "pedido":
        pedido = funcoes.buscar_pedido(item["codigo"], token_acesso, token_secreta)
        if pedido is None:
            return ""
        cliente_id = funcoes.converter_id(pedido.get("cliente_id"))
    if cliente_id is None:
        return ""

    ficha = funcoes.buscar_endereco(cliente_id, token_acesso, token_secreta)
    if ficha is None:
        return ""
    cliente = funcoes.montar_parada_extra(ficha, "")
    if cliente is None:
        return ""
    return funcoes.enderecos_em_texto(cliente["endereco"])
#______________________________________________________________________________________________________________________#
