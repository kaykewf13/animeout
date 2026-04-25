import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".m3u8")


def limpar_nome(nome):
    nome = re.sub(r"[\\/*?:\"<>|]", "_", nome)
    return nome.strip() or "animeout_download"


def coletar_links(url):
    print(f"Acessando: {url}")
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        texto = tag.get_text(" ", strip=True)
        link_final = urljoin(url, href)

        if any(ext in link_final.lower() for ext in VIDEO_EXTENSIONS):
            links.append({
                "titulo": texto or os.path.basename(link_final),
                "url": link_final
            })

    vistos = set()
    unicos = []
    for item in links:
        if item["url"] not in vistos:
            vistos.add(item["url"])
            unicos.append(item)

    return unicos


def baixar_arquivo(url, pasta, nome=None):
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo = limpar_nome(nome or os.path.basename(url.split("?")[0]) or "video")

    if "." not in os.path.basename(nome_arquivo):
        nome_arquivo += ".mp4"

    caminho = os.path.join(pasta, nome_arquivo)

    print(f"Baixando: {nome_arquivo}")
    with requests.get(url, headers=HEADERS, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(caminho, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    print(f"Salvo em: {caminho}")


def main():
    print("=" * 60)
    print("ANIMEOUT - BAIXAR ANIME COMPLETO")
    print("=" * 60)
    url = input("Cole a URL da página do anime: ").strip()

    if not url.startswith("http"):
        print("URL inválida. Use uma URL completa começando com http ou https.")
        return

    pasta = input("Nome da pasta de saída [downloads]: ").strip() or "downloads"

    try:
        links = coletar_links(url)
    except Exception as e:
        print(f"Erro ao coletar links: {e}")
        return

    if not links:
        print("Nenhum link direto de vídeo foi encontrado nessa página.")
        print("Dica: use uma página que contenha links diretos .mp4, .mkv ou .m3u8.")
        return

    print(f"\nEncontrados {len(links)} links de vídeo:\n")
    for i, item in enumerate(links, 1):
        print(f"{i}. {item['titulo']} - {item['url']}")

    confirmar = input("\nDeseja baixar todos? (s/n): ").strip().lower()
    if confirmar != "s":
        print("Download cancelado.")
        return

    for i, item in enumerate(links, 1):
        try:
            baixar_arquivo(item["url"], pasta, f"episodio_{i}")
        except Exception as e:
            print(f"Erro ao baixar item {i}: {e}")


if __name__ == "__main__":
    main()
