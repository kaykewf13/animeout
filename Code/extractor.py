import asyncio
from playwright.async_api import async_playwright

async def extrair_streams(url):
    streams = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def handle_response(response):
            if any(ext in response.url for ext in [".m3u8", ".mp4", ".mkv"]):
                streams.append(response.url)

        page.on("response", handle_response)

        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(5000)

        await browser.close()

    return list(set(streams))


def gerar_m3u(lista, nome_arquivo="playlist.m3u"):
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, link in enumerate(lista, 1):
            f.write(f"#EXTINF:-1,Anime {i}\n{link}\n")

    print(f"Playlist gerada: {nome_arquivo}")


if __name__ == "__main__":
    url = input("Cole a URL da página do player: ")
    streams = asyncio.run(extrair_streams(url))

    if streams:
        print("\nStreams encontrados:")
        for s in streams:
            print(s)

        gerar_m3u(streams)
    else:
        print("Nenhum stream encontrado.")
