# The Cookbook

34 recipes, mostly cooked for one, mostly from one grocery run. A static site —
no server, no database, no build toolchain beyond Python.

Live at: `https://<your-username>.github.io/cookbook/`

---

## How it's put together

```
recipes.json        ← the only file you edit
template.html       ← page shell and all the UI code
sw-template.js      ← service worker (offline support)
build.py            ← turns the three above into the site
tools/make-icons.py ← one-off; regenerates the PNG icons from the SVG
cookbook.md         ← generated plain-text export of every recipe
docs/               ← generated site. GitHub Pages serves this folder.
```

**Never edit anything in `docs/`.** It's overwritten on every build. Source at the
root, output in `docs/`, so the two can't get confused.

## Adding a recipe

1. Append one object to `recipes.json`. Take the next unused `id` — **IDs are
   permanent.** Never reuse a number, never shift one. Deleting a recipe retires
   its number and leaves a gap; that's intended.
2. `python3 build.py`
3. `git add -A && git commit -m "Add #35" && git push`

Live in about a minute. Nobody reinstalls anything.

`build.py` refuses to build on duplicate IDs, broken `related` links, or missing
required fields. If it exits with an error, the site is unchanged.

### Recipe object

```json
{
  "id": 35,
  "title": "Something Good",
  "cuisine": "Korean",
  "method": "Stovetop",
  "time": "25 min",
  "level": "Beginner",
  "serves": "Serves 1",
  "blurb": "One or two sentences for the card.",
  "allergens": "soy, wheat",
  "ing": [{ "g": null, "items": ["200 g thing", "1 tbsp other thing"] }],
  "steps": [["Step title", "What to actually do."]],
  "notes": ["Optional. One string per note."],
  "related": [31],
  "locked": "Optional. Shown when an amount was a guess, not a tested number."
}
```

`"g"` names an ingredient group ("Sauce", "To finish") or is `null` for one flat
list. `cuisine` and `method` create their own filter chips automatically — a new
value just appears in the UI.

---

## First-time setup on GitHub Pages

1. Create a repo (`cookbook` is fine). Public — Pages on private repos needs a
   paid plan.
2. Push everything in this folder to `main`.
3. **Settings → Pages → Build and deployment → Deploy from a branch**, then pick
   **`main`** and folder **`/docs`**. Save.
4. Wait a minute or two. Your URL appears at the top of that same page.

Send that URL to whoever you like. No accounts, no app store, no install.

**On Android:** open in Chrome → **⋮ → Add to Home screen**. Gets an icon, opens
without browser chrome, works offline after the first visit.
**On iPhone:** Safari → Share → **Add to Home Screen**.

---

## Things worth knowing

**The URL is unlisted, not private.** Anyone with the link can open it, and a
public repo means the recipes are readable on GitHub too. Fine for a cookbook.
Don't put anything on it you'd mind a stranger reading.

**Offline works after the first visit.** A service worker caches the page. Page
loads try the network first, so an update lands the next time someone opens it
with a signal; if there's no signal, they get the last version they loaded.

**Fonts come from Google's CDN** and are cached after first use. First-ever load
on a bad connection shows a system font for a moment. Self-hosting the two
families would fix it and costs about 200 KB.

**The cache version is a hash of the built page**, so a rebuild that changes
nothing won't force everyone to re-download.

## Personal annotations

`recipes.json` carries `appleRisk` and `appleNote` on a few recipes — a private
apple/pear label-check flag. `build.py` strips both from the shared site and
fails the build if either leaks. The data stays in the JSON so a personal build
can render it later.
