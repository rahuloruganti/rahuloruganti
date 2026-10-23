#!/usr/bin/env python3
"""Generate assets/langs.svg and assets/activity.svg from live GitHub data.

Self-hosted replacements for third-party README widgets (no external service to go down).
Reuses fetch() from gen_card.py. Auth: GITHUB_TOKEN, falls back to `gh auth token`.
"""
import os
from collections import defaultdict
from datetime import date
from html import escape

from gen_card import USER, fetch

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

STYLE = """<style>
  text { font-family: 'Fira Code','JetBrains Mono',Consolas,Menlo,monospace; font-size: 13px; }
  .title { fill:#565f89; font-size:12px }
  .sect { fill:#ff9e64; font-weight:700 }
  .val { fill:#c0caf5 }
  .dim { fill:#7982a9; font-size:12px }
  .glow { animation: pulse 3s ease-in-out infinite }
  .appear { opacity:0; animation: appear .5s ease-out forwards }
  .grow { transform-box: fill-box; transform-origin: left center; transform: scaleX(0); animation: grow 1s cubic-bezier(.2,.8,.2,1) forwards }
  .draw { stroke-dasharray: 3000; stroke-dashoffset: 3000; animation: draw 2.2s ease-out .3s forwards }
  .fade { opacity:0; animation: appear 1s ease-out 1.6s forwards }
  @keyframes appear { from { opacity:0; transform: translateY(4px) } to { opacity:1; transform:none } }
  @keyframes grow { to { transform: scaleX(1) } }
  @keyframes draw { to { stroke-dashoffset: 0 } }
  @keyframes pulse { 0%,100% { opacity:.55 } 50% { opacity:1 } }
</style>"""

FRAME = """<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a1b27"/><stop offset="1" stop-color="#16161e"/></linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7aa2f7"/><stop offset=".5" stop-color="#bb9af7"/><stop offset="1" stop-color="#f7768e"/></linearGradient>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7aa2f7" stop-opacity=".45"/><stop offset="1" stop-color="#7aa2f7" stop-opacity="0"/></linearGradient>
</defs>"""


def frame(w, h, title):
    return (
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="url(#bg)"/>'
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="none" stroke="url(#edge)" stroke-width="2" class="glow"/>'
        f'<circle cx="24" cy="19" r="6" fill="#f7768e"/><circle cx="44" cy="19" r="6" fill="#e0af68"/><circle cx="64" cy="19" r="6" fill="#9ece6a"/>'
        f'<text x="{w//2}" y="23" text-anchor="middle" class="title">{escape(title)}</text>'
    )


def write(name, w, h, body, label):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">\n'
        f"{STYLE}\n{FRAME}\n{body}\n</svg>\n"
    )
    path = os.path.join(ASSETS, name)
    os.makedirs(ASSETS, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print("wrote", path)


def langs_svg(u):
    sizes, colors = defaultdict(int), {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            sizes[n] += e["size"]
            colors[n] = e["node"]["color"] or "#7982a9"
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:6]
    total = sum(v for _, v in top) or 1
    W, H = 860, 190
    x0, bw, y = 34, 792, 74
    body = [f'<text x="34" y="62" class="sect">▍languages · public repos</text>']
    # stacked bar, clipped to a rounded track
    body.append(f'<clipPath id="track"><rect x="{x0}" y="{y+14}" width="{bw}" height="14" rx="7"/></clipPath>')
    body.append(f'<rect x="{x0}" y="{y+14}" width="{bw}" height="14" rx="7" fill="#24283b"/>')
    segs, x = [], x0
    for i, (n, v) in enumerate(top):
        w = bw * v / total
        segs.append(
            f'<rect class="grow" style="animation-delay:{0.2 + i*0.12:.2f}s" x="{x:.1f}" y="{y+14}" '
            f'width="{w:.1f}" height="14" fill="{colors[n]}"><title>{escape(n)}: {100*v/total:.1f}%</title></rect>'
        )
        x += w
    body.append(f'<g clip-path="url(#track)">{"".join(segs)}</g>')
    # legend, 3 columns x 2 rows
    for i, (n, v) in enumerate(top):
        cx, cy = x0 + (i % 3) * 270, y + 62 + (i // 3) * 30
        body.append(
            f'<g class="appear" style="animation-delay:{0.9 + i*0.1:.2f}s">'
            f'<circle cx="{cx+6}" cy="{cy-4}" r="6" fill="{colors[n]}"/>'
            f'<text x="{cx+20}" y="{cy}" class="val">{escape(n)}</text>'
            f'<text x="{cx+20+9*len(n)+10}" y="{cy}" class="dim">{100*v/total:.1f}%</text></g>'
        )
    body.append(f'<text x="{W-30}" y="{H-14}" text-anchor="end" class="dim">refreshed {date.today().isoformat()}</text>')
    write("langs.svg", W, H, "\n".join(body), f"Top languages for {USER}")


def activity_svg(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"][-52:]
    data = [(w["contributionDays"][0]["date"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in weeks]
    W, H = 860, 270
    L, R, T, B = 50, 30, 90, 40
    pw, ph = W - L - R, H - T - B
    mx = max(c for _, c in data) or 1
    step = pw / (len(data) - 1)
    # sqrt scale so quiet weeks stay visible next to one-off spikes
    pts = [(L + i * step, T + ph - ph * (c / mx) ** 0.5) for i, (_, c) in enumerate(data)]

    def smooth(p):  # simple Catmull-Rom -> cubic bezier
        d = f"M{p[0][0]:.1f},{p[0][1]:.1f}"
        for i in range(len(p) - 1):
            p0, p1, p2, p3 = p[max(i-1, 0)], p[i], p[i+1], p[min(i+2, len(p)-1)]
            c1 = (p1[0] + (p2[0]-p0[0]) / 6, p1[1] + (p2[1]-p0[1]) / 6)
            c2 = (p2[0] - (p3[0]-p1[0]) / 6, p2[1] - (p3[1]-p1[1]) / 6)
            d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        return d

    line = smooth(pts)
    base = T + ph
    area = f'{line} L{pts[-1][0]:.1f},{base} L{pts[0][0]:.1f},{base} Z'
    body = [f'<text x="34" y="62" class="sect">▍contribution graph · last 52 weeks</text>']
    for frac in (0, .5, 1):  # frac = height fraction; value = mx * frac^2
        gy = T + ph - ph * frac
        body.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{W-R}" y2="{gy:.1f}" stroke="#2a2e45" stroke-dasharray="3 4"/>')
        body.append(f'<text x="{L-8}" y="{gy+4:.1f}" text-anchor="end" class="dim">{round(mx*frac*frac)}</text>')
    body.append(f'<path d="{area}" fill="url(#area)" class="fade"/>')
    body.append(f'<path d="{line}" fill="none" stroke="#7aa2f7" stroke-width="2.5" stroke-linecap="round" class="draw"/>')
    # month labels (first week of each month, every other)
    last = None
    for i, (d, _) in enumerate(data):
        m = d[:7]
        if m != last:
            last = m
            if int(m[5:]) % 2 == 1:
                mname = date(int(m[:4]), int(m[5:]), 1).strftime("%b")
                body.append(f'<text x="{pts[i][0]:.1f}" y="{base+20}" text-anchor="middle" class="dim">{mname}</text>')
    pk = max(range(len(data)), key=lambda i: data[i][1])
    px, py = pts[pk]
    body.append(
        f'<g class="fade"><circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#f7768e"/>'
        f'<text x="{px-12:.1f}" y="{py+4:.1f}" text-anchor="end" class="val">peak {data[pk][1]} · week of {data[pk][0]}</text></g>'
    )
    body.append(f'<text x="{W-30}" y="62" text-anchor="end" class="dim">{cal["totalContributions"]:,} contributions · refreshed {date.today().isoformat()}</text>')
    write("activity.svg", W, H, "\n".join(body), f"Contribution graph for {USER}")


if __name__ == "__main__":
    user = fetch()
    langs_svg(user)
    activity_svg(user)
