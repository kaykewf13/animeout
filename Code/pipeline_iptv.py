import csv
import json
import os
import re
import unicodedata
from pathlib import Path

CATALOG_SOURCES = [
    "sources/catalog.csv",
    "sources/iptv_org_vod.csv",
    "sources/plex_vod.csv",
    "sources/external_vod_sources.csv",
    "sources/vod_playlist_items.csv",
    "sources/channel_playlist_items.csv",
    "sources/github_vod_discovered.csv",
]

OUTPUT_M3U = "valid_links.m3u"
OUTPUT_JSON = "web/catalog.json"
OUTPUT_CLUSTERED_JSON = "web/catalog_clustered.json"
OUTPUT_MASTER = "output/master_playlist.m3u"
OUTPUT_CANAIS = "output/canais.m3u"
OUTPUT_SERIES = "output/series.m3u"
OUTPUT_FILMES = "output/filmes.m3u"
INVALID_CSV = "invalid_links.csv"
LOG_DIR = "logs"

VALID_GROUPS = {"Canais", "Filmes", "Series"}
ANIME_KEYWORDS = ["anime", "animes", "hentai", "ecchi", "shounen", "shonen", "seinen", "josei", "isekai", "mecha", "otaku", "naruto", "one piece", "dragon ball", "jujutsu"]
ADULT_KEYWORDS = ["adult", "adulto", "18+", "hentai", "erotic", "mature", "xxx"]
EXCLUDE_KEYWORDS = ["yaoi", "boys love", "boyslove", "shounen ai", "shonen ai"]
INVALID_TITLE_WORDS = ["test", "teste", "sample", "demo", "placeholder", "sem titulo", "sem título"]
CHANNEL_HINTS = [" tv", "channel", "canal", "news", "live", "24/7", "pluto tv", "rakuten tv"]
CATEGORY_MAP = {"movies":"Filmes","movie":"Filmes","film":"Filmes","films":"Filmes","series":"Series","shows":"Series","tv shows":"Series","animation":"Animacao","classic":"Classicos","entertainment":"Entretenimento","family":"Familia","kids":"Infantil","comedy":"Comedia","action":"Acao","adventure":"Aventura","horror":"Terror","thriller":"Suspense","documentary":"Documentario","music":"Musica","culture":"Cultura","general":"Geral","sports":"Esportes","news":"Noticias"}
DEFAULT_POSTERS = {
    "Canais": "https://placehold.co/600x900/111218/e7e9ee?text=Canais",
    "Filmes": "https://placehold.co/600x900/111218/e7e9ee?text=Filmes",
    "Series": "https://placehold.co/600x900/111218/e7e9ee?text=Series",
    "Anime": "https://placehold.co/600x900/111218/e23b3b?text=Anime",
    "Adultos": "https://placehold.co/600x900/111218/e23b3b?text=18%2B",
}


def ensure_dirs():
    Path("web").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path(LOG_DIR).mkdir(exist_ok=True)


def strip_accents(value):
    text = str(value or "")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def safe_text(value, max_len=140):
    text = strip_accents(value)
    text = text.replace("\ufeff", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = text.replace('"', "'").replace("`", "'")
    text = re.sub(r"[<>{}\[\]()]", " ", text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def safe_group(value):
    text = safe_text(value, 80)
    text = re.sub(r"[|;/\\:,]+", " - ", text)
    text = re.sub(r"[^A-Za-z0-9 +_.-]", " ", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or "Geral"


def iptv_group_name(group):
    group = safe_group(group)
    if group == "Canais":
        return "Canais"
    if group == "Filmes":
        return "Filmes"
    if group == "Series":
        return "Series"
    return "Outros"


def title_case(value):
    text = safe_text(value)
    small = {"da", "de", "do", "das", "dos", "e", "a", "o"}
    parts = []
    for p in text.split():
        parts.append(p.lower() if p.lower() in small else p[:1].upper() + p[1:])
    return " ".join(parts)


def normalizar_grupo(value):
    raw = (value or "").strip().lower()
    mapa = {"canais":"Canais","canal":"Canais","live":"Canais","lives":"Canais","filmes":"Filmes","filme":"Filmes","movies":"Filmes","movie":"Filmes","series":"Series","séries":"Series","serie":"Series","série":"Series","shows":"Series"}
    return mapa.get(raw, value.strip() if value else "")


def normalizar_categoria(value, grupo=""):
    parts = re.split(r"[;|,/]+", value or "")
    clean = []
    for part in parts:
        key = part.strip().lower()
        if not key:
            continue
        mapped = CATEGORY_MAP.get(key, part.strip())
        mapped = safe_group(mapped)
        if mapped not in clean and mapped != grupo:
            clean.append(mapped)
    return clean[0] if clean else "Geral"


def texto_item(*partes): return " ".join(str(p or "") for p in partes).lower()
def contem(texto, termos): return any(t in texto for t in termos)
def stream_ext(url): return (url or "").split("?")[0].lower().rsplit(".", 1)[-1] if "." in (url or "").split("?")[0] else ""
def is_stream_url(url): return (url or "").split("?")[0].lower().endswith((".m3u8", ".mp4", ".ts"))
def slug(value):
    value = strip_accents(value or "item").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "item"


def clean_title(value):
    text = value or ""
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\([^)]*(?:720p|1080p|480p|dub|legendado|pt-br)[^)]*\)", " ", text, flags=re.I)
    text = re.sub(r"\b(?:fhd|uhd|hd|sd|4k|1080p|720p|480p|360p|x264|x265|hevc|aac|dual audio|dublado|legendado|dub|sub)\b", " ", text, flags=re.I)
    text = re.sub(r"\b(?:ep|epis[oó]dio|episodio|episode)\s*\.?\s*\d+\b", " ", text, flags=re.I)
    text = re.sub(r"\b(?:season|temporada)\s*\d+\b", " ", text, flags=re.I)
    text = re.sub(r"\bS\d{1,2}E\d{1,3}\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,4}\b$", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -_|.")
    return title_case(text or value or "Sem titulo")


def normalized_display_title(titulo, grupo):
    title = clean_title(titulo)
    if grupo != "Canais":
        title = re.sub(r"\b(?:tv|channel|canal|live)\b$", "", title, flags=re.I).strip()
    return title_case(title)


def is_invalid_title(title):
    lower = strip_accents(title).lower().strip()
    return any(w in lower for w in INVALID_TITLE_WORDS) or len(lower) < 2


def should_be_channel(titulo, grupo, fonte):
    lower = strip_accents(f"{titulo} {fonte}").lower()
    return grupo == "Canais" or any(h in lower for h in CHANNEL_HINTS)


def default_logo(group, is_anime=False, is_adult=False):
    if is_adult: return DEFAULT_POSTERS["Adultos"]
    if is_anime: return DEFAULT_POSTERS["Anime"]
    return DEFAULT_POSTERS.get(group, DEFAULT_POSTERS["Series"])


def episode_number(title):
    patterns = [r"S(\d{1,2})E(\d{1,3})", r"(?:ep|epis[oó]dio|episodio|episode)\s*\.?\s*(\d+)", r"\b(\d{1,4})\b$"]
    for p in patterns:
        m = re.search(p, title or "", flags=re.I)
        if m:
            try: return int(m.groups()[-1])
            except Exception: pass
    return None


def obra_key(item):
    base = item.get("anime") or clean_title(item.get("titulo"))
    return (item.get("grupo"), slug(base))


def group_title(item):
    base = safe_group(item.get("grupo") or "Geral")
    categoria = safe_group((item.get("categoria") or "Geral").split("|")[0])
    if item.get("is_adult") == "true" or item.get("isAdult") is True:
        return f"{base} - Adultos"
    if categoria and categoria.lower() not in ["geral", base.lower()]:
        return f"{base} - {categoria}"
    return base


def tvg_type(grupo): return "live" if grupo == "Canais" else "movie" if grupo == "Filmes" else "series"


def classificar_flags(grupo, categoria, titulo, description):
    texto = texto_item(grupo, categoria, titulo, description)
    return contem(texto, ANIME_KEYWORDS) or contem(texto, ADULT_KEYWORDS), contem(texto, ADULT_KEYWORDS), contem(texto, EXCLUDE_KEYWORDS)


def carregar_csv(path):
    if not os.path.exists(path): return [], []
    validos, invalidos = [], []
    with open(path, encoding="utf-8", errors="ignore") as f:
        linhas = [linha for linha in f if linha.strip() and not linha.lstrip().startswith("#")]
    if not linhas: return validos, invalidos
    reader = csv.DictReader(linhas)
    for row in reader:
        grupo = normalizar_grupo(row.get("grupo") or row.get("group"))
        titulo_raw = (row.get("titulo") or row.get("title") or row.get("tvg-name") or "Sem titulo").strip() or "Sem titulo"
        fonte = (row.get("fonte") or row.get("source") or path).strip()
        if should_be_channel(titulo_raw, grupo, fonte): grupo = "Canais"
        categoria = normalizar_categoria(row.get("categoria") or row.get("category") or "Geral", grupo)
        titulo = normalized_display_title(titulo_raw, grupo)
        url = (row.get("stream_url") or row.get("url") or "").strip()
        logo = (row.get("logo") or row.get("tvg-logo") or "").strip()
        description = (row.get("description") or row.get("descricao") or "").strip()
        rating = (row.get("rating") or row.get("nota") or "").strip()
        subtitle = (row.get("subtitle") or row.get("legenda") or "").strip()
        anime_name = normalized_display_title(row.get("anime") or "", "Series") if row.get("anime") else ""
        ep = row.get("episodio") or episode_number(titulo_raw) or ""
        motivo = ""
        if is_invalid_title(titulo): motivo = "titulo_invalido_ou_teste"
        elif not url or not url.startswith("http"): motivo = "url_vazia_ou_invalida"
        elif grupo not in VALID_GROUPS: motivo = "grupo_invalido"
        elif not is_stream_url(url): motivo = "nao_e_stream_direto"
        is_anime, is_adult, is_excluded = classificar_flags(grupo, categoria, titulo, description)
        if is_excluded: motivo = "conteudo_excluido_yaoi_bl"
        if not logo: logo = default_logo(grupo, is_anime, is_adult)
        item = {"grupo":grupo,"categoria":categoria,"titulo":titulo,"stream_url":url,"logo":logo,"fonte":fonte,"description":description,"rating":rating,"subtitle":subtitle,"is_anime":"true" if is_anime else "false","is_adult":"true" if is_adult else "false","source_file":path,"anime":anime_name,"episodio":ep}
        if motivo:
            item["motivo"] = motivo; invalidos.append(item)
        else: validos.append(item)
    return validos, invalidos


def carregar_catalogos():
    todos, invalidos = [], []
    for source in CATALOG_SOURCES:
        itens, ruins = carregar_csv(source)
        print(f"Fonte {source}: {len(itens)} valido(s), {len(ruins)} ignorado(s)")
        todos.extend(itens); invalidos.extend(ruins)
    return todos, invalidos


def calcular_score(item, qtd_fontes=1):
    ext = stream_ext(item["stream_url"])
    score = 100 if ext == "m3u8" else 70 if ext == "mp4" else 45 if ext == "ts" else 0
    if item.get("grupo") == "Canais" and ext == "m3u8": score += 15
    if item.get("grupo") in ["Series", "Filmes"] and ext in ["mp4", "m3u8"]: score += 10
    if item.get("is_anime") == "true": score += 12
    if item.get("logo"): score += 5
    if item.get("description"): score += 3
    score += min(qtd_fontes, 5) * 2
    return score


def melhor_por_episodio_com_fallback(items):
    grupos = {}
    for item in items:
        key = (obra_key(item), item.get("episodio") or slug(item.get("titulo")))
        grupos.setdefault(key, []).append(item)
    escolhidos = []
    for _, grupo in grupos.items():
        qtd = len(grupo)
        for item in grupo:
            item["score"] = calcular_score(item, qtd); item["sources_count"] = qtd
        grupo.sort(key=lambda x: (-x["score"], x["titulo"], x["stream_url"]))
        best = grupo[0]
        best["alternatives"] = [{"url": g["stream_url"], "source": g.get("fonte", ""), "score": g.get("score", 0)} for g in grupo[1:6] if g["stream_url"] != best["stream_url"]]
        escolhidos.append(best)
    return escolhidos


def gerar_cluster(items):
    clusters = {}
    for item in melhor_por_episodio_com_fallback(items):
        key = obra_key(item)
        obra_nome = item.get("anime") or clean_title(item.get("titulo"))
        if key not in clusters:
            clusters[key] = {"title": safe_text(obra_nome),"group": item["grupo"],"category": item["categoria"],"groupTitle": group_title(item),"logo": item.get("logo", ""),"description": item.get("description", ""),"rating": item.get("rating", ""),"isAnime": item.get("is_anime") == "true","isAdult": item.get("is_adult") == "true","score": 0,"sourcesCount": 0,"episodes": []}
        ep = item.get("episodio") or len(clusters[key]["episodes"]) + 1
        clusters[key]["episodes"].append({"title": safe_text(item["titulo"]),"episode": ep,"url": item["stream_url"],"source": item.get("fonte", ""),"subtitle": item.get("subtitle", ""),"score": item.get("score", 0),"logo": item.get("logo", ""),"alternatives": item.get("alternatives", [])})
        clusters[key]["score"] = max(clusters[key]["score"], item.get("score", 0))
        clusters[key]["sourcesCount"] += item.get("sources_count", 1)
        if not clusters[key].get("logo") and item.get("logo"): clusters[key]["logo"] = item["logo"]
    result = list(clusters.values())
    for c in result:
        c["episodes"].sort(key=lambda e: (int(e["episode"]) if str(e["episode"]).isdigit() else 999999, e["title"]))
        c["episodeCount"] = len(c["episodes"])
        first = c["episodes"][0] if c["episodes"] else {}
        c["url"] = first.get("url", "")
        c["source"] = first.get("source", "")
        c["subtitle"] = first.get("subtitle", "")
    return sorted(result, key=lambda x: (x["group"], x["category"], -x["score"], x["title"]))


def gerar_m3u(clusters, caminho, mode="iptv"):
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        idx = 1
        for obra in clusters:
            for ep in obra.get("episodes", []):
                if not is_stream_url(ep.get("url")):
                    continue
                title = safe_text(ep.get("title") or obra.get("title") or "Sem titulo")
                logo = safe_text(ep.get("logo") or obra.get("logo") or "", 300)
                group = iptv_group_name(obra.get("group")) if mode == "iptv" else safe_group(obra.get("groupTitle") or group_title(obra))
                tvg_id = f"{slug(obra.get('group'))}_{idx}"
                f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{title}" tvg-logo="{logo}" tvg-type="{tvg_type(obra.get("group"))}" group-title="{group}",{title}\n')
                f.write(f"{ep['url']}\n")
                idx += 1
    print(f"Gerado {caminho}: {idx-1} item(ns)")


def gerar_json(items, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Gerado {caminho}: {len(items)} item(ns)")


def gerar_flat_json(clusters):
    payload = []
    for obra in clusters:
        item = dict(obra); item["url"] = obra.get("url", "")
        payload.append(item)
    gerar_json(payload, OUTPUT_JSON); gerar_json(clusters, OUTPUT_CLUSTERED_JSON)


def gerar_csv(caminho, rows, fields):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
    print(f"Gerado {caminho}: {len(rows)} linha(s)")


def main():
    ensure_dirs()
    itens, invalidos = carregar_catalogos()
    stream_items = [i for i in itens if i.get("stream_url", "").startswith("http") and is_stream_url(i.get("stream_url"))]
    clusters = gerar_cluster(stream_items)
    gerar_m3u(clusters, OUTPUT_M3U, mode="iptv"); gerar_m3u(clusters, OUTPUT_MASTER, mode="iptv")
    gerar_m3u([c for c in clusters if c["group"] == "Canais"], OUTPUT_CANAIS, mode="iptv")
    gerar_m3u([c for c in clusters if c["group"] == "Series"], OUTPUT_SERIES, mode="iptv")
    gerar_m3u([c for c in clusters if c["group"] == "Filmes"], OUTPUT_FILMES, mode="iptv")
    gerar_flat_json(clusters)
    gerar_csv(INVALID_CSV, invalidos, ["grupo","categoria","titulo","stream_url","fonte","source_file","motivo"])
    gerar_csv("logs/catalog_summary.csv", [{"metric":"total_titles","value":len(clusters)},{"metric":"total_episodes","value":sum(len(c.get("episodes", [])) for c in clusters)},{"metric":"canais","value":sum(1 for c in clusters if c["group"] == "Canais")},{"metric":"series","value":sum(1 for c in clusters if c["group"] == "Series")},{"metric":"filmes","value":sum(1 for c in clusters if c["group"] == "Filmes")},{"metric":"anime","value":sum(1 for c in clusters if c.get("isAnime"))},{"metric":"adult","value":sum(1 for c in clusters if c.get("isAdult"))}], ["metric","value"])
    print("IPTV ultra compat finalizado com sucesso.")


if __name__ == "__main__":
    main()
