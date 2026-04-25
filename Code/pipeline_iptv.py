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
CATEGORY_MAP = {"movies":"Filmes","movie":"Filmes","film":"Filmes","films":"Filmes","series":"Series","shows":"Series","tv shows":"Series","animation":"Animação","classic":"Clássicos","entertainment":"Entretenimento","family":"Família","kids":"Infantil","comedy":"Comédia","action":"Ação","adventure":"Aventura","horror":"Terror","thriller":"Suspense","documentary":"Documentário","music":"Música","culture":"Cultura","general":"Geral","sports":"Esportes","news":"Notícias"}


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
    text = text.replace('"', "'")
    text = re.sub(r"[<>{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def safe_group(value):
    text = safe_text(value, 80)
    text = text.replace("|", "-").replace(";", "-").replace("/", "-").replace("\\", "-")
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or "Geral"


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
        if mapped not in clean and mapped != grupo:
            clean.append(mapped)
    return " | ".join(clean[:3]) if clean else "Geral"


def texto_item(*partes): return " ".join(str(p or "") for p in partes).lower()
def contem(texto, termos): return any(t in texto for t in termos)
def is_stream_url(url): return (url or "").split("?")[0].lower().endswith((".m3u8", ".mp4", ".ts"))
def slug(value):
    value = strip_accents(value or "item").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "item"


def clean_title(value):
    text = value or ""
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\([^)]*(?:720p|1080p|480p|dub|legendado|pt-br)[^)]*\)", " ", text, flags=re.I)
    text = re.sub(r"\b(?:ep|epis[oó]dio|episodio|episode)\s*\.?\s*\d+\b", " ", text, flags=re.I)
    text = re.sub(r"\b(?:season|temporada)\s*\d+\b", " ", text, flags=re.I)
    text = re.sub(r"\bS\d{1,2}E\d{1,3}\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,4}\b$", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -_|.")
    return text or value or "Sem título"


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
    categoria = safe_group((item.get("categoria") or "").split("|")[0])
    if item.get("is_adult") == "true":
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
        categoria = normalizar_categoria(row.get("categoria") or row.get("category") or "Geral", grupo)
        titulo = (row.get("titulo") or row.get("title") or row.get("tvg-name") or "Sem título").strip() or "Sem título"
        url = (row.get("stream_url") or row.get("url") or "").strip()
        logo = (row.get("logo") or row.get("tvg-logo") or "").strip()
        fonte = (row.get("fonte") or row.get("source") or path).strip()
        description = (row.get("description") or row.get("descricao") or "").strip()
        rating = (row.get("rating") or row.get("nota") or "").strip()
        subtitle = (row.get("subtitle") or row.get("legenda") or "").strip()
        anime_name = (row.get("anime") or "").strip()
        ep = row.get("episodio") or episode_number(titulo) or ""
        motivo = ""
        if not url or not url.startswith("http"): motivo = "url_vazia_ou_invalida"
        elif grupo not in VALID_GROUPS: motivo = "grupo_invalido"
        elif fonte in ["iptv-org", "plex-vod", "vod-org"] and grupo == "Canais": motivo = "vod_nao_pode_ser_canal"
        elif not is_stream_url(url): motivo = "nao_e_stream_direto"
        is_anime, is_adult, is_excluded = classificar_flags(grupo, categoria, titulo, description)
        if is_excluded: motivo = "conteudo_excluido_yaoi_bl"
        item = {"grupo":grupo,"categoria":categoria,"titulo":titulo,"stream_url":url,"logo":logo,"fonte":fonte,"description":description,"rating":rating,"subtitle":subtitle,"is_anime":"true" if is_anime else "false","is_adult":"true" if is_adult else "false","source_file":path,"anime":anime_name,"episodio":ep}
        if motivo:
            item["motivo"] = motivo; invalidos.append(item)
        else: validos.append(item)
    return validos, invalidos


def carregar_catalogos():
    todos, invalidos = [], []
    for source in CATALOG_SOURCES:
        itens, ruins = carregar_csv(source)
        print(f"Fonte {source}: {len(itens)} válido(s), {len(ruins)} ignorado(s)")
        todos.extend(itens); invalidos.extend(ruins)
    return todos, invalidos


def calcular_score(item, qtd_fontes=1):
    url = item["stream_url"].lower().split("?")[0]
    score = 50 if url.endswith(".m3u8") else 20 if url.endswith(".mp4") else 10 if url.endswith(".ts") else 0
    if item.get("is_anime") == "true": score += 12
    if item.get("logo"): score += 5
    if item.get("description"): score += 3
    score += min(qtd_fontes, 5) * 2
    return score


def selecionar_melhor_streams_por_episodio(items):
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
        escolhidos.append(grupo[0])
    return escolhidos


def gerar_cluster(items):
    clusters = {}
    for item in selecionar_melhor_streams_por_episodio(items):
        key = obra_key(item)
        obra_nome = item.get("anime") or clean_title(item.get("titulo"))
        if key not in clusters:
            clusters[key] = {"title": safe_text(obra_nome),"group": item["grupo"],"category": item["categoria"],"groupTitle": group_title(item),"logo": item.get("logo", ""),"description": item.get("description", ""),"rating": item.get("rating", ""),"isAnime": item.get("is_anime") == "true","isAdult": item.get("is_adult") == "true","score": 0,"sourcesCount": 0,"episodes": []}
        ep = item.get("episodio") or len(clusters[key]["episodes"]) + 1
        clusters[key]["episodes"].append({"title": safe_text(item["titulo"]),"episode": ep,"url": item["stream_url"],"source": item.get("fonte", ""),"subtitle": item.get("subtitle", ""),"score": item.get("score", 0),"logo": item.get("logo", "")})
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


def gerar_m3u(clusters, caminho):
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        idx = 1
        for obra in clusters:
            for ep in obra.get("episodes", []):
                title = safe_text(ep.get("title") or obra.get("title") or "Sem titulo")
                logo = safe_text(ep.get("logo") or obra.get("logo") or "", 300)
                group = safe_group(obra.get("groupTitle") or group_title(obra))
                tvg_id = f"{slug(obra.get('group'))}_{slug(obra.get('title'))}_{idx}"
                f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{title}" tvg-logo="{logo}" tvg-language="pt" tvg-type="{tvg_type(obra.get("group"))}" group-title="{group}",{title}\n')
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
        item = dict(obra)
        item["url"] = obra.get("url", "")
        payload.append(item)
    gerar_json(payload, OUTPUT_JSON)
    gerar_json(clusters, OUTPUT_CLUSTERED_JSON)


def gerar_csv(caminho, rows, fields):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    print(f"Gerado {caminho}: {len(rows)} linha(s)")


def main():
    ensure_dirs()
    itens, invalidos = carregar_catalogos()
    clusters = gerar_cluster([i for i in itens if i.get("stream_url", "").startswith("http")])
    gerar_m3u(clusters, OUTPUT_M3U)
    gerar_m3u(clusters, OUTPUT_MASTER)
    gerar_m3u([c for c in clusters if c["group"] == "Canais"], OUTPUT_CANAIS)
    gerar_m3u([c for c in clusters if c["group"] == "Series"], OUTPUT_SERIES)
    gerar_m3u([c for c in clusters if c["group"] == "Filmes"], OUTPUT_FILMES)
    gerar_flat_json(clusters)
    gerar_csv(INVALID_CSV, invalidos, ["grupo","categoria","titulo","stream_url","fonte","source_file","motivo"])
    gerar_csv("logs/catalog_summary.csv", [{"metric":"total_titles","value":len(clusters)},{"metric":"total_episodes","value":sum(len(c.get("episodes", [])) for c in clusters)},{"metric":"canais","value":sum(1 for c in clusters if c["group"] == "Canais")},{"metric":"series","value":sum(1 for c in clusters if c["group"] == "Series")},{"metric":"filmes","value":sum(1 for c in clusters if c["group"] == "Filmes")},{"metric":"anime","value":sum(1 for c in clusters if c.get("isAnime"))},{"metric":"adult","value":sum(1 for c in clusters if c.get("isAdult"))}], ["metric","value"])
    print("Cluster inteligente finalizado com sucesso.")


if __name__ == "__main__":
    main()
