import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".m3u8")


def limpar_nome(nome):
    nome = unquote(nome)
    nome = re.sub(r"[\\/*?:\"<>|]", "_", nome)
    return nome.strip() or "animeout_download"


def normalizar_url(url):
    url = url.strip()
    # Evita URL colada duas vezes no formato ...?https://...
    pos = url.find("?http")
    if pos != -1:
        url = url[:pos]
    return url


def is_link_video(url):
    base = url.split("?")[0].lower()
    return any(base.endswith(ext) for ext in VIDEO_EXTENSIONS)


def montar_headers(url, referer=None):
    headers = DEFAULT_HEADERS.copy()
    parsed = urlparse(url)
    origem = f"{parsed.scheme}://{parsed.netloc}"
    headers["Referer"] = referer or origem + "/"
    headers["Origin"] = origem
    return headers


def coletar_links(url):
    print(f"Acessando página: {url}")
    response = requests.get(url, headers=montar_headers(url), timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for tag in soup.find_all(["a", "source", "video"], href=True):
        href = tag.get("href") or tag.get("src")
        if not href:
            continue
        texto = tag.get_text(" ", strip=True)
        link_final = urljoin(url, href.strip())
        if is_link_video(link_final):
            links.append({"titulo": texto or os.path.basename(link_final), "url": link_final})

    for tag in soup.find_all(["source", "video"], src=True):
        src = tag.get("src")
        link_final = urljoin(url, src.strip())
        if is_link_video(link_final):
            links.append({"titulo": os.path.basename(link_final), "url": link_final})

    vistos = set()
    unicos = []
    for item in links:
        if item["url"] not in vistos:
            vistos.add(item["url"])
            unicos.append(item)

    return unicos


def baixar_arquivo(url, pasta, nome=None, referer=None):
    os.makedirs(pasta, exist_ok=True)
    url = normalizar_url(url)

    nome_base = nome or os.path.basename(url.split("?")[0]) or "video"
    nome_arquivo = limpar_nome(nome_base)

    if "." not in os.path.basename(nome_arquivo):
        ext = os.path.splitext(url.split("?")[0])[1] or ".mp4"
        nome_arquivo += ext

    caminho = os.path.join(pasta, nome_arquivo)
    session = requests.Session()

    print(f"Baixando: {nome_arquivo}")
    with session.get(url, headers=montar_headers(url, referer), stream=True, timeout=60, allow_redirects=True) as r:
        if r.status_code == 403:
            print("Erro 403: servidor bloqueou download direto.")
            print("Use a opção 2 com a URL direta do arquivo e informe a URL da página original como Referer.")
            return False
        r.raise_for_status()
        with open(caminho, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)

    print(f"Salvo em: {caminho}")
    return True


def main():
    print("=" * 60)
    print("ANIMEOUT - BAIXAR ANIME COMPLETO")
    print("=" * 60)
    url = normalizar_url(input("Cole a URL da página do anime ou link direto do vídeo: ").strip())

    if not url.startswith("http"):
        print("URL inválida. Use uma URL completa começando com http ou https.")
        return

    pasta = input("Nome da pasta de saída [downloads]: ").strip() or "downloads"

    if is_link_video(url):
        referer = input("URL da página original/referer [opcional]: ").strip() or None
        try:
            baixar_arquivo(url, pasta, referer=referer)
        except Exception as e:
            print(f"Erro ao baixar arquivo direto: {e}")
        return

    try:
        links = coletar_links(url)
    except Exception as e:
        print(f"Erro ao coletar links: {e}")
        return

    if not links:
        print("Nenhum link direto de vídeo foi encontrado nessa página.")
        print("Dica: cole diretamente uma URL .mp4, .mkv ou .m3u8.")
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
            baixar_arquivo(item["url"], pasta, f"episodio_{i}", referer=url)
        except Exception as e:
            print(f"Erro ao baixar item {i}: {e}")


if __name__ == "__main__":
    main()
