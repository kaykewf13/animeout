from stream_validator import validar_stream

def validar_lista(itens):
    validos = []

    for item in itens:
        if validar_stream(item["stream_url"]):
            validos.append(item)

    return validos