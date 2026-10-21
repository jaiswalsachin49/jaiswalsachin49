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
FONT = 17
LINE = 27
CHAR = FONT * 0.6  # monospace advance width
CELL, GAP = 12, 3

THEMES = {
    "dark": dict(
        bg="#0d1117", border="#30363d", bar="#161b22", lights=["#ff5f57", "#febc2e", "#28c840"], title="#7d8590",
        prompt="#7d8590", cmd="#e6edf3", out="#9198a1", strong="#e6edf3", accent="#fb7a2c",
        levels=["#1c2128", "#4a2512", "#7d3a12", "#c25a17", "#fb7a2c"],
    ),
    "light": dict(
        bg="#ffffff", border="#d0d7de", bar="#f6f8fa", lights=["#ff5f57", "#febc2e", "#28c840"], title="#6e7781",
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
    bar_h = 40
    y = bar_h + 14
    parts, keyframes = [], []
    clock = 0.4  # seconds; drives the whole sequence

    def show(content, delay, cls="in"):
        return f'<g class="{cls}" style="animation-delay:{delay:.2f}s">{content}</g>'

    prompt_w = (len(PROMPT) + 1) * CHAR
    for i, (cmd, outputs) in enumerate(blocks):
        y += LINE
        x0 = PAD + prompt_w
        dist = len(cmd) * CHAR
        typing = max(0.35, len(cmd) * 0.045)
        line = (
            f'<text x="{PAD}" y="{y}"><tspan fill="{t["prompt"]}">{PROMPT} </tspan>'
            f'<tspan fill="{t["cmd"]}">{html.escape(cmd)}</tspan></text>'
        )
        # A background-coloured cover with the cursor on its left edge slides right
        # one character at a time, which reads as the command being typed.
        keyframes.append(f"@keyframes k{i}{{to{{transform:translateX({dist:.1f}px)}}}}")
        cover = (
            f'<g style="animation:k{i} {typing:.2f}s steps({len(cmd)}) {clock + 0.25:.2f}s forwards">'
            f'<rect x="{x0 + CHAR:.1f}" y="{y - FONT}" width="{dist + 4:.1f}" height="{LINE}" fill="{t["bg"]}"/>'
            f'<rect class="caret" x="{x0:.1f}" y="{y - FONT + 1}" width="{CHAR:.1f}" height="{FONT + 3}" fill="{t["accent"]}" '
            f'style="animation-delay:{clock + 0.25 + typing + 0.1:.2f}s"/>'
            f'</g>'
        )
        parts.append(show(line + cover, clock))
        clock += 0.25 + typing + 0.2
        for j, out in enumerate(outputs):
            y += LINE
            spans = "".join(f'<tspan fill="{t[role]}">{html.escape(txt)}</tspan>' for txt, role in out)
            parts.append(show(f'<text x="{PAD}" y="{y}">{spans}</text>', clock + j * 0.07, "rise"))
        clock += len(outputs) * 0.07 + 0.3
        y += 12

    # Contribution graph, filled in one week (column) at a time.
    grid_top = y + 4
    cols = []
    for wi, week in enumerate(s["weeks"]):
        cells = "".join(
            f'<rect x="{PAD + wi * (CELL + GAP)}" y="{grid_top + weekday * (CELL + GAP)}" '
            f'width="{CELL}" height="{CELL}" rx="2.5" fill="{t["levels"][level]}"/>'
            for weekday, level in week
        )
        cols.append(show(cells, clock + wi * 0.018, "pop"))
    parts.append("".join(cols))
    clock += len(s["weeks"]) * 0.018 + 0.3
    y = grid_top + 7 * (CELL + GAP) + 20

    # Final prompt with a blinking cursor.
    y += LINE
    parts.append(show(
        f'<text x="{PAD}" y="{y}" fill="{t["prompt"]}">{PROMPT}</text>'
        f'<rect class="cursor" x="{PAD + prompt_w:.1f}" y="{y - FONT + 1}" width="{CHAR:.1f}" height="{FONT + 3}" fill="{t["accent"]}"/>',
        clock,
    ))

    height = y + PAD
    dots = "".join(
        f'<circle cx="{PAD - 10 + i * 20}" cy="{bar_h / 2}" r="6" fill="{c}"/>'
        for i, c in enumerate(t["lights"])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace" font-size="{FONT}">
<style>
text{{white-space:pre}}
.win{{animation:win .5s cubic-bezier(.2,.8,.2,1) both}}
@keyframes win{{from{{opacity:0;transform:translateY(8px)}}}}
.in{{opacity:0;animation:in .2s ease-out forwards}}
@keyframes in{{to{{opacity:1}}}}
.rise{{opacity:0;animation:rise .4s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes rise{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.pop{{opacity:0;animation:pop .35s ease-out forwards}}
@keyframes pop{{from{{opacity:0;transform:translateY(-4px)}}to{{opacity:1;transform:none}}}}
.caret{{animation:out 0s forwards}}
@keyframes out{{to{{opacity:0}}}}
{"".join(keyframes)}
.cursor{{animation:blink 1.1s step-end infinite}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.in,.rise,.pop{{opacity:1}}.caret{{opacity:0}}g[style*="steps"]{{display:none}}}}
</style>
<g class="win">
<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>
<path d="M.5 {bar_h}V12.5a12 12 0 0 1 12-12h{WIDTH - 25}a12 12 0 0 1 12 12V{bar_h}z" fill="{t["bar"]}"/>
<line x1="0" y1="{bar_h}" x2="{WIDTH}" y2="{bar_h}" stroke="{t["border"]}"/>
{dots}
<text x="{WIDTH / 2}" y="{bar_h / 2 + 5}" text-anchor="middle" font-size="13" fill="{t["title"]}">sachin — zsh</text>
{"".join(parts)}
</g>
</svg>
"""


def main():
    stats = fetch()
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, stats))
    print("updated:", {k: v for k, v in stats.items() if k != "weeks"})


if __name__ == "__main__":
    main()
