import csv
import re
from pathlib import Path

import requests

SOURCE_FILE = "sources/vod_playlist_sources.csv"
OUTPUT_FILE = "sources/vod_playlist_items.csv"
TIMEOUT = 35
VALID_GROUPS = {"Filmes", "Series"}


def normalizar_grupo(value):
    raw = (value or "").strip().lower()
    if raw in ["filme", "filmes", "movie", "movies"]:
        return "Filmes"
    if raw in ["serie", "série", "series", "séries", "show", "shows"]:
        return "Series"
    return value.strip() if value else ""


def clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def get_attr(line, attr):
    match = re.search(rf'{attr}="([^"]*)"', line)
    return match.group(1).strip() if match else ""


def parse_m3u(text, grupo_padrao, categoria_padrao, fonte):
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
                "grupo": grupo_padrao,
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


def ensure_source_template():
    Path(SOURCE_FILE).parent.mkdir(parents=True, exist_ok=True)
    if Path(SOURCE_FILE).exists():
        return

    rows = [
        {
            "nome": "vod-org-public-domain",
            "grupo": "Filmes",
            "categoria": "Clássicos",
            "url": "https://vod-org.github.io/vod/index.m3u8",
            "ativo": "true",
        },
        {
            "nome": "m3u8-xtream-trending-series",
            "grupo": "Series",
            "categoria": "Trending",
            "url": "https://aymrgknetzpucldhpkwm.supabase.co/storage/v1/object/public/tmdb/trending-series.m3u",
            "ativo": "false",
        },
        {
            "nome": "m3u8-xtream-top-movies",
            "grupo": "Filmes",
            "categoria": "Top Movies",
            "url": "https://aymrgknetzpucldhpkwm.supabase.co/storage/v1/object/public/tmdb/top-movies.m3u",
            "ativo": "false",
        },
        {
            "nome": "m3u8-xtream-action-movies",
            "grupo": "Filmes",
            "categoria": "Ação",
            "url": "https://aymrgknetzpucldhpkwm.supabase.co/storage/v1/object/public/tmdb/action-movies.m3u",
            "ativo": "false",
        },
        {
            "nome": "m3u8-xtream-adventure-movies",
            "grupo": "Filmes",
            "categoria": "Aventura",
            "url": "https://aymrgknetzpucldhpkwm.supabase.co/storage/v1/object/public/tmdb/adventure-movies.m3u",
            "ativo": "false",
        },
    ]
    with open(SOURCE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nome", "grupo", "categoria", "url", "ativo"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Modelo de fontes criado em {SOURCE_FILE}")


def load_sources():
    ensure_source_template()
    with open(SOURCE_FILE, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))


def import_source(row):
    ativo = (row.get("ativo") or "").strip().lower() == "true"
    if not ativo:
        return []

    nome = clean(row.get("nome") or "vod-playlist")
    grupo = normalizar_grupo(row.get("grupo"))
    categoria = clean(row.get("categoria") or "Geral")
    url = clean(row.get("url"))

    if grupo not in VALID_GROUPS:
        print(f"Fonte ignorada por grupo inválido: {nome}")
        return []
    if not url.startswith("http"):
        print(f"Fonte ignorada por URL inválida: {nome}")
        return []

    print(f"Importando VOD playlist: {nome} ({grupo} | {categoria})")
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return parse_m3u(response.text, grupo, categoria, f"vod-playlist:{nome}")


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
        key = (item["grupo"], item["titulo"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    write_csv(unique)


if __name__ == "__main__":
    main()
