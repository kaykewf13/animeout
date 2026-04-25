import csv
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

SOURCE_FILE = "sources/vod_playlist_sources.csv"
OUTPUT_FILE = "sources/vod_playlist_items.csv"
CACHE_FILE = "cache/vod_playlist_items_cache.json"
TIMEOUT = 35
VALID_GROUPS = {"Filmes", "Series"}
STREAM_RE = re.compile(r'https?://[^\s"\'<>]+?\.(?:m3u8|mp4|ts)(?:\?[^\s"\'<>]*)?', re.I)

DEFAULT_SOURCES = [
    {"nome":"vod-org-public-domain","grupo":"Filmes","categoria":"Clássicos","url":"https://vod-org.github.io/vod/index.m3u8","ativo":"true","refresh":"weekly","tipo":"playlist"},
    {"nome":"drewlive-vod-authorized","grupo":"Filmes","categoria":"VOD Externo","url":"https://raw.githubusercontent.com/konanda-sg/DrewLive-1/main/DrewLiveVOD.m3u8","ativo":"true","refresh":"manual","tipo":"playlist"},
    {"nome":"m3u8-xtream-trending-series","grupo":"Series","categoria":"Trending","url":"https://aymrgknetzpucldhpkwm.supabase.co/storage/v1/object/public/tmdb/trending-series.m3u","ativo":"false","refresh":"manual","tipo":"playlist"},
    {"nome":"m3u8-xtream-top-movies","grupo":"Filmes","categoria":"Top Movies","url":"https://aymrgknetzpucldhpkwm.supabase.co/storage/v1/object/public/tmdb/top-movies.m3u","ativo":"false","refresh":"manual","tipo":"playlist"},
]


def clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def normalizar_grupo(value):
    raw = (value or "").strip().lower()
    if raw in ["filme", "filmes", "movie", "movies"]:
        return "Filmes"
    if raw in ["serie", "série", "series", "séries", "show", "shows"]:
        return "Series"
    return value.strip() if value else ""


def get_attr(line, attr):
    match = re.search(rf'{attr}="([^"]*)"', line)
    return match.group(1).strip() if match else ""


def guess_title_from_url(url):
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    name = re.sub(r"\.(m3u8|mp4|ts)$", "", name, flags=re.I)
    name = re.sub(r"[_\-.]+", " ", name)
    return clean(name).title() or "VOD Externo"


def parse_m3u(text, grupo_padrao, categoria_padrao, fonte, base_url=""):
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
            current = {"grupo": grupo_padrao, "categoria": clean(group_title) or categoria_padrao, "titulo": title, "url": "", "logo": logo, "fonte": fonte}
        elif (line.startswith("http") or line.startswith("/")) and current:
            current["url"] = urljoin(base_url, line)
            items.append(current)
            current = None
    return items


def parse_external_links(text, grupo_padrao, categoria_padrao, fonte):
    items = []
    seen = set()
    for url in STREAM_RE.findall(text):
        if url in seen:
            continue
        seen.add(url)
        items.append({"grupo": grupo_padrao, "categoria": categoria_padrao, "titulo": guess_title_from_url(url), "url": url, "logo": "", "fonte": fonte})
    return items


def write_sources(rows):
    fields = ["nome", "grupo", "categoria", "url", "ativo", "refresh", "tipo"]
    with open(SOURCE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def ensure_source_template():
    Path(SOURCE_FILE).parent.mkdir(parents=True, exist_ok=True)
    if not Path(SOURCE_FILE).exists():
        write_sources(DEFAULT_SOURCES)
        print(f"Modelo de fontes criado em {SOURCE_FILE}")
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
        write_sources(rows)
        print(f"Fontes padrão adicionadas em {SOURCE_FILE}")


def load_sources():
    ensure_source_template()
    with open(SOURCE_FILE, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))


def load_cache():
    if not Path(CACHE_FILE).exists():
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    Path(CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def should_refresh(row, cached_items):
    refresh = (row.get("refresh") or "manual").strip().lower()
    if not cached_items:
        return True
    return refresh in ["always", "daily"]


def import_source(row, cache):
    ativo = (row.get("ativo") or "").strip().lower() == "true"
    if not ativo:
        return []
    nome = clean(row.get("nome") or "vod-playlist")
    grupo = normalizar_grupo(row.get("grupo"))
    categoria = clean(row.get("categoria") or "Geral")
    url = clean(row.get("url"))
    tipo = (row.get("tipo") or "playlist").strip().lower()
    if grupo not in VALID_GROUPS or not url.startswith("http"):
        print(f"Fonte ignorada: {nome}")
        return []
    cached = cache.get(nome, {}).get("items", [])
    if not should_refresh(row, cached):
        print(f"Usando cache VOD estável: {nome} ({len(cached)} item(ns))")
        return cached
    print(f"Importando VOD autorizado: {nome} ({grupo} | {categoria} | {tipo})")
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    text = response.text
    if tipo in ["page", "html", "external_links"]:
        items = parse_external_links(text, grupo, categoria, f"vod-authorized:{nome}")
    else:
        items = parse_m3u(text, grupo, categoria, f"vod-playlist:{nome}", base_url=url)
        if not items:
            items = parse_external_links(text, grupo, categoria, f"vod-authorized:{nome}")
    cache[nome] = {"items": items}
    return items


def write_csv(items):
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    fields = ["grupo", "categoria", "titulo", "url", "logo", "fonte"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
    print(f"Arquivo gerado: {OUTPUT_FILE} ({len(items)} item(ns))")


def main():
    cache = load_cache()
    all_items = []
    for row in load_sources():
        try:
            all_items.extend(import_source(row, cache))
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
    save_cache(cache)


if __name__ == "__main__":
    main()
