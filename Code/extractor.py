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

VIDEO_PATTERN = re.compile(r"https?://[^\"'<>\s]+?\.(?:m3u8|mp4|mkv)(?:\?[^\"'<>\s]*)?", re.IGNORECASE)
VIDEO_EXTENSIONS = (".m3u8", ".mp4", ".mkv")


def normalizar_link(link, base_url):
    link = unquote(link.strip())
    return urljoin(base_url, link)


def nome_do_item(link, indice):
    arquivo = os.path.basename(link.split("?")[0])
    arquivo = unquote(arquivo).replace("_", " ").replace("%20", " ")
    return arquivo or f"Anime {indice}"


def extrair_do_html(html, base_url):
    streams = set()

    for match in VIDEO_PATTERN.findall(html):
        streams.add(normalizar_link(match, base_url))

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "source", "video", "script" ]):
        for attr in ["href", "src", "data-src", "data-url", "file"]:
            valor = tag.get(attr)
            if valor and any(ext in valor.lower() for ext in VIDEO_EXTENSIONS):
                streams.add(normalizar_link(valor, base_url))

    return streams, soup


def extrair_streams(url):
    print(f"Acessando: {url}")
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()

    streams, soup = extrair_do_html(response.text, url)

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if not src:
            continue

        iframe_url = normalizar_link(src, url)
        print(f"Verificando iframe: {iframe_url}")

        try:
            r2 = requests.get(iframe_url, headers={**HEADERS, "Referer": url}, timeout=20)
            encontrados, _ = extrair_do_html(r2.text, iframe_url)
            streams.update(encontrados)
        except Exception as e:
            print(f"Não consegui ler iframe: {e}")

    return sorted(streams)


def gerar_m3u(lista, nome_arquivo="playlist.m3u"):
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, link in enumerate(lista, 1):
            titulo = nome_do_item(link, i)
            f.write(f"#EXTINF:-1 group-title=\"AnimeOut\",{titulo}\n{link}\n")

    print(f"{nome_arquivo} gerada com {len(lista)} item(ns)")


if __name__ == "__main__":
    url = input("Cole a URL: ").strip()
    streams = extrair_streams(url)

    if streams:
        print("\nStreams encontrados:")
        for s in streams:
            print(s)
        gerar_m3u(streams)
    else:
        print("Nenhum stream encontrado")
