"""Draw the profile card: a short terminal session plus last year's contributions.

Writes dark_mode.svg and light_mode.svg next to README.md.
Run locally with `GH_TOKEN=$(gh auth token) python scripts/generate.py`;
a GitHub Action runs it once a day so the numbers and graph stay current.
"""

import html
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = "jaiswalsachin49"
PROMPT = "sachin@nst ~ %"

WIDTH = 880
PAD = 32
FONT = 14
LINE = 22
CELL, GAP = 12, 3

THEMES = {
    "dark": dict(
        bg="#0d1117", border="#30363d", bar="#161b22", dot="#30363d", title="#7d8590",
        prompt="#7d8590", cmd="#e6edf3", out="#9198a1", strong="#e6edf3", accent="#fb7a2c",
        levels=["#1c2128", "#4a2512", "#7d3a12", "#c25a17", "#fb7a2c"],
    ),
    "light": dict(
        bg="#ffffff", border="#d0d7de", bar="#f6f8fa", dot="#d0d7de", title="#6e7781",
        prompt="#6e7781", cmd="#1f2328", out="#59636e", strong="#1f2328", accent="#d4520a",
        levels=["#eff2f5", "#ffd9bf", "#ffac73", "#f47b2a", "#d4520a"],
    ),
}

LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    query = """query($login: String!) {
      user(login: $login) {
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) { totalCount }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { contributionLevel weekday } }
          }
        }
      }
    }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.load(res)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    u = body["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["weekday"], LEVEL[d["contributionLevel"]]) for d in w["contributionDays"]] for w in cal["weeks"]]
    return dict(
        total=cal["totalContributions"],
        repos=u["repositories"]["totalCount"],
        followers=u["followers"]["totalCount"],
        weeks=weeks,
    )


def session(s):
    """The terminal transcript: (command, [output lines]). Outputs are lists of (text, role)."""
    return [
        ("whoami", [[("Sachin Jaiswal", "strong"), (". Full stack developer from Sonipat, India.", "out")]]),
        ("cat now.md", [
            [("Software Development Intern at ", "out"), ("Mindtrot Technologies", "strong")],
            [("B.Tech in AI at ", "out"), ("Newton School of Technology", "strong"), (", class of '28", "out")],
        ]),
        ("ls ~/projects", [[("skillswap/  fuelflow/  hpcl-lead-agent/  ev-charging-intelligence/  alcovia/", "out")]]),
        ("cat stack.txt", [
            [(f"{label:<11}", "out"), (items, "strong")]
            for label, items in [
                ("languages", "c++, python, typescript, javascript, sql"),
                ("frontend", "react, next.js, tailwind css, react native"),
                ("backend", "node.js, express, fastapi, socket.io"),
                ("data", "mongodb, mysql, sqlite, prisma"),
                ("ai", "langchain, langgraph, scikit-learn, pandas"),
                ("tools", "git, postman, vercel, render"),
            ]
        ]),
        ("cat ratings.txt", [[
            ("leetcode ", "out"), ("1700+", "strong"), ("   codeforces ", "out"), ("1200+", "strong"),
            ("   icpc prelims ", "out"), ("AIR 1068", "strong"),
        ]]),
        ("git activity --last-year", [[
            (f"{s['total']:,}", "accent"), (" contributions across ", "out"), (f"{s['repos']}", "strong"),
            (" public repos", "out"),
        ]]),
    ]


def render(theme, s):
    t = THEMES[theme]
    blocks = session(s)
    bar_h = 36
    y = bar_h + 12
    parts, step = [], 0

    def fade(content, delay):
        return f'<g class="in" style="animation-delay:{delay:.2f}s">{content}</g>'

    for cmd, outputs in blocks:
        y += LINE
        line = (
            f'<text x="{PAD}" y="{y}"><tspan fill="{t["prompt"]}">{PROMPT} </tspan>'
            f'<tspan fill="{t["cmd"]}">{html.escape(cmd)}</tspan></text>'
        )
        parts.append(fade(line, 0.25 + step * 0.35))
        step += 1
        for out in outputs:
            y += LINE
            spans = "".join(f'<tspan fill="{t[role]}">{html.escape(txt)}</tspan>' for txt, role in out)
            parts.append(fade(f'<text x="{PAD}" y="{y}">{spans}</text>', 0.25 + step * 0.35))
        step += 1
        y += 10

    # Contribution graph under the last command.
    grid_top = y + 6
    cells = []
    for wi, week in enumerate(s["weeks"]):
        for weekday, level in week:
            cx = PAD + wi * (CELL + GAP)
            cy = grid_top + weekday * (CELL + GAP)
            cells.append(f'<rect x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" rx="2" fill="{t["levels"][level]}"/>')
    parts.append(fade("".join(cells), 0.25 + step * 0.35))
    step += 1
    y = grid_top + 7 * (CELL + GAP) + 18

    # Final prompt with a blinking cursor.
    y += LINE
    cursor_x = PAD + (len(PROMPT) + 1) * FONT * 0.6
    parts.append(fade(
        f'<text x="{PAD}" y="{y}" fill="{t["prompt"]}">{PROMPT}</text>'
        f'<rect class="cursor" x="{cursor_x:.1f}" y="{y - FONT + 2}" width="{FONT * 0.6:.1f}" height="{FONT + 2}" fill="{t["accent"]}"/>',
        0.25 + step * 0.35,
    ))

    height = y + PAD
    dots = "".join(
        f'<circle cx="{PAD - 12 + i * 18}" cy="{bar_h / 2}" r="5" fill="{t["dot"]}"/>' for i in range(3)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace" font-size="{FONT}">
<style>
text{{white-space:pre}}
.in{{opacity:0;animation:in .35s ease-out forwards}}
@keyframes in{{to{{opacity:1}}}}
.cursor{{animation:blink 1.1s step-end infinite}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.in{{animation:none;opacity:1}}.cursor{{animation:none}}}}
</style>
<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>
<path d="M.5 {bar_h}V10.5a10 10 0 0 1 10-10h{WIDTH - 21}a10 10 0 0 1 10 10V{bar_h}z" fill="{t["bar"]}"/>
<line x1="0" y1="{bar_h}" x2="{WIDTH}" y2="{bar_h}" stroke="{t["border"]}"/>
{dots}
<text x="{WIDTH / 2}" y="{bar_h / 2 + 4}" text-anchor="middle" font-size="12" fill="{t["title"]}">sachin — zsh</text>
{"".join(parts)}
</svg>
"""


def main():
    stats = fetch()
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, stats))
    print("updated:", {k: v for k, v in stats.items() if k != "weeks"})


if __name__ == "__main__":
    main()
