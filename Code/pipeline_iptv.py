def detectar_tipo(item):
    url = item["stream_url"].lower()
    titulo = item["titulo"].lower()
    fonte = item.get("fonte", "").lower()

    # 🔴 CANAIS (LIVE / FAST)
    if any(x in url for x in [
        "pluto", "rakuten", "amagi", "wurl", "stitch",
        "free-tv", "channel", "live"
    ]):
        return "CANAIS"

    if "iptv-org" in fonte:
        return "CANAIS"

    if url.endswith(".ts"):
        return "CANAIS"

    # 🎬 VOD REAL
    if url.endswith(".mp4"):
        return "VOD"

    # ⚠️ .m3u8 precisa de contexto
    if ".m3u8" in url:
        if any(x in titulo for x in ["ep", "episodio", "s01", "s02"]):
            return "VOD"
        return "CANAIS"

    return "INVALIDO"