import csv
import re
from pathlib import Path

import requests

SOURCE_FILE = "sources/channel_playlist_sources.csv"
OUTPUT_FILE = "sources/channel_playlist_items.csv"
TIMEOUT = 35

DEFAULT_SOURCES = [
    {
        "nome": "free-tv-br",
        "categoria": "Brasil",
        "url": "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
        "ativo": "true",
    },
    {
        "nome": "ibert-jp",
        "categoria": "Japão",
        "url": "https://m3u.ibert.me/jp.m3u",
        "ativo": "false",
    },
]


def clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def get_attr(line, attr):
    match = re.search(rf'{attr}="([^"]*)"', line)
    return match.group(1).strip() if match else ""


def parse_m3u(text, categoria_padrao, fonte):
    items = []
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            title = clean(line.split(",", 1)[-1] if "," in line else "Sem título")
            group_title = get_attr(line, "group-title") or categoria_padrao
            logo = get_attr(line, "tvg-logo")
            tvg_name = get_attr(line, "tvg-name")
            if tvg_name and title.lower() in ["", "sem título", "sem titulo"]:
                title = tvg_name
            current = {
                "grupo": "Canais",
                "categoria": clean(group_title) or categoria_padrao,
                "titulo": title,
                "url": "",
                "logo": logo,
                "fonte": fonte,
            }
        elif line.startswith("http") and current:
            current["url"] = line
            items.append(current)
            current = None
    return items


def ensure_source_file():
    Path(SOURCE_FILE).parent.mkdir(parents=True, exist_ok=True)
    if not Path(SOURCE_FILE).exists():
        with open(SOURCE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["nome", "categoria", "url", "ativo"])
            writer.writeheader()
            writer.writerows(DEFAULT_SOURCES)
        print(f"Modelo criado em {SOURCE_FILE}")
        return

    with open(SOURCE_FILE, encoding="utf-8", errors="ignore") as f:
        rows = list(csv.DictReader(f))
    existing = {r.get("nome") for r in rows}
    changed = False
    for row in DEFAULT_SOURCES:
        if row["nome"] not in existing:
            rows.append(row)
            changed = True
    if changed:
        with open(SOURCE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["nome", "categoria", "url", "ativo"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Fontes padrão adicionadas em {SOURCE_FILE}")


def load_sources():
    ensure_source_file()
    with open(SOURCE_FILE, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))


def import_source(row):
    ativo = (row.get("ativo") or "").strip().lower() == "true"
    if not ativo:
        return []
    nome = clean(row.get("nome") or "channel-playlist")
    categoria = clean(row.get("categoria") or "TV")
    url = clean(row.get("url"))
    if not url.startswith("http"):
        print(f"Fonte ignorada por URL inválida: {nome}")
        return []
    print(f"Importando canais live: {nome} ({categoria})")
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return parse_m3u(response.text, categoria, f"channel-playlist:{nome}")


def write_csv(items):
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    fields = ["grupo", "categoria", "titulo", "url", "logo", "fonte"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
    print(f"Arquivo gerado: {OUTPUT_FILE} ({len(items)} item(ns))")


def main():
    all_items = []
    for row in load_sources():
        try:
            all_items.extend(import_source(row))
        except Exception as e:
            print(f"Erro ao importar {row.get('nome')}: {e}")
    seen = set()
    unique = []
    for item in all_items:
        key = (item["titulo"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    write_csv(unique)


if __name__ == "__main__":
    main()
