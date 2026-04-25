import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def extrair_streams(url):
    print(f"Acessando: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    html = r.text

    streams = set()

    # Buscar links diretos
    for match in re.findall(r"https?://[^\"' ]+\.(m3u8|mp4|mkv)", html):
        streams.add(match)

    soup = BeautifulSoup(html, "html.parser")

    # Buscar em iframes
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            print(f"Verificando iframe: {src}")
            try:
                r2 = requests.get(src, headers=HEADERS, timeout=10)
                html2 = r2.text
                for match in re.findall(r"https?://[^\"' ]+\.(m3u8|mp4|mkv)", html2):
                    streams.add(match)
            except:
                pass

    return list(streams)


def gerar_m3u(lista):
    with open("playlist.m3u", "w") as f:
        f.write("#EXTM3U\n")
        for i, link in enumerate(lista, 1):
            f.write(f"#EXTINF:-1,Anime {i}\n{link}\n")

    print("playlist.m3u gerada")


if __name__ == "__main__":
    url = input("Cole a URL: ")
    streams = extrair_streams(url)

    if streams:
        print("Streams encontrados:")
        for s in streams:
            print(s)
        gerar_m3u(streams)
    else:
        print("Nenhum stream encontrado")
