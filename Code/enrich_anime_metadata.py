import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

INPUT_JSON = "web/catalog.json"
OUTPUT_JSON = "web/catalog.json"
CACHE_FILE = "logs/anime_metadata_cache.json"
TIMEOUT = 15
REQUEST_DELAY = 0.8
MAX_ITEMS_PER_RUN = 120


def clean_title(title):
    text = title or ""
    text = re.sub(r"\b(?:ep|epis[oó]dio|episodio|episode)\s*\.?\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"\b(?:temporada|season)\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"\b\d{1,4}\b$", "", text)
    text = re.sub(r"[\[\](){}|_]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or title or "Anime"


def load_cache():
    if not Path(CACHE_FILE).exists():
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    Path(CACHE_FILE).parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def buscar_jikan(nome):
    query = quote(nome)
    url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or []
    if not data:
        return None

    anime = data[0]
    images = anime.get("images") or {}
    jpg = images.get("jpg") or {}

    return {
        "logo": jpg.get("large_image_url") or jpg.get("image_url") or "",
        "description": anime.get("synopsis") or "",
        "rating": anime.get("score") or "",
        "mal_id": anime.get("mal_id") or "",
        "canonical_title": anime.get("title") or nome,
    }


def enrich_item(item, cache):
    if not item.get("isAnime"):
        return item, False

    title = clean_title(item.get("title") or item.get("titulo"))
    key = title.lower()

    if key not in cache:
        meta = buscar_jikan(title)
        cache[key] = meta or {}
        time.sleep(REQUEST_DELAY)

    meta = cache.get(key) or {}
    if not meta:
        return item, False

    changed = False
    for field in ["logo", "description", "rating"]:
        if meta.get(field) and not item.get(field):
            item[field] = meta[field]
            changed = True

    if meta.get("canonical_title"):
        item["metadataTitle"] = meta["canonical_title"]
    if meta.get("mal_id"):
        item["metadataId"] = meta["mal_id"]

    return item, changed


def main():
    if not Path(INPUT_JSON).exists():
        print(f"Arquivo não encontrado: {INPUT_JSON}")
        return

    with open(INPUT_JSON, encoding="utf-8") as f:
        items = json.load(f)

    cache = load_cache()
    changed_count = 0
    processed = 0

    for item in items:
        if not item.get("isAnime"):
            continue
        if processed >= MAX_ITEMS_PER_RUN:
            break
        try:
            item, changed = enrich_item(item, cache)
            processed += 1
            if changed:
                changed_count += 1
        except Exception as e:
            print(f"Falha ao enriquecer {item.get('title')}: {e}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    save_cache(cache)
    print(f"Enriquecimento concluído. Processados: {processed}. Alterados: {changed_count}.")


if __name__ == "__main__":
    main()
