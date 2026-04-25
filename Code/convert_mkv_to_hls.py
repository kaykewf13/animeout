import argparse
import csv
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse


def slugify(value):
    value = unquote(value or "video")
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-_\.]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "video"


def detectar_nome_origem(origem, index):
    parsed = urlparse(origem)
    if parsed.scheme in ["http", "https"]:
        base = os.path.basename(parsed.path) or f"video_{index}"
    else:
        base = os.path.basename(origem) or f"video_{index}"

    nome_sem_ext = os.path.splitext(base)[0]
    return slugify(nome_sem_ext or f"video_{index}")


def ffmpeg_disponivel():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def converter_para_hls(origem, saida_base="hls_output", index=1, codec_mode="copy"):
    titulo = detectar_nome_origem(origem, index)
    pasta_saida = Path(saida_base) / titulo
    pasta_saida.mkdir(parents=True, exist_ok=True)

    playlist_path = pasta_saida / "playlist.m3u8"
    segment_pattern = pasta_saida / "seg_%05d.ts"

    if codec_mode == "transcode":
        video_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k"]
    else:
        # Mais rápido: copia vídeo e converte áudio para AAC quando necessário.
        video_args = ["-c:v", "copy", "-c:a", "aac", "-b:a", "128k"]

    cmd = [
        "ffmpeg",
        "-y",
        "-i", origem,
        *video_args,
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(segment_pattern),
        str(playlist_path),
    ]

    print(f"\nConvertendo: {origem}")
    print(f"Saída: {playlist_path}")

    try:
        subprocess.run(cmd, check=True)
        return {
            "titulo": titulo,
            "origem": origem,
            "playlist_local": str(playlist_path),
            "status": "OK",
            "erro": "",
        }
    except subprocess.CalledProcessError as e:
        return {
            "titulo": titulo,
            "origem": origem,
            "playlist_local": str(playlist_path),
            "status": "ERRO",
            "erro": str(e),
        }


def ler_origens(args):
    origens = []

    if args.input:
        origens.append(args.input)

    if args.list and os.path.exists(args.list):
        with open(args.list, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith("#"):
                    origens.append(linha)

    # Fallback padrão: usa o arquivo gerado pelo extractor quando existir.
    if not origens and os.path.exists("ignored_download_files.txt"):
        with open("ignored_download_files.txt", "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                linha = linha.strip()
                if linha and linha.lower().split("?")[0].endswith(".mkv"):
                    origens.append(linha)

    # Remove duplicados mantendo ordem.
    vistos = set()
    unicos = []
    for item in origens:
        if item not in vistos:
            vistos.add(item)
            unicos.append(item)

    return unicos


def gerar_manifesto(resultados, caminho="hls_manifest.csv"):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["titulo", "origem", "playlist_local", "status", "erro"])
        writer.writeheader()
        writer.writerows(resultados)
    print(f"\nManifesto gerado: {caminho}")


def gerar_playlist_local(resultados, caminho="converted_hls_local.m3u"):
    ok = [r for r in resultados if r["status"] == "OK"]
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for r in ok:
            f.write(f"#EXTINF:-1 group-title=\"Series | Convertidos\",{r['titulo']}\n{r['playlist_local']}\n")
    print(f"Playlist local gerada: {caminho} ({len(ok)} item(ns))")


def main():
    parser = argparse.ArgumentParser(description="Converte arquivos MKV autorizados para HLS/M3U8 usando ffmpeg.")
    parser.add_argument("--input", help="Arquivo local ou URL direta MKV autorizada.")
    parser.add_argument("--list", help="Arquivo .txt com uma origem MKV por linha.")
    parser.add_argument("--output", default="hls_output", help="Pasta base de saída. Padrão: hls_output")
    parser.add_argument("--codec-mode", choices=["copy", "transcode"], default="copy", help="copy é mais rápido; transcode é mais compatível.")
    args = parser.parse_args()

    if not ffmpeg_disponivel():
        print("ffmpeg não encontrado.")
        print("Instale com: sudo apt update && sudo apt install ffmpeg -y")
        return

    origens = ler_origens(args)

    if not origens:
        print("Nenhum MKV encontrado para converter.")
        print("Use uma das opções:")
        print("  python Code/convert_mkv_to_hls.py --input arquivo.mkv")
        print("  python Code/convert_mkv_to_hls.py --list ignored_download_files.txt")
        return

    print(f"Encontradas {len(origens)} origem(ns) para conversão.")
    resultados = []

    for i, origem in enumerate(origens, 1):
        resultados.append(converter_para_hls(origem, args.output, i, args.codec_mode))

    gerar_manifesto(resultados)
    gerar_playlist_local(resultados)

    print("\nResumo:")
    print(f"OK: {sum(1 for r in resultados if r['status'] == 'OK')}")
    print(f"ERRO: {sum(1 for r in resultados if r['status'] != 'OK')}")
    print("\nObservação: para usar em IPTV fora do ambiente local, hospede a pasta hls_output em um servidor/CDN e use URLs HTTP/HTTPS no M3U.")


if __name__ == "__main__":
    main()
