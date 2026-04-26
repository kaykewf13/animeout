import csv
import json
import os
import re
from pathlib import Path

# ------------------------
# CONFIG
# ------------------------

SOURCES = [
    "sources/catalog.csv",
    "sources/external_vod_sources.csv",
    "sources/vod_playlist_items.csv",
    "sources/github_vod_discovered.csv",
    "sources/channel_playlist_items.csv",
    "sources/iptv_org_vod.csv"
]

OUTPUT_M3U = "valid_links.m3u"
OUTPUT_CANAIS = "output/canais.m3u"
OUTPUT_SERIES = "output/series.m3u"
OUTPUT_FILMES = "output/filmes.m3u"

# ------------------------
# UTILS
# ------------------------

def ensure_dirs():
    Path("output").mkdir(exist_ok=True)

def clean_title(title):
    title = title.lower()
    title = re.sub(r's\d+e\d+', '', title)
    title = re.sub(r'(ep|episodio|episode)\s*\d+', '', title)
    title = re.sub(r'[^a-z0-9 ]', ' ', title)
    return " ".join(title.split())

def identificar_obra(title):
    return " ".join(clean_title(title).split()[:4])

def get_ext(url):
    url = url.split("?")[0]
    if "." in url:
        return url.split(".")[-1]
    return ""

# ------------------------
# CLASSIFICAÇÃO
# ------------------------

def detectar_tipo(url, titulo):
    url = url.lower()
    titulo = titulo.lower()

    if any(x in url for x in ["pluto", "rakuten", "live"]):
        return "CANAIS"

    ext = get_ext(url)

    if ext == "ts":
        return "CANAIS"

    if ext == "mp4":
        return "FILMES"

    if ext == "m3u8":
        if any(x in titulo for x in ["ep", "episodio", "s01"]):
            return "SERIES"
        return "CANAIS"

    return "INVALIDO"

# ------------------------
# LEITURA
# ------------------------

def read_sources():
    items = []

    for source in SOURCES:
        if not os.path.exists(source):
            continue

        with open(source, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                url = row.get("stream_url") or row.get("url")
                titulo = row.get("titulo") or row.get("title") or "Sem titulo"

                if not url or not url.startswith("http"):
                    continue

                tipo = detectar_tipo(url, titulo)

                if tipo == "INVALIDO":
                    continue

                items.append({
                    "titulo": titulo,
                    "url": url,
                    "tipo": tipo,
                    "obra": identificar_obra(titulo)
                })

    return items

# ------------------------
# CLUSTER
# ------------------------

def cluster_items(items):
    clusters = {}

    for item in items:
        key = (item["tipo"], item["obra"])

        if key not in clusters:
            clusters[key] = []

        clusters[key].append(item)

    return clusters

# ------------------------
# EXPORTAÇÃO
# ------------------------

def write_m3u(items, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in items:
            f.write(f'#EXTINF:-1 group-title="{item["tipo"]}",{item["titulo"]}\n')
            f.write(f'{item["url"]}\n')

def export_all(clusters):
    all_items = []
    canais = []
    series = []
    filmes = []

    for (tipo, obra), itens in clusters.items():
        for item in itens:
            all_items.append(item)

            if tipo == "CANAIS":
                canais.append(item)
            elif tipo == "SERIES":
                series.append(item)
            elif tipo == "FILMES":
                filmes.append(item)

    write_m3u(all_items, OUTPUT_M3U)
    write_m3u(canais, OUTPUT_CANAIS)
    write_m3u(series, OUTPUT_SERIES)
    write_m3u(filmes, OUTPUT_FILMES)

# ------------------------
# MAIN
# ------------------------

def main():
    print("🚀 Iniciando pipeline IPTV...")

    ensure_dirs()

    items = read_sources()
    print(f"Itens carregados: {len(items)}")

    clusters = cluster_items(items)
    print(f"Clusters gerados: {len(clusters)}")

    export_all(clusters)

    print("✅ Pipeline finalizado com sucesso!")

# ------------------------

if __name__ == "__main__":
    main()