import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import requests

OUTPUT_FILE = "sources/external_vod_sources.csv"

SOURCES_VOD = [
    # group-title geralmente traz nome do anime, links MP4/HLS via fontes públicas configuradas
    "https://raw.githubusercontent.com/alzamer2/iptv/main/Anime.m3u",

    # Animes PT-BR com episódios
    "https://raw.githubusercontent.com/L3uS-IPTV/Animes/main/animes.m3u",
    "https://raw.githubusercontent.com/Iptv-Animes/AutoUpdate/main/lista.m3u",
]

TIMEOUT = 30

TYPE_KEYWORDS = [
    ("Hentai", ["hentai", "adult", "18+", "xxx"]),
    ("Ecchi", ["ecchi"]),
    ("Isekai", ["isekai", "tensei", "re:zero", "overlord", "slime", "konosuba"]),
    ("Shounen", ["shounen", "shonen", "naruto", "one piece", "dragon ball", "bleach", "jujutsu", "kimetsu", "hunter x hunter", "black clover"]),
    ("Seinen", ["seinen", "berserk", "vinland", "monster", "tokyo ghoul", "parasyte", "hellsing"]),
    ("Mecha", ["mecha", "gundam", "evangelion", "code geass", "darling in the franxx"]),
    ("Romance", ["romance", "love", "kaguya", "horimiya", "toradora", "komi", "clannad"]),
    ("Comedia", ["comedia", "comedy", "gintama", "saiki", "nichijou"]),
    ("Fantasia", ["fantasia", "fantasy", "frieren", "magi", "fairy tail", "fate"]),
    ("Terror", ["terror", "horror", "junji", "another", "corpse party"]),
    ("Esporte", ["sport", "esporte", "haikyuu", "kuroko", "blue lock", "slam dunk"]),
]

EPISODE_PATTERNS = [
    r"(?:ep|epis[oó]dio|episodio|episode)\s*\.?\s*(\d+)",
    r"\b(\d{1,4})\b",
]


def clean_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_anime_name(value):
    text = clean_text(value)
    text = re.sub(r"\b(?:ep|epis[oó]dio|episodio|episode)\s*\.?\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"\b(?:temporada|season)\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"\b\d{1,4}\b$", "", text).strip(" -_|[]()")
    return clean_text(text) or "Anime"


def extract_episode_number(title):
    lower = title.lower()
    for pattern in EPISODE_PATTERNS:
        matches = re.findall(pattern, lower, flags=re.I)
        if matches:
            try:
                return int(matches[-1])
            except Exception:
                pass
    return None


def detect_type(title, group_title):
    text = f"{title} {group_title}".lower()
    for tipo, keywords in TYPE_KEYWORDS:
        if any(k in text for k in keywords):
            return tipo
    return "Anime"


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
                group_title = clean_text(group_match.group(1)) or "Anime"
            if logo_match:
                logo = logo_match.group(1).strip()

            anime_name = normalize_anime_name(group_title if group_title.lower() != "anime" else title)
            tipo = detect_type(title, group_title)
            ep = extract_episode_number(title)

            current = {
                "grupo": "Series",
                "tipo": tipo,
                "anime": anime_name,
                "episodio": ep or "",
                "categoria": "",  # preenchido após contagem final
                "titulo": clean_text(title),
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


def apply_episode_counts(items):
    counts = Counter(item["anime"] for item in items)
    for item in items:
        qtd = counts[item["anime"]]
        # Ordem pedida: tipo do anime antes do nome e quantidade de episódios.
        item["categoria"] = f"{item['tipo']} | {item['anime']} | {qtd} eps"
    return items


def write_csv(items):
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    fields = ["grupo", "categoria", "titulo", "url", "logo", "fonte", "tipo", "anime", "episodio"]

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
            print(f"Erro ao baixar {url}: {e}")

    unique = []
    seen = set()
    for item in all_items:
        key = (item["titulo"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    unique = apply_episode_counts(unique)
    write_csv(unique)


if __name__ == "__main__":
    main()
