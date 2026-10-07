#!/usr/bin/env python3
"""Builds every SVG in assets/ for the profile README.

- header: the sentence split into LLM tokens, desktop (1200px) and mobile (600px).
- footer: the <|endoftext|> token, desktop and mobile.
- contact/: GitHub-style link buttons, one per network.

Each image has light and dark versions. Fonts are subset through the Google Fonts
`text=` API and embedded as base64, so every SVG renders the same everywhere.
Needs Python 3 and network access to fonts.googleapis.com and cdn.jsdelivr.net.

Usage: python3 scripts/build-assets.py
"""
import base64, html, os, re, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
MODES = ("light", "dark")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

# ─────────────────────────── SVG helpers ───────────────────────────
_cache = {}

def fetch(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})) as r:
        d = r.read()
    return d if binary else d.decode()

def font_face(family, weight, chars):
    key = (family, weight, chars)
    if key not in _cache:
        q = urllib.parse.urlencode({"family": f"{family}:wght@{weight}", "text": chars})
        css = fetch("https://fonts.googleapis.com/css2?" + q)
        url = re.search(r"url\((https://[^)]+)\)", css).group(1)
        b64 = base64.b64encode(fetch(url, True)).decode()
        _cache[key] = f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
    return _cache[key]

# GitHub's own colours, so the images blend into the profile page in both themes.
GH = {
    "light": dict(fg="#1f2328", muted="#59636e", border="#d1d9e0", subtle="#f6f8fa"),
    "dark": dict(fg="#f0f6fc", muted="#9198a1", border="#3d444d", subtle="#151b23"),
}
# Token highlight colours, as in a tokenizer view.
TK = {"light": ["#d9cffb", "#bdebcb", "#fbe0ab", "#f9c7ce", "#bbdcf7"],
      "dark": ["#3a2f6a", "#1d4a31", "#574314", "#5a2430", "#1b4365"]}
MONO, SANS = "Geist Mono", "Geist"

def tpl(s, pal):
    for k in sorted(pal, key=len, reverse=True):
        s = s.replace("$" + k, pal[k])
    return s

BASE_CSS = "text{white-space:pre}@media (prefers-reduced-motion: reduce){*{animation:none!important}}"

def svg(w, h, title, css, body, fonts, pal):
    """Wraps body in an accessible SVG, embedding only the glyphs its text uses."""
    body, css = tpl(body, pal), tpl(css, pal)
    raw = html.unescape("".join(re.findall(r">([^<>]*)<", body)))
    chars = "".join(sorted({c for c in raw + " " if c >= " "}))
    faces = "".join(font_face(f, wt, chars) for f, wt in fonts)
    t = html.escape(title)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{t}"><title>{t}</title>'
            f"<style>{faces}{BASE_CSS}{css}</style>{body}</svg>")

def T(x, y, s, cls, extra=""):
    return f'<text x="{x}" y="{y}" class="{cls}" {extra}>{html.escape(s)}</text>'

# ─────────────────────────── header ───────────────────────────
# The sentence, one list per line. The first line (the name) is set larger.
LINES = [["ant", "onio", "hg"], [" writes", " software", " with", " people"], [" and", " with", " models", "."]]
LINES_MOBILE = [["ant", "onio", "hg"], [" writes", " software"], [" with", " people", " and"], [" with", " models", "."]]
TITLE = ("antoniohg writes software with people and with models. "
         "The sentence is split into 11 coloured LLM tokens, as in a tokenizer, with a cursor after the last one.")

def tokens_header(mode, width, lines, big, small, gap, stat_x, stat_label, stat_value):
    p = dict(GH[mode], **{f"k{i}": c for i, c in enumerate(TK[mode])})
    b, n, chars, top = [], 0, 0, 0
    for li, toks in enumerate(lines):
        fs = big if li == 0 else small
        cw, h = fs * .6, round(fs * 1.34)
        x = 0
        for t in toks:
            w = len(t) * cw
            b.append(f'<g class="tk" style="animation-delay:{.25 + n * .11:.2f}s">'
                     f'<rect x="{x:.1f}" y="{top}" width="{w:.1f}" height="{h}" rx="3" fill="$k{n % 5}"/>'
                     + T(f"{x:.1f}", top + round(fs * 1.0), t, "t", f'style="font-size:{fs}px" textLength="{w:.1f}"') + "</g>")
            x += w; n += 1; chars += len(t)
        last = (x, top, h, cw)
        top += h + gap
    # Streaming cursor after the last token: appears when the stream ends, blinks, then stays.
    cx, ctop, ch, ccw = last
    d = .25 + n * .11
    b.append(f'<rect class="cur" x="{cx + ccw * .3:.1f}" y="{ctop}" width="{ccw * .5:.1f}" height="{ch}" rx="1" fill="$fg" '
             f'style="animation-delay:{d:.2f}s,{d:.2f}s"/>')
    y = top + 30
    b += [T(0, y, "Tokens", "l"), T(0, y + stat_value + 6, str(n), "v"),
          T(stat_x, y, "Characters", "l"), T(stat_x, y + stat_value + 6, str(chars), "v")]
    css = (f".t{{font-family:'{MONO}';font-weight:400;fill:$fg}}.l{{font:400 {stat_label}px '{SANS}';fill:$muted}}"
           f".v{{font:600 {stat_value}px '{SANS}';fill:$fg}}.tk{{animation:tk .18s ease-out both}}@keyframes tk{{from{{opacity:0}}}}"
           ".cur{animation:tk .01s backwards,blink 1.1s steps(1) 5 forwards}@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}")
    return svg(width, y + stat_value + 20, TITLE, css, "".join(b), [(MONO, 400), (SANS, 400), (SANS, 600)], p)

def header(mode):
    return tokens_header(mode, 1200, LINES, 66, 48, 12, 200, 20, 34)

def header_mobile(mode):
    return tokens_header(mode, 600, LINES_MOBILE, 48, 34, 8, 180, 19, 32)

# ─────────────────────────── footer ───────────────────────────
def endoftext(mode, width, fs, h):
    p = dict(GH[mode], k0=TK[mode][2])
    t = "<|endoftext|>"; w = len(t) * fs * .6
    b = f'<rect x="0" y="4" width="{w:.1f}" height="{h}" rx="3" fill="$k0"/>' + T(0, h - 6, t, "t", f'textLength="{w:.1f}"')
    return svg(width, h + 8, "End of text token", f".t{{font:400 {fs}px '{MONO}';fill:$fg}}", b, [(MONO, 400)], p)

def footer(mode):
    return endoftext(mode, 1200, 28, 40)

def footer_mobile(mode):
    return endoftext(mode, 600, 26, 38)

# ─────────────────────────── contact buttons ───────────────────────────
# GitHub style: subtle background, border and the logo in its brand colour.
# Each button is the whole link, so its alt text in the README names the link.
ICON_SRC = {
    "cv": "https://cdn.jsdelivr.net/npm/@primer/octicons@19.38.0/build/svg/file-24.svg",
    "linkedin": "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/linkedin/linkedin-plain.svg",
    "bluesky": "https://cdn.jsdelivr.net/npm/simple-icons@16.32.0/icons/bluesky.svg",
    "x": "https://cdn.jsdelivr.net/npm/simple-icons@16.32.0/icons/x.svg",
}
# Logo colour per theme; None uses the text colour (X has no brand colour).
BRAND = {"cv": ("#8250df", "#a371f7"), "linkedin": ("#0a66c2", "#0a66c2"), "bluesky": ("#0085ff", "#0085ff"), "x": None}
# Label advance widths in em for Geist 500, measured in the browser.
LABEL_EM = {"CV": 1.381, "LinkedIn": 3.969, "Bluesky": 3.706, "X": .631}
CONTACT = [("cv", "CV"), ("linkedin", "LinkedIn"), ("bluesky", "Bluesky"), ("x", "X")]

def contact_button(name, label, src, mode):
    p = GH[mode]
    logo = BRAND[name][mode == "dark"] if BRAND[name] else p["fg"]
    vb = float(re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+)', src).group(1))
    paths = "".join(f'<path d="{d}"/>' for d in re.findall(r'<path[^>]*\sd="([^"]+)"', src))
    fs, h, pad, ic, gap = 16, 36, 12, 16, 8
    w = round(pad + ic + gap + LABEL_EM[label] * fs + pad)
    body = (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="6" fill="$subtle" stroke="$border"/>'
            f'<g transform="translate({pad} {(h - ic) / 2}) scale({ic / vb:.4f})" fill="{logo}">{paths}</g>'
            + T(pad + ic + gap, f"{h / 2 + fs * .35:.1f}", label, "l"))
    return svg(w, h, label, f".l{{font:500 {fs}px '{SANS}';fill:$fg}}", body, [(SANS, 500)], p)

# ─────────────────────────── build ───────────────────────────
def write(path, s):
    with open(path, "w") as f:
        f.write(s)

if __name__ == "__main__":
    contact_dir = os.path.join(ASSETS, "contact")
    os.makedirs(contact_dir, exist_ok=True)
    for name, desktop, mobile in [("header", header, header_mobile), ("footer", footer, footer_mobile)]:
        for mode in MODES:
            write(os.path.join(ASSETS, f"{name}-{mode}.svg"), desktop(mode))
            write(os.path.join(ASSETS, f"{name}-mobile-{mode}.svg"), mobile(mode))
    for name, label in CONTACT:
        src = fetch(ICON_SRC[name])
        for mode in MODES:
            write(os.path.join(contact_dir, f"{name}-{mode}.svg"), contact_button(name, label, src, mode))
    print("assets/ rebuilt")
