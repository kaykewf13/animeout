import os
import re
import requests
from urllib.parse import urlparse

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


def limpar_nome(nome):
    nome = re.sub(r"[\\/*?:\"<>|]", "_", nome)
    return nome.strip() or "episodio"


def montar_headers(url, referer=None):
    headers = DEFAULT_HEADERS.copy()
    headers["Referer"] = referer or f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    headers["Origin"] = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    return headers


def baixar(url, arquivo_saida="episodio.mp4", referer=None):
    session = requests.Session()
    headers = montar_headers(url, referer)

    response = session.get(url, headers=headers, stream=True, timeout=40, allow_redirects=True)

    if response.status_code == 403:
        print("Erro 403: o servidor bloqueou o download direto.")
        print("Possíveis causas: link temporário expirado, proteção por player, necessidade de cookie/login ou referer específico.")
        print("Tente copiar o link direto do vídeo pelo navegador ou informe a URL da página original como Referer.")
        return False

    response.raise_for_status()

    with open(arquivo_saida, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 512):
            if chunk:
                f.write(chunk)

    print(f"Download concluído: {arquivo_saida}")
    return True


def main():
    print("=" * 50)
    print("ANIMEOUT - BAIXAR EPISÓDIO")
    print("=" * 50)

    url = input("Cole a URL direta do episódio/vídeo: ").strip()
    if not url.startswith("http"):
        print("URL inválida.")
        return

    referer = input("Cole a URL da página original do episódio [opcional]: ").strip() or None
    nome = input("Nome do arquivo de saída [episodio.mp4]: ").strip() or "episodio.mp4"
    nome = limpar_nome(nome)

    if "." not in os.path.basename(nome):
        nome += ".mp4"

    try:
        baixar(url, nome, referer)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
