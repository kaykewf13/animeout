import csv
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

OUTPUT_FILE = "sources/github_vod_discovered.csv"
LOG_FILE = "logs/github_vod_discovery_summary.csv"
MAX_REPOS_PER_QUERY = int(os.getenv("GITHUB_VOD_MAX_REPOS", "8"))
MAX_FILES_PER_REPO = int(os.getenv("GITHUB_VOD_MAX_FILES", "15"))
TIMEOUT = 30
STREAM_RE = re.compile(r'https?://[^\s"\'<>]+?\.(?:m3u8|mp4|ts)(?:\?[^\s"\'<>]*)?', re.I)
M3U_FILE_RE = re.compile(r'\.(m3u8?|txt)$', re.I)

SEARCH_QUERIES = [
    'vod m3u8 playlist anime',
    'anime vod m3u8',
    'iptv vod anime m3u',
    'm3u8 vod playlist',
    'movie vod m3u8 playlist',
]


def headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "animeout-vod-discovery"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def cutoff_date():
    return (datetime.now(timezone.utc) - timedelta(days=183)).date().isoformat()


def gh_get(url):
    r = requests.get(url, headers=headers(), timeout=TIMEOUT)
    if r.status_code in [403, 429]:
        print(f"Rate limit/blocked on GitHub: {r.status_code}. {url}")
        return None
    if r.status_code >= 400:
        print(f"GitHub request failed {r.status_code}: {url}")
        return None
    return r.json()


def search_repos(query):
    q = f"{query} pushed:>{cutoff_date()}"
    url = f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&order=desc&per_page={MAX_REPOS_PER_QUERY}"
    data = gh_get(url)
    if not data:
        return []
    return data.get("items", [])


def get_tree(repo_full_name, branch):
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{quote(branch)}?recursive=1"
    data = gh_get(url)
    if not data:
        return []
    return data.get("tree", [])


def raw_url(repo_full_name, branch, path):
    return f"https://raw.githubusercontent.com/{repo_full_name}/{branch}/{path}"


def detect_group(path, content, repo_name):
    text = f"{path} {repo_name} {content[:4000]}".lower()
    if any(w in text for w in ["movie", "movies", "filme", "filmes"]):
        return "Filmes"
    return "Series"


def detect_category(path, repo_name):
    text = f"{path} {repo_name}".lower()
    if "anime" in text:
        return "Anime"
    if "movie" in text or "filme" in text:
        return "Filmes"
    if "series" in text or "serie" in text:
        return "Series"
    return "VOD GitHub"


def clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def get_attr(line, attr):
    m = re.search(rf'{attr}="([^"]*)"', line)
    return m.group(1).strip() if m else ""


def parse_m3u(content, repo_full_name, file_path):
    items = []
    current = None
    category_default = detect_category(file_path, repo_full_name)
    group_default = detect_group(file_path, content, repo_full_name)

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            title = clean(line.split(",", 1)[-1] if "," in line else "VOD GitHub")
            group_title = clean(get_attr(line, "group-title") or category_default)
            logo = clean(get_attr(line, "tvg-logo"))
            current = {
                "grupo": group_default,
                "categoria": group_title or category_default,
                "titulo": title,
                "url": "",
                "logo": logo,
                "fonte": f"github:{repo_full_name}:{file_path}",
            }
        elif line.startswith("http") and current:
            if STREAM_RE.search(line):
                current["url"] = line
                items.append(current)
            current = None

    if not items:
        for url in sorted(set(STREAM_RE.findall(content))):
            items.append({
                "grupo": group_default,
                "categoria": category_default,
                "titulo": guess_title(url),
                "url": url,
                "logo": "",
                "fonte": f"github:{repo_full_name}:{file_path}",
            })
    return items


def guess_title(url):
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    name = re.sub(r"\.(m3u8|mp4|ts)$", "", name, flags=re.I)
    name = re.sub(r"[_\-.]+", " ", name)
    return clean(name).title() or "VOD GitHub"


def fetch_text(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "animeout-vod-discovery"})
        if r.status_code >= 400:
            return ""
        if len(r.text) > 3_000_000:
            return r.text[:3_000_000]
        return r.text
    except Exception:
        return ""


def discover():
    discovered = []
    summary = []
    seen_repos = set()

    for query in SEARCH_QUERIES:
        repos = search_repos(query)
        for repo in repos:
            full_name = repo.get("full_name")
            if not full_name or full_name in seen_repos:
                continue
            seen_repos.add(full_name)
            branch = repo.get("default_branch") or "main"
            tree = get_tree(full_name, branch)
            files = [x.get("path") for x in tree if x.get("type") == "blob" and M3U_FILE_RE.search(x.get("path", ""))]
            files = files[:MAX_FILES_PER_REPO]
            repo_count = 0
            for path in files:
                content = fetch_text(raw_url(full_name, branch, path))
                if not content:
                    continue
                items = parse_m3u(content, full_name, path)
                discovered.extend(items)
                repo_count += len(items)
                time.sleep(0.2)
            summary.append({"repo": full_name, "query": query, "files_checked": len(files), "items": repo_count})
            time.sleep(0.5)
    return discovered, summary


def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    items, summary = discover()
    seen = set()
    unique = []
    for item in items:
        key = (item["grupo"], item["titulo"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    write_csv(OUTPUT_FILE, unique, ["grupo", "categoria", "titulo", "url", "logo", "fonte"])
    write_csv(LOG_FILE, summary, ["repo", "query", "files_checked", "items"])
    print(f"GitHub VOD discovery: {len(unique)} stream(s) direto(s) encontrados")


if __name__ == "__main__":
    main()
