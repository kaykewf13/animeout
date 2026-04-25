import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

OUTPUT = "sources/plex_vod.csv"


def load_json(source):
    if source.startswith("http"):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return response.json()

    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


def first_title(meta):
    titles = meta.get("titles") or []
    for preferred in ["pt", "pt-BR", "en"]:
        for item in titles:
            if (item.get("language") or "").lower() == preferred.lower():
                return item.get("title") or "Sem título"
    if titles:
        return titles[0].get("title") or "Sem título"
    return meta.get("title") or meta.get("name") or "Sem título"


def first_description(meta):
    descs = meta.get("descriptions") or []
    for preferred in ["pt", "pt-BR", "en"]:
        for item in descs:
            if (item.get("language") or "").lower() == preferred.lower():
                return item.get("description") or ""
    if descs:
        return descs[0].get("description") or ""
    return meta.get("description") or ""


def best_image(meta):
    images = meta.get("images") or []
    if not images:
        return ""
    for kind in ["coverPoster", "coverArt"]:
        for image in images:
            if image.get("type") == kind and image.get("url"):
                return image["url"]
    return images[0].get("url", "")


def availability_url(meta):
    avails = meta.get("availabilities") or []
    for item in avails:
        url = item.get("url") or item.get("stream_url") or item.get("video_url")
        if url and url.startswith("http"):
            return url
    return meta.get("url") or meta.get("stream_url") or ""


def group_for_type(meta_type):
    raw = (meta_type or "").lower()
    if raw == "movie":
        return "Filmes"
    if raw in ["show", "season", "episode", "series"]:
        return "Series"
    return "Series"


def normalize_item(meta):
    meta_type = meta.get("type") or meta.get("content_type") or "show"
    grupo = group_for_type(meta_type)
    genres = meta.get("genre") or meta.get("genres") or ["Geral"]
    if isinstance(genres, str):
        genres = [genres]
    categoria = genres[0] if genres else "Geral"
    titulo = first_title(meta)
    url = availability_url(meta)
    logo = best_image(meta)
    description = first_description(meta)
    rating = ""
    ratings = meta.get("ratings") or []
    if ratings:
        rating = ratings[0].get("rating", "")

    return {
        "grupo": grupo,
        "categoria": categoria or "Geral",
        "titulo": titulo,
        "url": url,
        "logo": logo,
        "description": description,
        "rating": rating,
        "fonte": "plex-vod",
    }


def extract_metadata(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("metadata"), list):
            return payload["metadata"]
        if isinstance(payload.get("items"), list):
            return payload["items"]
        if isinstance(payload.get("results"), list):
            return payload["results"]
    return []


def write_csv(items, output):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    fields = ["grupo", "categoria", "titulo", "url", "logo", "description", "rating", "fonte"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
    print(f"Arquivo gerado: {output} ({len(items)} item(ns))")


def main():
    parser = argparse.ArgumentParser(description="Importa catálogo no padrão Plex VOD para sources/plex_vod.csv")
    parser.add_argument("source", help="Arquivo JSON local ou URL JSON do catálogo VOD")
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()

    payload = load_json(args.source)
    metadata = extract_metadata(payload)
    items = []

    for meta in metadata:
        item = normalize_item(meta)
        if not item["url"]:
            continue
        parsed = urlparse(item["url"])
        if parsed.scheme not in ["http", "https"]:
            continue
        # Regra dura: movie vira Filmes; show/season/episode vira Series. Nunca Canais.
        items.append(item)

    write_csv(items, args.output)


if __name__ == "__main__":
    main()
