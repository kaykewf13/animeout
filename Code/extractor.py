import os
import re
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

# IPTV real: priorizar HLS (.m3u8). MP4 fica opcional. MKV é ignorado na playlist final.
STREAM_PATTERN = re.compile(r"https?://[^\"'<>\s]+?\.(?:m3u8|mp4)(?:\?[^\"'<>\s]*)?", re.IGNORECASE)
M3U8_PATTERN = re.compile(r"https?://[^\"'<>\s]+?\.m3u8(?:\?[^\"'<>\s]*)?", re.IGNORECASE)
STREAM_EXTENSIONS = (".m3u8", ".mp4")
IGNORED_EXTENSIONS = (".mkv", ".avi", ".mov")


def normalizar_link(link, base_url):
    link = unquote(link.strip())
    return urljoin(base_url, link)


def extensao_do_link(link):
    base = link.lower().split("?")[0]
    _, ext = os.path.splitext(base)
    return ext


def is_stream_iptv(link, aceitar_mp4=True):
    ext = extensao_do_link(link)
    if ext == ".m3u8":
        return True
    if aceitar_mp4 and ext == ".mp4":
        return True
    return False


def nome_do_item(link, indice):
    arquivo = os.path.basename(link.split("?")[0])
    arquivo = unquote(arquivo).replace("_", " ").replace("%20", " ")
    return arquivo or f"Stream {indice}"


def extrair_do_html(html, base_url, aceitar_mp4=True):
    streams = set()
    ignorados = set()

    for match in STREAM_PATTERN.findall(html):
        link = normalizar_link(match, base_url)
        if is_stream_iptv(link, aceitar_mp4=aceitar_mp4):
            streams.add(link)

    # Registra MKV encontrados só para diagnóstico, mas não coloca na playlist.
    for match in re.findall(r"https?://[^\"'<>\s]+?\.(?:mkv|avi|mov)(?:\?[^\"'<>\s]*)?", html, flags=re.IGNORECASE):
        ignorados.add(normalizar_link(match, base_url))

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "source", "video", "script"]):
        for attr in ["href", "src", "data-src", "data-url", "file"]:
            valor = tag.get(attr)
            if not valor:
                continue
            link = normalizar_link(valor, base_url)
            ext = extensao_do_link(link)
            if is_stream_iptv(link, aceitar_mp4=aceitar_mp4):
                streams.add(link)
            elif ext in IGNORED_EXTENSIONS:
                ignorados.add(link)

    return streams, ignorados, soup


def extrair_streams(url, aceitar_mp4=True):
    print(f"Acessando: {url}")
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()

    streams, ignorados, soup = extrair_do_html(response.text, url, aceitar_mp4=aceitar_mp4)

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if not src:
            continue

        iframe_url = normalizar_link(src, url)
        print(f"Verificando iframe: {iframe_url}")

        try:
            r2 = requests.get(iframe_url, headers={**HEADERS, "Referer": url}, timeout=20)
            encontrados, ignorados_iframe, _ = extrair_do_html(r2.text, iframe_url, aceitar_mp4=aceitar_mp4)
            streams.update(encontrados)
            ignorados.update(ignorados_iframe)
        except Exception as e:
            print(f"Não consegui ler iframe: {e}")

    # Ordena priorizando .m3u8 antes de .mp4
    ordenados = sorted(streams, key=lambda x: (0 if extensao_do_link(x) == ".m3u8" else 1, x))
    return ordenados, sorted(ignorados)


def gerar_m3u(lista, nome_arquivo="playlist.m3u"):
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, link in enumerate(lista, 1):
            titulo = nome_do_item(link, i)
            f.write(f"#EXTINF:-1 group-title=\"AnimeOut\",{titulo}\n{link}\n")

    print(f"{nome_arquivo} gerada com {len(lista)} item(ns)")


def gerar_ignorados(lista, nome_arquivo="ignored_download_files.txt"):
    if not lista:
        return
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        for link in lista:
            f.write(link + "\n")
    print(f"{nome_arquivo} gerado com {len(lista)} arquivo(s) ignorado(s), como MKV/AVI/MOV")


if __name__ == "__main__":
    url = input("Cole a URL: ").strip()
    aceitar_mp4_txt = input("Aceitar MP4 além de M3U8? [s/N]: ").strip().lower()
    aceitar_mp4 = aceitar_mp4_txt == "s"

    streams, ignorados = extrair_streams(url, aceitar_mp4=aceitar_mp4)

    if streams:
        print("\nStreams IPTV encontrados:")
        for s in streams:
            print(s)
        gerar_m3u(streams)
    else:
        print("Nenhum stream IPTV encontrado (.m3u8 ou .mp4 se habilitado).")

    if ignorados:
        print(f"\nArquivos ignorados por não serem ideais para IPTV: {len(ignorados)}")
        gerar_ignorados(ignorados)
