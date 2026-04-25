import csv
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

VALID_GROUPS = {"Canais", "Filmes", "Series"}
STREAM_PATTERN = re.compile(r"https?://[^\"'<>\s]+?\.(?:m3u8|mp4)(?:\?[^\"'<>\s]*)?", re.IGNORECASE)
IGNORED_PATTERN = re.compile(r"https?://[^\"'<>\s]+?\.(?:mkv|avi|mov)(?:\?[^\"'<>\s]*)?", re.IGNORECASE)
TIMEOUT_SECONDS = 8
WORKERS = 12


def ensure_dirs():
    Path("output").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)


def normalizar_link(link, base_url):
    return urljoin(base_url, unquote(link.strip()))


def extensao(link):
    return os.path.splitext(link.lower().split("?")[0])[1]


def group_title(item):
    return f"{item['grupo']} | {item['categoria']}"


def ler_catalogo(caminho="sources/catalog.csv"):
    itens = []
    if not os.path.exists(caminho):
        print(f"Catálogo não encontrado: {caminho}")
        return itens

    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        linhas = [linha for linha in f if linha.strip() and not linha.lstrip().startswith("#")]

    reader = csv.DictReader(linhas)
    for row in reader:
        grupo = (row.get("grupo") or "").strip()
        categoria = (row.get("categoria") or "Geral").strip() or "Geral"
        titulo = (row.get("titulo") or "Sem título").strip() or "Sem título"
        url = (row.get("url") or "").strip()

        if not url or not url.startswith("http"):
            continue
        if grupo not in VALID_GROUPS:
            print(f"Grupo ignorado: {grupo}. Use Canais, Filmes ou Series.")
            continue

        itens.append({"grupo": grupo, "categoria": categoria, "titulo": titulo, "url": url})

    return itens


def extrair_do_html(html, base_url, aceitar_mp4=False):
    streams = set()
    ignorados = set()

    for match in STREAM_PATTERN.findall(html):
        link = normalizar_link(match, base_url)
        ext = extensao(link)
        if ext == ".m3u8" or (aceitar_mp4 and ext == ".mp4"):
            streams.add(link)

    for match in IGNORED_PATTERN.findall(html):
        ignorados.add(normalizar_link(match, base_url))

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["a", "source", "video", "script"]):
        for attr in ["href", "src", "data-src", "data-url", "file"]:
            valor = tag.get(attr)
            if not valor:
                continue
            link = normalizar_link(valor, base_url)
            ext = extensao(link)
            if ext == ".m3u8" or (aceitar_mp4 and ext == ".mp4"):
                streams.add(link)
            elif ext in [".mkv", ".avi", ".mov"]:
                ignorados.add(link)

    return streams, ignorados, soup


def extrair_streams_item(item, aceitar_mp4=False):
    url = item["url"]
    ext = extensao(url)
    if ext == ".m3u8" or (aceitar_mp4 and ext == ".mp4"):
        return [{**item, "stream_url": url}], []
    if ext in [".mkv", ".avi", ".mov"]:
        return [], [{**item, "ignored_url": url, "motivo": "arquivo_download_nao_iptv"}]

    streams_finais = set()
    ignorados_finais = set()

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        streams, ignorados, soup = extrair_do_html(r.text, url, aceitar_mp4=aceitar_mp4)
        streams_finais.update(streams)
        ignorados_finais.update(ignorados)

        for iframe in soup.find_all("iframe"):
            src = iframe.get("src")
            if not src:
                continue
            iframe_url = normalizar_link(src, url)
            try:
                r2 = requests.get(iframe_url, headers={**HEADERS, "Referer": url}, timeout=TIMEOUT_SECONDS)
                encontrados, ignorados_iframe, _ = extrair_do_html(r2.text, iframe_url, aceitar_mp4=aceitar_mp4)
                streams_finais.update(encontrados)
                ignorados_finais.update(ignorados_iframe)
            except Exception as e:
                ignorados_finais.add(f"IFRAME_ERROR::{iframe_url}::{e}")
    except Exception as e:
        return [], [{**item, "ignored_url": url, "motivo": f"erro_extracao: {e}"}]

    streams = [{**item, "stream_url": s} for s in sorted(streams_finais, key=lambda x: (0 if extensao(x) == ".m3u8" else 1, x))]
    ignorados = [{**item, "ignored_url": s, "motivo": "arquivo_ignorado_ou_erro"} for s in sorted(ignorados_finais)]
    return streams, ignorados


def validar_stream(item):
    url = item["stream_url"]
    try:
        if extensao(url) == ".m3u8":
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, allow_redirects=True)
            texto = r.text[:500] if r.text else ""
            ok = r.status_code == 200 and ("#EXTM3U" in texto or "#EXT" in texto)
            motivo = "m3u8 válido" if ok else "m3u8 inválido"
            return ok, item, r.status_code, r.headers.get("content-type", ""), motivo

        headers = {**HEADERS, "Range": "bytes=0-1024"}
        r = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=True)
        content_type = r.headers.get("content-type", "").lower()
        ok = r.status_code in [200, 206] and ("video" in content_type or extensao(url) == ".mp4")
        motivo = "mp4 provável" if ok else "mp4 inválido"
        return ok, item, r.status_code, content_type, motivo
    except Exception as e:
        return False, item, "ERROR", "", str(e)


def gerar_m3u(itens, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in itens:
            f.write(f"#EXTINF:-1 group-title=\"{group_title(item)}\",{item['titulo']}\n{item['stream_url']}\n")
    print(f"Gerado: {caminho} ({len(itens)} item(ns))")


def gerar_csv(caminho, rows, fields):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Gerado: {caminho} ({len(rows)} linha(s))")


def main():
    ensure_dirs()
    aceitar_mp4 = os.getenv("ACCEPT_MP4", "false").lower() == "true"

    catalogo = ler_catalogo()
    print(f"Itens no catálogo: {len(catalogo)}")
    if not catalogo:
        return

    extraidos = []
    ignorados = []

    print(f"Extraindo streams com {WORKERS} worker(s)...")
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futuros = [executor.submit(extrair_streams_item, item, aceitar_mp4) for item in catalogo]
        for futuro in as_completed(futuros):
            streams, ignored = futuro.result()
            extraidos.extend(streams)
            ignorados.extend(ignored)

    gerar_csv("logs/extracted_streams.csv", extraidos, ["grupo", "categoria", "titulo", "url", "stream_url"])
    gerar_csv("logs/ignored_download_files.csv", ignorados, ["grupo", "categoria", "titulo", "url", "ignored_url", "motivo"])

    validos = []
    invalidos = []

    print(f"Validando {len(extraidos)} stream(s) com {WORKERS} worker(s)...")
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futuros = [executor.submit(validar_stream, item) for item in extraidos]
        for futuro in as_completed(futuros):
            ok, item, status, content_type, motivo = futuro.result()
            if ok:
                validos.append(item)
            else:
                invalidos.append({**item, "status": status, "content_type": content_type, "motivo": motivo})

    validos = sorted(validos, key=lambda x: (x["grupo"], x["categoria"], x["titulo"], x["stream_url"]))

    gerar_m3u(validos, "valid_links.m3u")
    gerar_m3u(validos, "output/master_playlist.m3u")
    gerar_m3u([i for i in validos if i["grupo"] == "Canais"], "output/canais.m3u")
    gerar_m3u([i for i in validos if i["grupo"] == "Series"], "output/series.m3u")
    gerar_m3u([i for i in validos if i["grupo"] == "Filmes"], "output/filmes.m3u")

    gerar_csv("invalid_links.csv", invalidos, ["grupo", "categoria", "titulo", "url", "stream_url", "status", "content_type", "motivo"])

    print("\nResumo final:")
    print(f"Extraídos: {len(extraidos)}")
    print(f"Válidos: {len(validos)}")
    print(f"Inválidos: {len(invalidos)}")
    print(f"Ignorados/fallback MKV: {len(ignorados)}")


if __name__ == "__main__":
    main()
