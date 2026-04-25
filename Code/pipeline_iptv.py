import csv
import json

INPUT = "sources/catalog.csv"
OUTPUT_M3U = "valid_links.m3u"
OUTPUT_JSON = "web/catalog.json"

EXCLUDE_KEYWORDS = ["yaoi", "boys love", "shounen ai"]

def is_excluded(text):
    text = text.lower()
    return any(k in text for k in EXCLUDE_KEYWORDS)

def classify(item):
    text = (item["titulo"] + item["categoria"]).lower()
    item["is_anime"] = "true" if "anime" in text else "false"
    item["is_adult"] = "true" if any(x in text for x in ["hentai", "adult"]) else "false"
    return item

def agrupar_por_titulo(itens):
    grupos = {}
    for item in itens:
        chave = item["titulo"].strip().lower()
        grupos.setdefault(chave, []).append(item)
    return grupos

def calcular_score(item):
    score = 0
    if item["stream_url"].endswith(".m3u8"):
        score += 3
    if item["is_anime"] == "true":
        score += 2
    if item["is_adult"] == "true":
        score += 1
    return score

def selecionar_melhor_stream(grupo):
    for item in grupo:
        item["score"] = calcular_score(item)
    grupo.sort(key=lambda x: -x["score"])
    return grupo[0]

def group_title(item):
    categoria = item["categoria"]
    if item["is_adult"] == "true":
        categoria = f"Adultos | {categoria}"
    return f"{item['grupo']} | {categoria}"

def gerar_m3u(itens):
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for idx, item in enumerate(itens):
            f.write(
                f'#EXTINF:-1 tvg-id="{idx}" tvg-name="{item["titulo"]}" tvg-logo="{item.get("logo","")}" tvg-language="pt" tvg-type="{item["grupo"].lower()}" group-title="{group_title(item)}",{item["titulo"]}\n'
            )
            f.write(f"{item['stream_url']}\n")

def gerar_json(itens):
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False, indent=2)

def main():
    itens = []

    with open(INPUT, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if is_excluded(row["titulo"]):
                continue
            row = classify(row)
            itens.append(row)

    grupos = agrupar_por_titulo(itens)

    selecionados = []
    for grupo in grupos.values():
        selecionados.append(selecionar_melhor_stream(grupo))

    validos = [
        i for i in selecionados
        if i.get("stream_url") and i["stream_url"].startswith("http")
    ]

    gerar_m3u(validos)
    gerar_json(validos)

    print(f"Finalizado: {len(validos)} itens válidos")

if __name__ == "__main__":
    main()
