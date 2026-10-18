#!/usr/bin/env python3
"""Generate assets/card.svg: an animated neofetch-style terminal card from live GitHub data.

Uses only the public GraphQL API plus the contribution counts GitHub exposes
(private commits are counted anonymously if the profile setting allows it).
Auth: GITHUB_TOKEN env var, falls back to `gh auth token` for local runs.
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import date
from html import escape

USER = os.environ.get("GH_USER", "rahuloruganti")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "card.svg")

QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    all:repositories(ownerAffiliations:OWNER, privacy:PUBLIC){ totalCount }
    repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
      nodes{
        stargazerCount
        languages(first:6, orderBy:{field:SIZE, direction:DESC}){
          edges{size node{name color}}
        }
      }
    }
    contributionsCollection{
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount}}
      }
    }
  }
}
"""


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token()}", "User-Agent": "profile-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def streaks(days):
    """days: list of (date, count) oldest->newest. Returns (current, longest)."""
    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    cur = 0
    for i, (_, c) in enumerate(reversed(days)):
        if c > 0:
            cur += 1
        elif i == 0:  # today may still be empty
            continue
        else:
            break
    return cur, longest


def level(c, mx):
    if c <= 0:
        return 0
    q = c / mx
    return 1 if q <= 0.25 else 2 if q <= 0.5 else 3 if q <= 0.75 else 4


def main():
    u = fetch()
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    public_repos = u["all"]["totalCount"]
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])

    # ---- heatmap: last 26 weeks -------------------------------------------------
    weeks = cal["weeks"][-26:]
    mx = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1) or 1
    heat_colors = ["#24283b", "#1c4b3b", "#2a7a4b", "#3fb36a", "#9ece6a"]
    cells = []
    for wi, w in enumerate(weeks):
        for di, d in enumerate(w["contributionDays"]):
            lv = level(d["contributionCount"], mx)
            x, y = 34 + wi * 13, 150 + di * 13
            delay = round(0.9 + wi * 0.05 + di * 0.01, 2)
            cells.append(
                f'<rect class="cell" style="animation-delay:{delay}s" x="{x}" y="{y}" '
                f'width="10" height="10" rx="2" fill="{heat_colors[lv]}">'
                f'<title>{escape(d["date"])}: {d["contributionCount"]}</title></rect>'
            )

    # ---- contribution-mix bars (works with private activity, no PAT needed) -------
    private_c = cc["restrictedContributionsCount"]
    commits = cc["totalCommitContributions"] + private_c
    mix = [
        ("commits", commits, "#9ece6a"),
        ("pull requests", cc["totalPullRequestContributions"], "#7aa2f7"),
        ("reviews", cc["totalPullRequestReviewContributions"], "#bb9af7"),
        ("issues", cc["totalIssueContributions"], "#ff9e64"),
    ]
    mmax = max(v for _, v, _ in mix) or 1
    bars = []
    bar_w = 215
    for i, (name, val, color) in enumerate(mix):
        y = 292 + i * 24
        w = max(4, round(bar_w * val / mmax)) if val else 4
        bars.append(
            f'<text x="34" y="{y + 9}" class="dim">{escape(name)}</text>'
            f'<rect x="130" y="{y}" width="{bar_w}" height="10" rx="5" fill="#24283b"/>'
            f'<rect class="bar" style="animation-delay:{1.8 + i * 0.15}s" x="130" y="{y}" '
            f'width="{w}" height="10" rx="5" fill="{color}"/>'
            f'<text x="{130 + bar_w + 10}" y="{y + 9}" class="dim">{val:,}</text>'
        )

    info = [
        ("role", "AI & Mitigation intern @ UNFCCC"),
        ("edu", "MS Artificial Intelligence @ BTU Cottbus"),
        ("loc", "Cottbus, Germany"),
        ("focus", "RAG · LLM eval · agents · automation"),
        ("repos", f"{public_repos} public repos  ·  {u['followers']['totalCount']} followers" + (f"  ·  {stars} stars" if stars else "")),
        ("commits", f"{commits:,} in the last year"),
        ("prs", f"{cc['totalPullRequestContributions']} pull requests  ·  {cc['totalIssueContributions']} issues"),
        ("streak", f"{cur} days now  ·  {longest} best"),
    ]
    info_svg = []
    for i, (k, v) in enumerate(info):
        y = 150 + i * 24
        info_svg.append(
            f'<g class="line" style="animation-delay:{1.0 + i * 0.22:.2f}s">'
            f'<text x="440" y="{y}" class="key">{escape(k)}</text>'
            f'<text x="520" y="{y}" class="val">{escape(v)}</text></g>'
        )

    palette = ["#f7768e", "#ff9e64", "#e0af68", "#9ece6a", "#7dcfff", "#7aa2f7", "#bb9af7"]
    pal_svg = "".join(
        f'<rect class="line" style="animation-delay:{3.2 + i * 0.08:.2f}s" x="{440 + i * 30}" y="{150 + 8 * 24 + 4}" '
        f'width="26" height="14" rx="3" fill="{c}"/>'
        for i, c in enumerate(palette)
    )

    updated = date.today().isoformat()
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="430" viewBox="0 0 860 430" role="img" aria-label="GitHub stats terminal card for {USER}">
<style>
  text {{ font-family: 'Fira Code','JetBrains Mono',Consolas,Menlo,monospace; font-size: 13px; }}
  .title {{ fill:#565f89; font-size:12px }}
  .prompt {{ fill:#9ece6a; font-weight:700 }}
  .cmd {{ fill:#c0caf5 }}
  .head {{ fill:#7aa2f7; font-weight:700; font-size:15px }}
  .rule {{ fill:#3b4261 }}
  .key {{ fill:#bb9af7; font-weight:700 }}
  .val {{ fill:#a9b1d6 }}
  .dim {{ fill:#7982a9; font-size:12px }}
  .sect {{ fill:#ff9e64; font-weight:700 }}
  .line {{ opacity:0; animation: appear .35s ease-out forwards }}
  .cell {{ opacity:0; animation: pop .4s ease-out forwards }}
  .bar {{ transform-box: fill-box; transform-origin: left center; transform: scaleX(0); animation: grow .8s cubic-bezier(.2,.8,.2,1) forwards }}
  .cursor {{ fill:#c0caf5; animation: blink 1.1s steps(1) infinite }}
  .glow {{ animation: pulse 3s ease-in-out infinite }}
  @keyframes appear {{ from {{ opacity:0; transform: translateX(-6px) }} to {{ opacity:1; transform:none }} }}
  @keyframes pop {{ 0% {{ opacity:0; transform: scale(.2) }} 100% {{ opacity:1; transform:none }} }}
  @keyframes grow {{ to {{ transform: scaleX(1) }} }}
  @keyframes blink {{ 50% {{ opacity:0 }} }}
  @keyframes pulse {{ 0%,100% {{ opacity:.55 }} 50% {{ opacity:1 }} }}
  @keyframes type {{ to {{ transform: scaleX(0) }} }}
  #typer {{ transform-box: fill-box; transform-origin: right center; animation: type .9s steps(24) .2s forwards }}
</style>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#1a1b27"/><stop offset="1" stop-color="#16161e"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#7aa2f7"/><stop offset=".5" stop-color="#bb9af7"/><stop offset="1" stop-color="#f7768e"/>
  </linearGradient>
</defs>
<rect x="1" y="1" width="858" height="428" rx="14" fill="url(#bg)"/>
<rect x="1" y="1" width="858" height="428" rx="14" fill="none" stroke="url(#edge)" stroke-width="2" class="glow"/>
<rect x="1" y="1" width="858" height="36" rx="14" fill="#1f2335"/>
<rect x="1" y="22" width="858" height="15" fill="#1f2335"/>
<circle cx="24" cy="19" r="6" fill="#f7768e"/><circle cx="44" cy="19" r="6" fill="#e0af68"/><circle cx="64" cy="19" r="6" fill="#9ece6a"/>
<text x="430" y="23" text-anchor="middle" class="title">{USER}@github: ~/profile</text>

<text x="30" y="68" class="prompt">❯</text><text x="50" y="68" class="cmd">neofetch --github --live</text>
<rect id="typer" x="50" y="52" width="230" height="22" fill="#1a1b27"/>

<text x="440" y="108" class="head line" style="animation-delay:.9s">{USER}@github</text>
<rect x="440" y="116" width="360" height="1.5" class="rule line" style="animation-delay:.95s"/>
{"".join(info_svg)}
{pal_svg}

<text x="34" y="108" class="sect line" style="animation-delay:.8s">▍activity · last 26 weeks</text>
<text x="34" y="124" class="dim line" style="animation-delay:.85s">{cal['totalContributions']:,} contributions this year</text>
{"".join(cells)}

<text x="34" y="276" class="sect line" style="animation-delay:1.6s">▍contribution mix · last year</text>
{"".join(bars)}

<text x="30" y="408" class="prompt">❯</text><rect class="cursor" x="50" y="396" width="9" height="16"/>
<text x="830" y="408" text-anchor="end" class="dim">refreshed {updated}</text>
</svg>
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print(f"wrote {OUT}: commits={commits} (private={private_c}) repos={public_repos} stars={stars} "
          f"streak={cur}/{longest} reviews={cc['totalPullRequestReviewContributions']}")


if __name__ == "__main__":
    main()
