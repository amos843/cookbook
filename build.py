#!/usr/bin/env python3
"""
Build the cookbook site from a single source of truth.

    python3 build.py

Reads  : recipes.json, template.html, sw-template.js
Writes : docs/index.html, docs/sw.js, docs/manifest.webmanifest,
         docs/icon.svg, docs/.nojekyll, cookbook.md

GitHub Pages serves the docs/ folder. Source lives at the repo root so the
two never get confused.

To add a recipe: append one object to recipes.json, run this, commit, push.
IDs are permanent — take the next unused number, never reuse or shift one.

The PNG icons are generated once by tools/make-icons.py and committed; this
script does not regenerate them.

This is the SHARED build. Personal allergy annotations (appleRisk /
appleNote) are kept in recipes.json but deliberately never rendered.
"""
import hashlib, json, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.environ.get("COOKBOOK_SITE", os.path.join(HERE, "docs"))
DOCS_ROOT = os.environ.get("COOKBOOK_ROOT", HERE)

CUISINE_ORDER = ["Korean", "Japanese", "Asian", "Italian", "Mexican",
                 "Argentine", "American", "Baking", "Dessert"]

MANIFEST = {
    "name": "The Cookbook",
    "short_name": "Cookbook",
    "description": "Beginner-friendly recipes, mostly cooked for one.",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#edeee7",
    "theme_color": "#edeee7",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png",
         "purpose": "maskable"},
    ],
}

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#2f5d4e"/>
  <g fill="none" stroke="#edeee7" stroke-width="24" stroke-linecap="round">
    <path d="M176 150v82a32 32 0 0 0 64 0v-82"/>
    <path d="M208 150v212"/>
    <path d="M336 362V150c-30 16-44 54-44 98 0 30 14 46 44 46"/>
  </g>
</svg>
"""

EXPECTED_PNGS = ["icon-192.png", "icon-512.png", "icon-maskable-512.png"]


def load():
    with open(os.path.join(HERE, "recipes.json"), encoding="utf-8") as f:
        recipes = json.load(f)
    recipes.sort(key=lambda r: r["id"])
    ids = [r["id"] for r in recipes]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        sys.exit(f"ERROR: duplicate recipe IDs: {dupes}")
    known = set(ids)
    broken = [(r["id"], x) for r in recipes
              for x in r.get("related", []) if x not in known]
    if broken:
        sys.exit(f"ERROR: broken 'related' links: {broken}")
    required = ["id", "title", "cuisine", "method", "time", "level",
                "serves", "blurb", "allergens", "ing", "steps"]
    missing = [(r.get("id"), k) for r in recipes for k in required if k not in r]
    if missing:
        sys.exit(f"ERROR: recipes missing required fields: {missing}")
    return recipes


def build_html(recipes):
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    if "/*__RECIPES__*/" not in tpl:
        sys.exit("ERROR: template.html is missing the /*__RECIPES__*/ placeholder")
    drop = {"appleRisk", "appleNote"}
    slim = [{k: v for k, v in r.items()
             if not k.startswith("_") and k not in drop} for r in recipes]
    blob = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</script", "<\\/script")  # can't close the tag early
    html = tpl.replace("/*__RECIPES__*/", blob)
    for word in ("appleRisk", "appleNote"):
        if word in html:
            sys.exit(f"ERROR: personal annotation '{word}' leaked into the shared build")
    path = os.path.join(SITE, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path, html


def build_sw(html):
    with open(os.path.join(HERE, "sw-template.js"), encoding="utf-8") as f:
        sw = f.read()
    version = hashlib.sha256(html.encode("utf-8")).hexdigest()[:12]
    path = os.path.join(SITE, "sw.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write(sw.replace("__VERSION__", version))
    return path, version


def build_assets():
    written = []
    p = os.path.join(SITE, "manifest.webmanifest")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)
    written.append(p)
    p = os.path.join(SITE, "icon.svg")
    with open(p, "w", encoding="utf-8") as f:
        f.write(ICON_SVG)
    written.append(p)
    p = os.path.join(SITE, ".nojekyll")
    open(p, "w").close()
    written.append(p)
    return written


def recipe_md(r):
    L = [f"## {r['id']}. {r['title']}", "", r["blurb"], ""]
    L += [f"**{r['cuisine']} · {r['method']} · {r['time']} · {r['level']} · {r['serves']}**"]
    L += [f"*Contains: {r['allergens']}.*"]
    if r.get("locked"):
        L += ["", f"> **About these amounts.** {r['locked']}"]
    L += ["", "### Ingredients", ""]
    for g in r["ing"]:
        if g.get("g"):
            L += [f"**{g['g']}**"]
        L += [f"- {i}" for i in g["items"]]
        L += [""]
    L += ["### Method", ""]
    for n, (title, body) in enumerate(r["steps"], 1):
        L += [f"{n}. **{title}** — {body}"]
    if r.get("notes"):
        L += ["", "### Notes", ""]
        L += [f"> {n}\n>" for n in r["notes"]]
    if r.get("related"):
        L += ["", f"**Goes with:** {', '.join('#' + str(i) for i in r['related'])}"]
    L += ["", "---", ""]
    return "\n".join(L)


def build_md(recipes):
    today = date.today().strftime("%d %B %Y")
    by_cuisine = {}
    for r in recipes:
        by_cuisine.setdefault(r["cuisine"], []).append(r)
    order = [c for c in CUISINE_ORDER if c in by_cuisine]
    order += [c for c in sorted(by_cuisine) if c not in order]

    L = ["# The Cookbook", "",
         f"**{len(recipes)} recipes · mostly cooked for one · mostly one grocery run**", "",
         f"Generated {today}. Plain-text export of the site — the readable version",
         "if you'd rather scroll one long page than tap through cards.", "",
         "Ingredient amounts are what worked in my kitchen, not gospel — taste as you go.",
         "A few recipes note where an amount was a best guess rather than a tested number.",
         "Every recipe lists what it contains; check it before you cook if you avoid",
         "anything.", "",
         "Recipe numbers are permanent IDs, assigned when a recipe is added and never",
         "shifted. The index groups by cuisine, so numbers won't always run in order",
         "within a group. That's expected.", "",
         "---", "", "## Index", ""]

    for c in order:
        L += [f"**{c}**"]
        L += [f"- **{r['id']}.** {r['title']}" for r in by_cuisine[c]]
        L += [""]

    L += ["---", ""]
    for c in order:
        L += [f"# {c}", "", "---", ""]
        for r in by_cuisine[c]:
            L += [recipe_md(r)]

    L += ["## Standing notes", "",
          "**Equipment used across the book:** air fryer · slow cooker · rice cooker · "
          "stovetop · oven · pizza stone · Ninja Creami · microwave. Nothing here needs "
          "all of it — filter by equipment on the site to see what you can cook with "
          "what you own.", "",
          "**Shopping:** Walmart covers almost everything. Korean specialty items "
          "(pre-marinated bulgogi, somyeon, gochugaru, Dashida) are easier to find at "
          "H Mart or another Asian grocery.", "",
          "**Cans:** standard cans are 15 oz. Tomato sauce sometimes comes in 8 oz — "
          "avoid those.", "",
          "**Slow cooker HIGH conversions:** chicken tacos 3–4 hrs · beef stew 4–5 hrs · "
          "pasta e fagioli 3–3½ hrs (+30 min for pasta) · honey garlic chicken 3–3½ hrs · "
          "beef chili 3–4 hrs.", "",
          "**Leftovers:** 3–4 days in the fridge. Pack straight from the pot into a "
          "container after dinner.", ""]

    path = os.path.join(DOCS_ROOT, "cookbook.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return path


if __name__ == "__main__":
    os.makedirs(SITE, exist_ok=True)
    recipes = load()
    h, html = build_html(recipes)
    sw, version = build_sw(html)
    a = build_assets()
    m = build_md(recipes)
    print(f"{len(recipes)} recipes (IDs 1–{max(r['id'] for r in recipes)})")
    print(f"cache version {version}")
    for p in [h, sw, m] + a:
        print("wrote", p)
    absent = [n for n in EXPECTED_PNGS if not os.path.exists(os.path.join(SITE, n))]
    if absent:
        print(f"WARNING: missing icons {absent} — run tools/make-icons.py")
