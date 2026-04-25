import requests


def main():
    print("=" * 50)
    print("ANIMEOUT - BAIXAR EPISÓDIO")
    print("=" * 50)

    url = input("Cole a URL do episódio: ").strip()

    if not url.startswith("http"):
        print("URL inválida.")
        return

    try:
        print("Baixando episódio...")
        response = requests.get(url)

        with open("episodio.mp4", "wb") as f:
            f.write(response.content)

        print("Download concluído: episodio.mp4")
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
