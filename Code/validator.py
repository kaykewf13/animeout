import csv
import os
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

VALID_CONTENT_HINTS = [
    "video",
    "mpegurl",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/octet-stream",
    "binary",
]

TIMEOUT_SECONDS = 8


def ler_playlist(caminho="playlist.m3u"):
    if not os.path.exists(caminho):
        print(f"Arquivo não encontrado: {caminho}")
        return []

    itens = []
    titulo_atual = "Sem título"

    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue

            if linha.startswith("#EXTINF"):
                titulo_atual = linha.split(",", 1)[-1].strip() if "," in linha else "Sem título"
            elif linha.startswith("http"):
                itens.append({"titulo": titulo_atual, "url": linha})

    return itens


def validar_m3u8(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        status = r.status_code
        content_type = r.headers.get("content-type", "").lower()
        texto = r.text[:500] if r.text else ""

        if status == 200 and "#EXTM3U" in texto:
            return True, status, content_type, "m3u8 válido"

        if status == 200 and "#EXT" in texto:
            return True, status, content_type, "playlist HLS provável"

        return False, status, content_type, "m3u8 não contém #EXTM3U"
    except Exception as e:
        return False, "ERROR", "", str(e)


def validar_video(url):
    try:
        headers = HEADERS.copy()
        headers["Range"] = "bytes=0-1024"

        r = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=True)
        status = r.status_code
        content_type = r.headers.get("content-type", "").lower()
        content_length = r.headers.get("content-length", "")

        if status in [200, 206]:
            if any(hint in content_type for hint in VALID_CONTENT_HINTS):
                return True, status, content_type, f"vídeo provável; bytes={content_length}"

            if url.lower().split("?")[0].endswith((".mp4", ".mkv", ".avi", ".mov")):
                return True, status, content_type, f"extensão de vídeo respondeu; bytes={content_length}"

        return False, status, content_type, f"resposta não compatível; bytes={content_length}"
    except Exception as e:
        return False, "ERROR", "", str(e)


def validar_link(url):
    url_limpa = url.lower().split("?")[0]

    if url_limpa.endswith(".m3u8"):
        return validar_m3u8(url)

    return validar_video(url)


def gerar_validos(validos, caminho="valid_links.m3u"):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in validos:
            f.write(f"#EXTINF:-1 group-title=\"AnimeOut\",{item['titulo']}\n{item['url']}\n")

    print(f"Arquivo gerado: {caminho} ({len(validos)} link(s) válido(s))")


def gerar_invalidos(invalidos, caminho="invalid_links.csv"):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["titulo", "url", "status", "content_type", "motivo"])
        writer.writeheader()
        for item in invalidos:
            writer.writerow(item)

    print(f"Arquivo gerado: {caminho} ({len(invalidos)} link(s) inválido(s))")


def salvar_parcial(validos, invalidos):
    print("\nSalvando progresso parcial...")
    gerar_validos(validos)
    gerar_invalidos(invalidos)
    print("Progresso salvo. Você pode continuar depois rodando novamente.")


def main():
    playlist = input("Arquivo M3U para validar [playlist.m3u]: ").strip() or "playlist.m3u"
    itens = ler_playlist(playlist)

    if not itens:
        print("Nenhum link encontrado para validar.")
        return

    limite_txt = input(f"Quantos links validar? [Enter = todos / sugestão teste = 20]: ").strip()
    if limite_txt:
        try:
            limite = int(limite_txt)
            itens = itens[:limite]
        except ValueError:
            print("Limite inválido. Vou validar todos.")

    validos = []
    invalidos = []

    print(f"Validando {len(itens)} link(s)...")
    print("Dica: pressione Ctrl+C para pausar e salvar o progresso parcial.\n")

    try:
        for i, item in enumerate(itens, 1):
            print(f"[{i}/{len(itens)}] Validando: {item['titulo']}")
            ok, status, content_type, motivo = validar_link(item["url"])

            if ok:
                print(f"  OK | status={status} | {motivo}")
                validos.append(item)
            else:
                print(f"  FALHOU | status={status} | {motivo}")
                invalidos.append({
                    "titulo": item["titulo"],
                    "url": item["url"],
                    "status": status,
                    "content_type": content_type,
                    "motivo": motivo,
                })
    except KeyboardInterrupt:
        salvar_parcial(validos, invalidos)
        return

    print("\nResumo:")
    print(f"Válidos: {len(validos)}")
    print(f"Inválidos: {len(invalidos)}")

    gerar_validos(validos)
    gerar_invalidos(invalidos)


if __name__ == "__main__":
    main()
