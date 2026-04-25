import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.animeout.xyz"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

def buscar_anime(nome):
    query = nome.replace(" ", "+")
    url = f"{BASE_URL}/?s={query}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        resultados = []
        # AnimeOut usa post entries com classe 'post'
        posts = soup.find_all("article") or soup.find_all("div", class_="post")

        for post in posts[:10]:
            titulo_tag = post.find("h2") or post.find("h3") or post.find("a")
            if titulo_tag:
                link = titulo_tag.find("a") if titulo_tag.name != "a" else titulo_tag
                if link and link.get("href"):
                    resultados.append({
                        "titulo": link.get_text(strip=True),
                        "url": link["href"]
                    })
        return resultados
    except Exception as e:
        print(f"Erro ao buscar: {e}")
        return []

def main():
    print("=" * 50)
    print("   ANIMEOUT - BUSCA DE ANIME")
    print("=" * 50)
    nome = input("\nDigite o nome do anime: ").strip()

    if not nome:
        print("Nome inválido.")
        return

    print(f"\nBuscando por '{nome}'...\n")
    resultados = buscar_anime(nome)

    if not resultados:
        print("Nenhum resultado encontrado.")
        print(f"Tente buscar manualmente em: {BASE_URL}/?s={nome.replace(' ', '+')}")
        return

    print(f"{'N°':<5} {'Título':<50} URL")
    print("-" * 80)
    for i, item in enumerate(resultados, 1):
        print(f"{i:<5} {item['titulo'][:48]:<50} {item['url']}")

    print("\nCopie a URL desejada e use nas opções 2 ou 3 do menu principal.")

if __name__ == "__main__":
    main()
