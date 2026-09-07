#!/usr/bin/env python3
"""
Generate the PNG app icons from the SVG. Run once, commit the results.

    python3 tools/make-icons.py

Why PNG at all, when docs/icon.svg exists: iOS ignores the web manifest and
reads <link rel="apple-touch-icon">, which does not accept SVG. Without a PNG,
"Add to Home Screen" on an iPhone shows a screenshot of the page instead of
the icon. Android accepts SVG but is happier with raster.

The maskable variant adds padding so Android can crop it to a circle or a
squircle without clipping the glyph.
"""
import os, sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("needs playwright: pip install playwright && playwright install chromium")

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "docs")
SVG = os.path.join(SITE, "icon.svg")

# Android crops maskable icons to the middle ~80%, so the glyph is scaled to
# 62% and centred, leaving room on every edge.
MASKABLE = """<div style="width:512px;height:512px;background:#2f5d4e;display:flex;
align-items:center;justify-content:center">
<div style="width:318px;height:318px">%s</div></div>"""


def main():
    if not os.path.exists(SVG):
        sys.exit(f"missing {SVG} — run build.py first")
    svg = open(SVG, encoding="utf-8").read()
    # strip the background rect for the maskable version; the wrapper supplies it
    glyph = svg.replace('<rect width="512" height="512" fill="#2f5d4e"/>', "")

    jobs = [
        ("icon-192.png", 192, f'<div style="width:192px;height:192px">{svg}</div>'),
        ("icon-512.png", 512, f'<div style="width:512px;height:512px">{svg}</div>'),
        ("icon-maskable-512.png", 512, MASKABLE % glyph),
    ]

    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, size, markup in jobs:
            pg = b.new_page(viewport={"width": size, "height": size},
                            device_scale_factor=1)
            pg.set_content(
                f'<body style="margin:0;background:#2f5d4e">{markup}</body>')
            pg.wait_for_timeout(150)
            out = os.path.join(SITE, name)
            pg.screenshot(path=out, omit_background=False)
            pg.close()
            print("wrote", out)
        b.close()


if __name__ == "__main__":
    main()
