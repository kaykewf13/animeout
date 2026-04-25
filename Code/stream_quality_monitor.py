import requests
import json
import time
from pathlib import Path

INPUT = "web/catalog.json"
OUTPUT = "web/catalog.json"
TIMEOUT = 6
MAX_CHECK = 200


def check_stream(url):
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        return r.status_code == 200
    except:
        return False


def main():
    if not Path(INPUT).exists():
        print("catalog.json não encontrado")
        return

    with open(INPUT, encoding="utf-8") as f:
        items = json.load(f)

    checked = 0
    valid = []

    for item in items:
        if checked >= MAX_CHECK:
            valid.append(item)
            continue

        url = item.get("url")
        if not url:
            continue

        ok = check_stream(url)
        checked += 1

        if ok:
            item["quality"] = "ok"
            item["score"] = (item.get("score") or 0) + 20
            valid.append(item)
        else:
            item["quality"] = "bad"

        time.sleep(0.1)

    valid.sort(key=lambda x: -(x.get("score") or 0))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(valid, f, ensure_ascii=False, indent=2)

    print(f"Streams validados: {checked} | válidos: {len(valid)}")


if __name__ == "__main__":
    main()
