import csv
import re
from pathlib import Path
import requests

OUTPUT_FILE = "sources/external_vod_sources.csv"

SOURCES_VOD = [
    # Anime CDN (categoria = nome do anime)
    "https://raw.githubusercontent.com/alzamer2/iptv/main/Anime.m3u",

    # Animes PT-BR
    "https://raw.githubusercontent.com/L3uS-IPTV/Animes/main/animes.m3u",
    "https://raw.githubusercontent.com/Iptv-Animes/AutoUpdate/main/lista.m3u",
]

TIMEOUT = 30


def parse_m3u(text):
    items = []
    current = None

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            title = line.split(",", 1)[-1].strip() if "," in line else "Sem título"

            group_title = "Anime"
            logo = ""

            group_match = re.search(r'group-title="([^"]+)"', line)
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)

            if group_match:
                group_title = group_match.group(1).strip()

            if logo_match:
                logo = logo_match.group(1).strip()

            current = {
                "grupo": "Series",  # 🔥 FORÇA COMO SERIES
                "categoria": group_title,
                "titulo": title,
                "url": "",
                "logo": logo,
                "fonte": "external-anime",
            }

        elif line.startswith("http") and current:
            current["url"] = line
            items.append(current)
            current = None

    return items


def fetch_source(url):
    print(f"Baixando: {url}")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_m3u(r.text)


def write_csv(items):
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    fields = ["grupo", "categoria", "titulo", "url", "logo", "fonte"]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)

    print(f"Arquivo gerado: {OUTPUT_FILE} ({len(items)} itens)")


def main():
    all_items = []

    for url in SOURCES_VOD:
        try:
            all_items.extend(fetch_source(url))
        except Exception as e:
            print(f"Erro: {e}")

    # 🔥 Deduplicação forte
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