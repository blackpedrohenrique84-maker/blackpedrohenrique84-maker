#!/usr/bin/env python3
"""Gera o bloco de estatisticas em ASCII e injeta no README.md."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
W = 60          # largura da caixa
BAR = 22        # largura das barras


def get(url):
    if url.startswith("/"):
        url = API + url
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ascii-stats"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def count_prs():
    q = urllib.parse.quote(f"author:{USER} type:pr")
    try:
        return get(f"/search/issues?q={q}&per_page=1")["total_count"]
    except Exception:
        return None


def collect():
    user = get(f"/users/{USER}")
    repos = get(f"/users/{USER}/repos?per_page=100&type=owner")
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        try:
            for name, size in get(r["languages_url"]).items():
                langs[name] = langs.get(name, 0) + size
        except Exception:
            pass
    return {
        "repos": user["public_repos"],
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "prs": count_prs(),
        "langs": langs,
    }


def row(text=""):
    return ("| " + text).rstrip()


def pair(a, av, b, bv):
    left = f"{a} ".ljust(19, ".") + f" {av}"
    right = f"{b} ".ljust(19, ".") + f" {bv}"
    return row(left.ljust(27) + right)


def render(d):
    lines = ["+-[ números ]" + "-" * (W - 13)]
    lines.append(row())
    prs = "?" if d["prs"] is None else d["prs"]
    lines.append(pair("repositórios", d["repos"], "estrelas", d["stars"]))
    lines.append(pair("seguidores", d["followers"], "pull requests", prs))
    lines.append(row())
    lines.append(row("linguagens (bytes de código)"))
    total = sum(d["langs"].values())
    if total:
        top = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:5]
        for name, size in top:
            pct = size / total * 100
            n = round(pct / 100 * BAR)
            bar = "#" * n + "." * (BAR - n)
            lines.append(row(f"  {name[:12].ljust(12)} [{bar}] {pct:5.1f}%"))
    else:
        lines.append(row("  sem dados ainda"))
    lines.append(row())
    lines.append("+" + "-" * (W - 1))
    return "\n".join(lines)


def main():
    if not USER:
        sys.exit("defina GH_USER")
    block = "```text\n" + render(collect()) + "\n```"
    with open("README.md", encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(r"<!-- STATS:START -->.*?<!-- STATS:END -->", re.S)
    if not pattern.search(text):
        sys.exit("marcadores STATS:START / STATS:END não encontrados no README.md")
    new = pattern.sub(lambda m: f"<!-- STATS:START -->\n{block}\n<!-- STATS:END -->", text)
    if new != text:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new)
    print(block)


if __name__ == "__main__":
    main()
