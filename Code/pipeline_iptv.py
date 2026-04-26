import csv
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except Exception:
    requests = None

CATALOG_SOURCES = [
    "sources/catalog.csv",
    "sources/external_vod_sources.csv",
    "sources/vod_playlist_items.csv",
    "sources/github_vod_discovered.csv",
    "sources/channel_playlist_items.csv",
    "sources/iptv_org_vod.csv",
    "sources/plex_vod.csv",
]

OUTPUT_M3U = "valid_links.m3u"
OUTPUT_MASTER = "output/master_playlist.m3u"
OUTPUT_CANAIS = "output/canais.m3u"
OUTPUT_SERIES = "output/series.m3u"
OUTPUT_FILMES = "output/filmes.m3u"
OUTPUT_JSON = "web/catalog.json"
OUTPUT_CLUSTERED_JSON = "web/catalog_clustered.json"
INVALID_CSV = "invalid_links.csv"
SUMMARY_CSV = "logs/catalog_summary.csv"
SUGOI_CACHE = "cache/sugoi_anime_cache.json"
SUGOI_BASE_URL = "https://kaykewf13.github.io/SUGOIAPI/api/animes?search="

VALID_GROUPS = {"Canais", "Filmes", "Series"}
STREAM_EXTENSIONS = (".m3u8", ".mp4", ".ts")

ANIME_KEYWORDS = [
    "anime", "animes", "naruto", "one piece", "dragon ball", "bleach", "jujutsu", "kimetsu",
    "demon slayer", "attack on titan", "shingeki", "hunter x hunter", "black clover", "frieren",
    "isekai", "shounen", "shonen", "seinen", "mecha", "otaku", "gundam", "evangelion",
]
ADULT_KEYWORDS = ["adult", "adulto", "18+", "hentai", "xxx", "porn", "erotic", "baddiehub"]
EXCLUDE_KEYWORDS = ["yaoi", "boys love", "boyslove", "shounen ai", "shonen ai"]
SERIES_HINTS = ["series", "serie", "série", "episode", "episodio", "episódio", "temporada", "season", "s01", "s02", "anime", "animes", "dorama", "novela"]
MOVIE_HINTS = ["movie", "movies", "filme", "filmes", "cinema", "film", "/movies/", " movie "]
LIVE_HINTS = ["pluto", "rakuten", "wurl", "amagi", "stitch", "linear", "live", "channel", "free-tv", "iptv-org", "playlist.m3u8", "master.m3u8"]
VOD_HINTS = ["vod", "drewlivevod", "external-anime", "episode", "episodio", "s01e", "s02e", "/series/", "/movies/", ".mp4"]

INVALID_CATEGORY_VALUES = {"", "geral", "general", "vod", "github vod", "other", "others", "undefined", "unknown", "brasil", "brazil", "usa", "uk", "belgium", "france", "germany", "italy", "spain", "portugal", "japan", "korea"}

DEFAULT_POSTERS = {
    "Canais": "https://placehold.co/600x900/111218/e7e9ee?text=Canais",
    "Filmes": "https://placehold.co/600x900/111218/e7e9ee?text=Filmes",
    "Series": "https://placehold.co/600x900/111218/e7e9ee?text=Series",
    "Anime": "https://placehold.co/600x900/111218/e23b3b?text=Anime",
    "Adultos": "https://placehold.co/600x900/111218/e23b3b?text=18%2B",
}

CHANNEL_RULES = [
    ("Pluto TV", ["pluto"]),
    ("Rakuten", ["rakuten"]),
    ("Samsung TV Plus", ["samsung"]),
    ("Noticias", ["news", "noticias", "cnn", "bbc", "globonews", "record news", "jovem pan"]),
    ("Esportes", ["espn", "sport", "sports", "futebol", "soccer", "premiere", "combate", "ufc", "nba", "nfl", "tennis"]),
    ("Infantil", ["kids", "infantil", "cartoon", "disney", "nick", "toon"]),
    ("Filmes e Series", ["movie", "movies", "cinema", "hbo", "telecine", "cinemax", "tnt", "warner", "sony", "axn", "space", "amc", "series"]),
    ("Adultos", ADULT_KEYWORDS),
]

MOVIE_RULES = [
    ("Adultos", ADULT_KEYWORDS),
    ("Lancamentos", ["lancamento", "lançamento", "release", "2026", "2025", "new"]),
    ("Anime", ANIME_KEYWORDS),
    ("Animacao", ["animation", "animacao", "animação", "cartoon"]),
    ("Acao", ["action", "acao", "ação", "fight", "martial"]),
    ("Aventura", ["adventure", "aventura"]),
    ("Comedia", ["comedy", "comedia", "comédia"]),
    ("Terror", ["horror", "terror"]),
    ("Suspense", ["thriller", "suspense"]),
    ("Drama", ["drama"]),
    ("Ficcao", ["sci-fi", "scifi", "ficcao", "ficção", "science fiction"]),
    ("Documentario", ["documentary", "documentario", "documentário"]),
    ("Classicos", ["classic", "classico", "clássico", "oldies"]),
]

SERIES_RULES = [
    ("Adultos", ADULT_KEYWORDS),
    ("Anime", ANIME_KEYWORDS),
    ("Doramas", ["dorama", "kdrama", "k-drama", "korean drama"]),
    ("Novelas", ["novela", "novelas"]),
    ("Netflix", ["netflix"]),
    ("Prime Video", ["prime video", "amazon prime"]),
    ("Disney+", ["disney", "disney+"]),
    ("Max", ["hbo max", "max"]),
    ("Globoplay", ["globoplay"]),
    ("Lancamentos", ["lancamento", "lançamento", "release", "2026", "2025", "new"]),
]


def ensure_dirs():
    for path in ["web", "output", "logs", "cache"]:
        Path(path).mkdir(parents=True, exist_ok=True)


def strip_accents(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "")) if not unicodedata.combining(c))


def text_blob(*values):
    return strip_accents(" ".join(str(v or "") for v in values)).lower()


def safe_text(value, max_len=160):
    text = strip_accents(value)
    text = text.replace("\ufeff", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = text.replace('"', "'").replace("`", "'")
    text = re.sub(r"[<>{}\[\]]", " ", text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def safe_group(value):
    text = safe_text(value, 90)
    text = re.sub(r"[;/\\:,]+", " - ", text)
    text = re.sub(r"[^A-Za-z0-9 +_.|\-]", " ", text)
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or "Geral"


def slug(value):
    value = strip_accents(value or "item").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "item"


def stream_ext(url):
    clean = (url or "").split("?")[0].lower()
    return clean.rsplit(".", 1)[-1] if "." in clean else ""


def is_stream_url(url):
    return (url or "").split("?")[0].lower().endswith(STREAM_EXTENSIONS)


def contains_any(text, terms):
    return any(term in text for term in terms)


def first_rule(text, rules):
    for label, terms in rules:
        if contains_any(text, terms):
            return label
    return None


def normalizar_grupo(value):
    raw = strip_accents(value or "").strip().lower()
    mapping = {
        "canais": "Canais", "canal": "Canais", "live": "Canais", "lives": "Canais",
        "filmes": "Filmes", "filme": "Filmes", "movies": "Filmes", "movie": "Filmes", "film": "Filmes",
        "series": "Series", "séries": "Series", "serie": "Series", "série": "Series", "shows": "Series",
    }
    return mapping.get(raw, value.strip() if value else "")


def normalizar_categoria(value):
    cat = safe_group(value or "Geral")
    return cat or "Geral"


def identificar_obra(titulo):
    t = strip_accents(titulo).lower()
    t = re.sub(r"\[[^\]]+\]", " ", t)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\bs\d{1,2}e\d{1,3}\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:ep|episodio|episodios|episode|capitulo|cap)\s*\.?\s*\d+\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:season|temporada)\s*\d+\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:1080p|720p|480p|360p|4k|hd|fhd|uhd|x264|x265|hevc|aac|dual audio|dub|dublado|legendado|sub)\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d{1,4}\b$", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(t.split()[:6]) or "item"


def clean_title(value):
    title = safe_text(value or "Sem titulo")
    title = re.sub(r"\s+", " ", title).strip(" -_|.")
    return title or "Sem titulo"


def episode_number(title):
    patterns = [r"S\d{1,2}E(\d{1,3})", r"(?:ep|episodio|episódio|episode|capitulo|cap)\s*\.?\s*(\d+)", r"\b(\d{1,4})\b$"]
    for pattern in patterns:
        m = re.search(pattern, title or "", flags=re.I)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return ""
    return ""


def load_sugoi_cache():
    if os.path.exists(SUGOI_CACHE):
        try:
            with open(SUGOI_CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_sugoi_cache(cache):
    with open(SUGOI_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def buscar_sugoi(nome, cache):
    key = slug(nome)
    if not key or key == "item":
        return None
    if key in cache:
        return cache[key]
    if requests is None:
        cache[key] = None
        return None
    try:
        response = requests.get(SUGOI_BASE_URL + quote(nome), timeout=6)
        if response.status_code != 200:
            cache[key] = None
            return None
        data = response.json()
        if not data:
            cache[key] = None
            return None
        anime = data[0] if isinstance(data, list) else data
        result = {
            "title": anime.get("title") or anime.get("name") or nome,
            "genres": anime.get("genres") or anime.get("generos") or [],
            "type": anime.get("type") or anime.get("tipo") or "",
            "status": anime.get("status") or "",
        }
        cache[key] = result
        return result
    except Exception:
        cache[key] = None
        return None


def detectar_tipo(grupo_original, titulo, categoria, fonte, source_file, url):
    ext = stream_ext(url)
    ctx = text_blob(grupo_original, titulo, categoria, fonte, source_file, url)
    if ext not in ["m3u8", "mp4", "ts"]:
        return "INVALIDO"
    if ext == "ts":
        return "CANAIS"
    if ext == "mp4":
        return "VOD"
    if "channel_playlist_items" in ctx or "iptv_org_vod" in ctx or contains_any(ctx, LIVE_HINTS):
        return "CANAIS"
    if "external_vod_sources" in ctx or "vod_playlist_items" in ctx or "github_vod_discovered" in ctx:
        if contains_any(ctx, VOD_HINTS) or contains_any(ctx, SERIES_HINTS + MOVIE_HINTS + ANIME_KEYWORDS):
            return "VOD"
    return "CANAIS"


def definir_grupo(tipo, grupo_original, titulo, categoria, fonte, source_file, url):
    if tipo == "CANAIS":
        return "Canais"
    if tipo == "VOD":
        ctx = text_blob(grupo_original, titulo, categoria, fonte, source_file, url)
        if contains_any(ctx, ANIME_KEYWORDS + SERIES_HINTS):
            return "Series"
        if contains_any(ctx, MOVIE_HINTS):
            return "Filmes"
        if grupo_original in ["Filmes", "Series"]:
            return grupo_original
        return "Series"
    return ""


def classificar_categoria(grupo, titulo, categoria, fonte, source_file, url, description, sugoi=None):
    ctx = text_blob(grupo, titulo, categoria, fonte, source_file, url, description)
    if contains_any(ctx, ADULT_KEYWORDS):
        return "Adultos"
    if grupo == "Canais":
        return first_rule(ctx, CHANNEL_RULES) or "Abertos"
    if grupo == "Filmes":
        return first_rule(ctx, MOVIE_RULES) or "Cinema"
    if grupo == "Series":
        if sugoi:
            genres = sugoi.get("genres") or []
            if genres:
                genre = safe_group(str(genres[0]))
                return f"Anime | {genre}" if genre else "Anime"
            return "Anime"
        return first_rule(ctx, SERIES_RULES) or "Lancamentos"
    return "Geral"


def should_enrich_anime(grupo, titulo, categoria, fonte, source_file):
    ctx = text_blob(grupo, titulo, categoria, fonte, source_file)
    return grupo == "Series" and contains_any(ctx, ANIME_KEYWORDS + ["external-anime", "anime.m3u", "animes.m3u"])


def default_logo(group, category):
    if category == "Adultos":
        return DEFAULT_POSTERS["Adultos"]
    if "Anime" in category:
        return DEFAULT_POSTERS["Anime"]
    return DEFAULT_POSTERS.get(group, DEFAULT_POSTERS["Series"])


def is_invalid_title(title):
    raw = strip_accents(title).lower().strip()
    if len(raw) < 2:
        return True
    return any(word in raw for word in ["test", "teste", "sample", "demo", "placeholder", "sem titulo", "sem título"])


def read_csv_source(path, sugoi_cache):
    valid, invalid = [], []
    if not os.path.exists(path):
        return valid, invalid
    with open(path, encoding="utf-8", errors="ignore") as f:
        rows = [line for line in f if line.strip() and not line.lstrip().startswith("#")]
    if not rows:
        return valid, invalid
    reader = csv.DictReader(rows)
    for row in reader:
        url = (row.get("stream_url") or row.get("url") or "").strip()
        titulo_raw = (row.get("titulo") or row.get("title") or row.get("tvg-name") or row.get("name") or "Sem titulo").strip()
        fonte = (row.get("fonte") or row.get("source") or path).strip()
        grupo_original = normalizar_grupo(row.get("grupo") or row.get("group") or "")
        categoria_raw = normalizar_categoria(row.get("categoria") or row.get("category") or row.get("group-title") or "Geral")
        description = (row.get("description") or row.get("descricao") or "").strip()
        logo = (row.get("logo") or row.get("tvg-logo") or "").strip()
        subtitle = (row.get("subtitle") or row.get("legenda") or "").strip()
        motivo = ""
        if not url.startswith("http"):
            motivo = "url_vazia_ou_invalida"
        elif not is_stream_url(url):
            motivo = "nao_e_stream_direto"
        tipo = detectar_tipo(grupo_original, titulo_raw, categoria_raw, fonte, path, url)
        grupo = definir_grupo(tipo, grupo_original, titulo_raw, categoria_raw, fonte, path, url)
        titulo = clean_title(titulo_raw)
        obra = identificar_obra(row.get("anime") or titulo)
        ep = row.get("episodio") or episode_number(titulo_raw)
        if tipo == "INVALIDO" or grupo not in VALID_GROUPS:
            motivo = motivo or "tipo_ou_grupo_invalido"
        if is_invalid_title(titulo):
            motivo = motivo or "titulo_invalido_ou_teste"
        if contains_any(text_blob(titulo, categoria_raw, description), EXCLUDE_KEYWORDS):
            motivo = motivo or "conteudo_excluido_yaoi_bl"
        sugoi = None
        if not motivo and should_enrich_anime(grupo, titulo, categoria_raw, fonte, path):
            sugoi = buscar_sugoi(obra, sugoi_cache)
            if sugoi and sugoi.get("title"):
                obra = identificar_obra(sugoi.get("title"))
        iptv_categoria = classificar_categoria(grupo, titulo, categoria_raw, fonte, path, url, description, sugoi=sugoi)
        if not logo:
            logo = default_logo(grupo, iptv_categoria)
        item = {
            "grupo": grupo,
            "categoria": categoria_raw,
            "iptv_categoria": iptv_categoria,
            "titulo": titulo,
            "obra": obra,
            "episodio": ep or "",
            "stream_url": url,
            "logo": logo,
            "fonte": fonte,
            "source_file": path,
            "description": description,
            "subtitle": subtitle,
            "is_anime": "true" if (sugoi or "Anime" in iptv_categoria) else "false",
            "is_adult": "true" if iptv_categoria == "Adultos" else "false",
            "sugoi": sugoi or {},
        }
        if motivo:
            item["motivo"] = motivo
            invalid.append(item)
        else:
            valid.append(item)
    return valid, invalid


def load_items():
    sugoi_cache = load_sugoi_cache()
    all_items, invalid = [], []
    for source in CATALOG_SOURCES:
        items, bad = read_csv_source(source, sugoi_cache)
        print(f"Fonte {source}: {len(items)} valido(s), {len(bad)} ignorado(s)")
        all_items.extend(items)
        invalid.extend(bad)
    save_sugoi_cache(sugoi_cache)
    return all_items, invalid


def score_item(item, count=1):
    ext = stream_ext(item["stream_url"])
    score = 0
    if item["grupo"] == "Canais":
        score += 100 if ext == "m3u8" else 85 if ext == "ts" else 30
    else:
        score += 110 if ext == "mp4" else 80 if ext == "m3u8" else 20
    if item.get("logo"):
        score += 5
    if item.get("description"):
        score += 3
    if item.get("is_anime") == "true":
        score += 8
    score += min(count, 5) * 2
    return score


def group_key(item):
    if item["grupo"] == "Canais":
        return (item["grupo"], slug(item["titulo"]))
    return (item["grupo"], slug(item.get("obra") or item["titulo"]))


def dedupe_and_cluster(items):
    buckets = {}
    for item in items:
        ep_key = item.get("episodio") or slug(item["titulo"])
        key = (group_key(item), ep_key)
        buckets.setdefault(key, []).append(item)
    selected = []
    for _, variants in buckets.items():
        for v in variants:
            v["score"] = score_item(v, len(variants))
            v["sources_count"] = len(variants)
        variants.sort(key=lambda x: (-x["score"], x["titulo"], x["stream_url"]))
        best = variants[0]
        best["alternatives"] = [
            {"url": v["stream_url"], "source": v.get("fonte", ""), "score": v.get("score", 0)}
            for v in variants[1:6]
            if v["stream_url"] != best["stream_url"]
        ]
        selected.append(best)
    clusters = {}
    for item in selected:
        key = group_key(item)
        if key not in clusters:
            clusters[key] = {
                "title": item.get("obra") if item["grupo"] != "Canais" else item["titulo"],
                "group": item["grupo"],
                "category": item["categoria"],
                "iptvCategory": item["iptv_categoria"],
                "groupTitle": f'{item["grupo"]} | {item["iptv_categoria"]}',
                "logo": item.get("logo", ""),
                "description": item.get("description", ""),
                "isAnime": item.get("is_anime") == "true",
                "isAdult": item.get("is_adult") == "true",
                "score": 0,
                "sourcesCount": 0,
                "episodes": [],
            }
        ep_number = item.get("episodio") or len(clusters[key]["episodes"]) + 1
        clusters[key]["episodes"].append({
            "title": item["titulo"],
            "episode": ep_number,
            "url": item["stream_url"],
            "source": item.get("fonte", ""),
            "subtitle": item.get("subtitle", ""),
            "score": item.get("score", 0),
            "logo": item.get("logo", ""),
            "alternatives": item.get("alternatives", []),
        })
        clusters[key]["score"] = max(clusters[key]["score"], item.get("score", 0))
        clusters[key]["sourcesCount"] += item.get("sources_count", 1)
    result = list(clusters.values())
    for c in result:
        c["episodes"].sort(key=lambda e: (int(e["episode"]) if str(e["episode"]).isdigit() else 999999, e["title"]))
        c["episodeCount"] = len(c["episodes"])
        first = c["episodes"][0] if c["episodes"] else {}
        c["url"] = first.get("url", "")
        c["source"] = first.get("source", "")
    return sorted(result, key=lambda x: (x["group"], x["iptvCategory"], -x["score"], x["title"]))


def tvg_type(group):
    return "live" if group == "Canais" else "movie" if group == "Filmes" else "series"


def write_m3u(clusters, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        idx = 1
        for cluster in clusters:
            group_title = safe_group(f'{cluster["group"]} | {cluster["iptvCategory"]}')
            for ep in cluster.get("episodes", []):
                url = ep.get("url")
                if not is_stream_url(url):
                    continue
                title = safe_text(ep.get("title") or cluster.get("title") or "Sem titulo")
                logo = safe_text(ep.get("logo") or cluster.get("logo") or default_logo(cluster["group"], cluster["iptvCategory"]), 300)
                tvg_id = f'{slug(cluster["group"])}_{idx}'
                f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{title}" tvg-logo="{logo}" tvg-type="{tvg_type(cluster["group"])}" group-title="{group_title}",{title}\n')
                f.write(f"{url}\n")
                idx += 1
    print(f"Gerado {path}: {idx-1} item(ns)")


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Gerado {path}: {len(data)} item(ns)")


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Gerado {path}: {len(rows)} linha(s)")


def main():
    ensure_dirs()
    items, invalid = load_items()
    clusters = dedupe_and_cluster(items)
    write_m3u(clusters, OUTPUT_M3U)
    write_m3u(clusters, OUTPUT_MASTER)
    write_m3u([c for c in clusters if c["group"] == "Canais"], OUTPUT_CANAIS)
    write_m3u([c for c in clusters if c["group"] == "Series"], OUTPUT_SERIES)
    write_m3u([c for c in clusters if c["group"] == "Filmes"], OUTPUT_FILMES)
    write_json(OUTPUT_JSON, clusters)
    write_json(OUTPUT_CLUSTERED_JSON, clusters)
    write_csv(INVALID_CSV, invalid, ["grupo", "categoria", "iptv_categoria", "titulo", "stream_url", "fonte", "source_file", "motivo"])
    summary = [
        {"metric": "total_titles", "value": len(clusters)},
        {"metric": "total_episodes", "value": sum(len(c.get("episodes", [])) for c in clusters)},
        {"metric": "canais", "value": sum(1 for c in clusters if c["group"] == "Canais")},
        {"metric": "series", "value": sum(1 for c in clusters if c["group"] == "Series")},
        {"metric": "filmes", "value": sum(1 for c in clusters if c["group"] == "Filmes")},
        {"metric": "anime", "value": sum(1 for c in clusters if c.get("isAnime"))},
        {"metric": "adult", "value": sum(1 for c in clusters if c.get("isAdult"))},
    ]
    write_csv(SUMMARY_CSV, summary, ["metric", "value"])
    print("Pipeline IPTV FULL PRODUCAO finalizado com sucesso.")


if __name__ == "__main__":
    main()
