import csv
import json
import os
import re
from pathlib import Path

CATALOG_SOURCES = [
    "sources/catalog.csv",
    "sources/iptv_org_vod.csv",
    "sources/plex_vod.csv",
    "sources/external_vod_sources.csv",
]

OUTPUT_M3U = "valid_links.m3u"
OUTPUT_JSON = "web/catalog.json"
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
CATEGORY_MAP = {
    "movies": "Filmes", "movie": "Filmes", "film": "Filmes", "films": "Filmes",
    "series": "Series", "shows": "Series", "tv shows": "Series",
    "animation": "Animação", "classic": "Clássicos", "entertainment": "Entretenimento",
    "family": "Família", "kids": "Infantil", "comedy": "Comédia", "action": "Ação",
    "adventure": "Aventura", "horror": "Terror", "thriller": "Suspense",
    "documentary": "Documentário", "music": "Música", "culture": "Cultura",
    "general": "Geral", "sports": "Esportes", "news": "Notícias",
}


def ensure_dirs():
    Path("web").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path(LOG_DIR).mkdir(exist_ok=True)


def normalizar_grupo(value):
    raw = (value or "").strip().lower()
    mapa = {
        "canais": "Canais", "canal": "Canais", "live": "Canais", "lives": "Canais",
        "filmes": "Filmes", "filme": "Filmes", "movies": "Filmes", "movie": "Filmes",
        "series": "Series", "séries": "Series", "serie": "Series", "série": "Series", "shows": "Series",
    }
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


def texto_item(*partes):
    return " ".join(str(p or "") for p in partes).lower()


def contem(texto, termos):
    return any(t in texto for t in termos)


def is_stream_url(url):
    url_limpa = (url or "").split("?")[0].lower()
    return url_limpa.endswith((".m3u8", ".mp4", ".ts"))


def slug(value):
    value = (value or "item").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "item"


def group_title(item):
    categoria = item["categoria"]
    if item.get("is_adult") == "true" and not categoria.lower().startswith("adultos"):
        categoria = f"Adultos | {categoria}"
    return f"{item['grupo']} | {categoria}"


def tvg_type(grupo):
    if grupo == "Canais":
        return "live"
    if grupo == "Filmes":
        return "movie"
    return "series"


def classificar_flags(grupo, categoria, titulo, description):
    texto = texto_item(grupo, categoria, titulo, description)
    is_excluded = contem(texto, EXCLUDE_KEYWORDS)
    is_adult = contem(texto, ADULT_KEYWORDS)
    is_anime = contem(texto, ANIME_KEYWORDS) or is_adult
    return is_anime, is_adult, is_excluded


def carregar_csv(path):
    if not os.path.exists(path):
        return [], []

    validos = []
    invalidos = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        linhas = [linha for linha in f if linha.strip() and not linha.lstrip().startswith("#")]
    if not linhas:
        return validos, invalidos

    reader = csv.DictReader(linhas)
    for row in reader:
        grupo = normalizar_grupo(row.get("grupo") or row.get("group"))
        categoria_raw = row.get("categoria") or row.get("category") or "Geral"
        categoria = normalizar_categoria(categoria_raw, grupo)
        titulo = (row.get("titulo") or row.get("title") or row.get("tvg-name") or "Sem título").strip() or "Sem título"
        url = (row.get("stream_url") or row.get("url") or "").strip()
        logo = (row.get("logo") or row.get("tvg-logo") or "").strip()
        fonte = (row.get("fonte") or row.get("source") or path).strip()
        description = (row.get("description") or row.get("descricao") or "").strip()
        rating = (row.get("rating") or row.get("nota") or "").strip()
        subtitle = (row.get("subtitle") or row.get("legenda") or "").strip()

        motivo = ""
        if not url or not url.startswith("http"):
            motivo = "url_vazia_ou_invalida"
        elif grupo not in VALID_GROUPS:
            motivo = "grupo_invalido"
        elif fonte in ["iptv-org", "plex-vod", "vod-org"] and grupo == "Canais":
            motivo = "vod_nao_pode_ser_canal"
        elif not is_stream_url(url):
            motivo = "nao_e_stream_direto"

        is_anime, is_adult, is_excluded = classificar_flags(grupo, categoria, titulo, description)
        if is_excluded:
            motivo = "conteudo_excluido_yaoi_bl"

        item = {
            "grupo": grupo,
            "categoria": categoria,
            "titulo": titulo,
            "stream_url": url,
            "logo": logo,
            "fonte": fonte,
            "description": description,
            "rating": rating,
            "subtitle": subtitle,
            "is_anime": "true" if is_anime else "false",
            "is_adult": "true" if is_adult else "false",
            "source_file": path,
        }

        if motivo:
            item["motivo"] = motivo
            invalidos.append(item)
        else:
            validos.append(item)
    return validos, invalidos


def carregar_catalogos():
    todos, invalidos = [], []
    for source in CATALOG_SOURCES:
        itens, ruins = carregar_csv(source)
        print(f"Fonte {source}: {len(itens)} válido(s), {len(ruins)} ignorado(s)")
        todos.extend(itens)
        invalidos.extend(ruins)
    return todos, invalidos


def calcular_score(item, qtd_fontes=1):
    url = item["stream_url"].lower().split("?")[0]
    score = 0
    if url.endswith(".m3u8"):
        score += 50
    elif url.endswith(".mp4"):
        score += 20
    elif url.endswith(".ts"):
        score += 10
    if item.get("is_anime") == "true": score += 12
    if item.get("logo"): score += 5
    if item.get("description"): score += 3
    score += min(qtd_fontes, 5) * 2
    return score


def agrupar_por_titulo(itens):
    grupos = {}
    for item in itens:
        chave = (item["grupo"], slug(item["titulo"]))
        grupos.setdefault(chave, []).append(item)
    return grupos


def selecionar_melhores(itens):
    selecionados = []
    for _, grupo in agrupar_por_titulo(itens).items():
        qtd = len(grupo)
        for item in grupo:
            item["score"] = calcular_score(item, qtd_fontes=qtd)
            item["sources_count"] = qtd
        grupo.sort(key=lambda x: (-x["score"], x["titulo"], x["stream_url"]))
        selecionados.append(grupo[0])
    return sorted(selecionados, key=lambda x: (x["grupo"], x["categoria"], -x.get("score", 0), x["titulo"]))


def gerar_m3u(itens, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for idx, item in enumerate(itens, 1):
            title = item["titulo"].replace('"', "'")
            logo = item.get("logo", "").replace('"', "")
            group = group_title(item).replace('"', "'")
            tvg_id = f"{slug(item['grupo'])}_{slug(title)}_{idx}"
            f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{title}" tvg-logo="{logo}" tvg-language="pt" tvg-type="{tvg_type(item["grupo"])}" group-title="{group}",{title}\n')
            f.write(f"{item['stream_url']}\n")
    print(f"Gerado {caminho}: {len(itens)} item(ns)")


def gerar_json(itens, caminho=OUTPUT_JSON):
    payload = []
    for item in itens:
        payload.append({
            "title": item["titulo"], "group": item["grupo"], "category": item["categoria"],
            "groupTitle": group_title(item), "url": item["stream_url"], "logo": item.get("logo", ""),
            "source": item.get("fonte", ""), "description": item.get("description", ""),
            "rating": item.get("rating", ""), "subtitle": item.get("subtitle", ""),
            "isAnime": item.get("is_anime") == "true", "isAdult": item.get("is_adult") == "true",
            "score": item.get("score", 0), "sourcesCount": item.get("sources_count", 1),
        })
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Gerado {caminho}: {len(payload)} item(ns)")


def gerar_csv(caminho, rows, fields):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    print(f"Gerado {caminho}: {len(rows)} linha(s)")


def main():
    ensure_dirs()
    itens, invalidos = carregar_catalogos()
    selecionados = selecionar_melhores(itens)
    selecionados = [i for i in selecionados if i.get("stream_url", "").startswith("http")]
    gerar_m3u(selecionados, OUTPUT_M3U)
    gerar_m3u(selecionados, OUTPUT_MASTER)
    gerar_m3u([i for i in selecionados if i["grupo"] == "Canais"], OUTPUT_CANAIS)
    gerar_m3u([i for i in selecionados if i["grupo"] == "Series"], OUTPUT_SERIES)
    gerar_m3u([i for i in selecionados if i["grupo"] == "Filmes"], OUTPUT_FILMES)
    gerar_json(selecionados)
    gerar_csv(INVALID_CSV, invalidos, ["grupo", "categoria", "titulo", "stream_url", "fonte", "source_file", "motivo"])
    gerar_csv("logs/catalog_summary.csv", [
        {"metric":"total_selected","value":len(selecionados)},
        {"metric":"canais","value":sum(1 for i in selecionados if i["grupo"] == "Canais")},
        {"metric":"series","value":sum(1 for i in selecionados if i["grupo"] == "Series")},
        {"metric":"filmes","value":sum(1 for i in selecionados if i["grupo"] == "Filmes")},
        {"metric":"anime","value":sum(1 for i in selecionados if i.get("is_anime") == "true")},
        {"metric":"adult","value":sum(1 for i in selecionados if i.get("is_adult") == "true")},
    ], ["metric", "value"])
    print("Pipeline finalizado com sucesso.")


if __name__ == "__main__":
    main()
