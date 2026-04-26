import requests

def validar_stream(url):
    try:
        r = requests.get(url, timeout=5, stream=True)

        if r.status_code != 200:
            return False

        content_type = r.headers.get("Content-Type", "")

        if "video" in content_type or "mpegurl" in content_type:
            return True

        return False

    except:
        return False