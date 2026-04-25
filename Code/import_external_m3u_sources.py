import csv
import re
from pathlib import Path

import requests

SOURCE_FILE = "sources/external_m3u_sources.csv"
OUTPUT_FILE = "sources/external_vod_sources.csv"
TIMEOUT = 30
VALID_GROUPS = {"Canais", "Filmes", "Series"}


def normalizar_grupo(value):
    raw = (value or "").strip().lower()
    mapa = {
        "canais": "Canais", "canal": "Canais", "live": "Canais", "lives": "Canais",
        "filmes": "Filmes", "filme": "Filmes", "movies": "Filmes", "movie": "Filmes",
        "series": "Series", "séries": "Series", "serie": "Series", "série": "Series", "shows": "Series",
    }
    return mapa.get(raw, value.strip() if value else "")


def parse_m3u(text, grupo_padrao, categoria_padrao, fonte):
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
                "grupo": grupo_padrao,
                "categoria": group_title,
                "titulo": title,
                "url": "",
                "logo": logo,
                "tvg_id": tvg_id,
                "fonte": fonte,
            }
        elif line.startswith("http") and current:
            current["url"] = line
            items.append(current)
            current = None

    return items


def carregar_sources():
    if not Path(SOURCE_FILE).exists():
        Path(SOURCE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(SOURCE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["nome", "grupo", "categoria", "url", "ativo"])
            writer.writeheader()
            writer.writerow({
                "nome": "exemplo",
                "grupo": "Series",
                "categoria": "Anime",
                "url": "https://example.com/lista.m3u",
                "ativo": "false",
            })
        print(f"Modelo criado em {SOURCE_FILE}. Adicione fontes autorizadas e marque ativo=true.")
        return []

    with open(SOURCE_FILE, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))


def baixar_source(row):
    ativo = (row.get("ativo") or "").strip().lower() == "true"
    if not ativo:
        return []

    nome = (row.get("nome") or "external").strip() or "external"
    grupo = normalizar_grupo(row.get("grupo"))
    categoria = (row.get("categoria") or "Geral").strip() or "Geral"
    url = (row.get("url") or "").strip()

    if grupo not in VALID_GROUPS or not url.startswith("http"):
        print(f"Fonte ignorada: {nome}")
        return []

    print(f"Importando fonte externa: {nome} ({grupo} | {categoria})")
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return parse_m3u(response.text, grupo, categoria, f"external:{nome}")


def write_csv(items):
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    fields = ["grupo", "categoria", "titulo", "url", "logo", "tvg_id", "fonte"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
    print(f"Arquivo gerado: {OUTPUT_FILE} ({len(items)} item(ns))")


def main():
    rows = carregar_sources()
    items = []
    for row in rows:
        try:
            items.extend(baixar_source(row))
        except Exception as e:
            print(f"Erro ao importar fonte {row.get('nome')}: {e}")

    seen = set()
    unique = []
    for item in items:
        key = (item["grupo"], item["titulo"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    write_csv(unique)


if __name__ == "__main__":
    main()
