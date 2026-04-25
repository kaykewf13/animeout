import csv
import re
from pathlib import Path

import requests

SOURCES = [
    {
        "grupo": "Filmes",
        "categoria": "Movies",
        "url": "https://iptv-org.github.io/iptv/categories/movies.m3u",
    },
    {
        "grupo": "Series",
        "categoria": "Series",
        "url": "https://iptv-org.github.io/iptv/categories/series.m3u",
    },
]

OUTPUT = "sources/iptv_org_vod.csv"
TIMEOUT = 30


def parse_m3u(text, grupo, categoria_padrao):
    items = []
    current = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            title = line.split(",", 1)[-1].strip() if "," in line else "Sem título"
            group_title = categoria_padrao
            logo = ""
            tvg_id = ""

            group_match = re.search(r'group-title="([^"]+)"', line)
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            id_match = re.search(r'tvg-id="([^"]+)"', line)

            if group_match:
                group_title = group_match.group(1).strip() or categoria_padrao
            if logo_match:
                logo = logo_match.group(1).strip()
            if id_match:
                tvg_id = id_match.group(1).strip()

            current = {
                "grupo": grupo,
                "categoria": group_title,
                "titulo": title,
                "url": "",
                "logo": logo,
                "tvg_id": tvg_id,
                "fonte": "iptv-org",
            }
        elif line.startswith("http") and current:
            current["url"] = line
            items.append(current)
            current = None

    return items


def fetch_source(source):
    print(f"Baixando {source['grupo']} de {source['url']}")
    response = requests.get(source["url"], timeout=TIMEOUT)
    response.raise_for_status()
    return parse_m3u(response.text, source["grupo"], source["categoria"])


def write_csv(items, output=OUTPUT):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    fields = ["grupo", "categoria", "titulo", "url", "logo", "tvg_id", "fonte"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
    print(f"Arquivo gerado: {output} ({len(items)} item(ns))")


def main():
    all_items = []
    for source in SOURCES:
        try:
            all_items.extend(fetch_source(source))
        except Exception as e:
            print(f"Erro ao importar {source['grupo']}: {e}")

    # Deduplicação por URL + título
    unique = []
    seen = set()
    for item in all_items:
        key = (item["titulo"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    write_csv(unique)


if __name__ == "__main__":
    main()
