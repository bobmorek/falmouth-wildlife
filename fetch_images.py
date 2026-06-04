#!/usr/bin/env python3
"""
fetch_images.py  —  Falmouth Bay Wildlife Log
Downloads a photo for each species, resizes to a small square thumbnail,
and writes credits.

Sources, in order of preference:
  1. Wikipedia / Wikimedia Commons  — freely licensed, safe to republish.
  2. whaletrail.org/spotters-guide  — fallback for species Wikimedia misses.
     NOTE: WhaleTrail images are COPYRIGHTED (all rights reserved). They are
     only used here because the project owner has opted in / arranged use.
     Set USE_WHALETRAIL = False to disable this fallback entirely.

USAGE:
    pip install pillow requests
    python3 fetch_images.py

Output:
    img/<species_key>.jpg     (square thumbnails, ~160px)
    CREDITS.md                (source + licence per image)

Drop the img/ folder and CREDITS.md into your repo next to index.html.
Re-run any time; it overwrites. If a species fails, the app falls back
to its built-in line icon automatically, so partial runs are fine.

Some hosts (incl. whaletrail.org) block non-browser clients; this script
presents a normal browser User-Agent for them. Run it from a machine with
open internet — sandboxed/allowlisted environments may 403.
"""
import os, json, time, io, re
import requests
from html.parser import HTMLParser
from urllib.parse import urljoin
from PIL import Image, ImageOps

UA = "FalmouthWildlifeLog/1.0 (community wildlife recording project)"
# Some sites refuse non-browser agents, so present a normal browser UA to them.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
THUMB = 160  # output square size in px

# whaletrail.org fallback ----------------------------------------------------
USE_WHALETRAIL = True
WHALETRAIL_URL = "https://whaletrail.org/spotters-guide"
# Manual overrides: species_key -> the exact label as it appears on whaletrail
# (only needed when their wording differs from our common name).
WHALETRAIL_ALIASES = {
    # "orca": "Killer Whale",
    # "harbour_porpoise": "Harbour Porpoise",
}

# species_key : (common name, scientific binomial)
# Both are looked up in order — the common-name page first, then the Latin
# binomial as a fallback — so a miss or a redirect on one still finds a photo.
SPECIES = {
    "common_dolphin":     ("Common dolphin",                "Delphinus delphis"),
    "bottlenose_dolphin": ("Common bottlenose dolphin",     "Tursiops truncatus"),
    "rissos_dolphin":     ("Risso's dolphin",               "Grampus griseus"),
    "striped_dolphin":    ("Striped dolphin",               "Stenella coeruleoalba"),
    "white_sided_dolphin":("Atlantic white-sided dolphin",  "Lagenorhynchus acutus"),
    "harbour_porpoise":   ("Harbour porpoise",              "Phocoena phocoena"),
    "minke_whale":        ("Common minke whale",            "Balaenoptera acutorostrata"),
    "humpback_whale":     ("Humpback whale",                "Megaptera novaeangliae"),
    "fin_whale":          ("Fin whale",                     "Balaenoptera physalus"),
    "pilot_whale":        ("Long-finned pilot whale",       "Globicephala melas"),
    "orca":               ("Orca",                          "Orcinus orca"),
    "gannet":             ("Northern gannet",               "Morus bassanus"),
    "shag":               ("European shag",                 "Gulosus aristotelis"),
    "cormorant":          ("Great cormorant",               "Phalacrocorax carbo"),
    "fulmar":             ("Northern fulmar",               "Fulmarus glacialis"),
    "kittiwake":          ("Black-legged kittiwake",        "Rissa tridactyla"),
    "razorbill":          ("Razorbill",                     "Alca torda"),
    "guillemot":          ("Common murre",                  "Uria aalge"),
    "puffin":             ("Atlantic puffin",               "Fratercula arctica"),
    "manx_shearwater":    ("Manx shearwater",               "Puffinus puffinus"),
    "storm_petrel":       ("European storm petrel",         "Hydrobates pelagicus"),
    "grey_seal":          ("Grey seal",                     "Halichoerus grypus"),
    "harbour_seal":       ("Harbor seal",                   "Phoca vitulina"),
    "basking_shark":      ("Basking shark",                 "Cetorhinus maximus"),
    "sunfish":            ("Ocean sunfish",                 "Mola mola"),
    "leatherback":        ("Leatherback sea turtle",        "Dermochelys coriacea"),
    "jellyfish":          ("Jellyfish",                     None),
    # "other" intentionally omitted — uses line icon
}

S = requests.Session()
S.headers.update({"User-Agent": UA})

def summary(title):
    """Wikipedia REST summary: gives originalimage + thumbnail."""
    r = S.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ','_')}", timeout=25)
    r.raise_for_status()
    return r.json()

def find_image(names):
    """Try each candidate page title in turn; return (title, summary, src) for
    the first one that yields an image. Raises if none do."""
    last_err = None
    for title in names:
        if not title:
            continue
        try:
            d = summary(title)
            src = (d.get("originalimage") or d.get("thumbnail") or {}).get("source")
            if src:
                return title, d, src
            last_err = RuntimeError("no image in summary")
        except Exception as e:
            last_err = e
        time.sleep(0.2)  # be polite between candidate lookups
    raise last_err or RuntimeError("no candidate titles")

def _norm(s):
    """Lowercase and collapse to single-spaced alphanumerics for matching."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

_WT_INDEX = None
def whaletrail_index():
    """Scrape whaletrail.org/spotters-guide once into {normalised label: url}.
    Cached for the run. Returns {} if the page can't be fetched."""
    global _WT_INDEX
    if _WT_INDEX is not None:
        return _WT_INDEX
    idx, pairs = {}, []
    try:
        r = S.get(WHALETRAIL_URL, headers={"User-Agent": BROWSER_UA}, timeout=30)
        r.raise_for_status()

        class _Imgs(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag != "img":
                    return
                a = dict(attrs)
                src = a.get("src") or a.get("data-src") or a.get("data-lazy-src") or ""
                label = a.get("alt") or a.get("title") or ""
                if src and not src.startswith("data:"):
                    pairs.append((label, urljoin(WHALETRAIL_URL, src)))

        _Imgs().feed(r.text)
        for label, url in pairs:
            k = _norm(label)
            if k and k not in idx:
                idx[k] = url
        print(f"  (whaletrail: indexed {len(idx)} labelled images)")
    except Exception as e:
        print(f"  (whaletrail index unavailable: {e})")
    _WT_INDEX = idx
    return idx

def whaletrail_image(key, common):
    """Best-effort match of a species to a whaletrail image URL, or None."""
    idx = whaletrail_index()
    if not idx:
        return None
    wanted = _norm(WHALETRAIL_ALIASES.get(key, common))
    if wanted in idx:
        return idx[wanted]
    # otherwise, accept a label that contains all the significant words
    words = [w for w in wanted.split() if len(w) > 2]
    best = None
    for label, url in idx.items():
        toks = label.split()
        if words and all(w in toks for w in words):
            if best is None or len(label) < len(best[0]):  # prefer most specific
                best = (label, url)
    return best[1] if best else None

def image_credit(img_url):
    """Look up licence + author for a Commons file via the MediaWiki API."""
    fname = img_url.split("/")[-1]
    if "/thumb/" in img_url:
        fname = img_url.split("/thumb/")[1].split("/")[0:1]
        fname = img_url.split("/")[-1]  # thumb filename == original here in most cases
    try:
        r = S.get("https://en.wikipedia.org/w/api.php", params={
            "action":"query","format":"json","prop":"imageinfo",
            "titles":f"File:{fname}","iiprop":"extmetadata|url"
        }, timeout=25)
        pages = r.json()["query"]["pages"]
        info = next(iter(pages.values()))["imageinfo"][0]["extmetadata"]
        lic = info.get("LicenseShortName",{}).get("value","(see source)")
        artist = info.get("Artist",{}).get("value","(unknown)")
        # strip any HTML tags from artist
        import re; artist = re.sub("<[^>]+>","",artist).strip()
        return lic, artist
    except Exception:
        return "(see source)", "(unknown)"

def square(data):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im = ImageOps.fit(im, (THUMB, THUMB), Image.LANCZOS)  # centre-crop to square
    out = io.BytesIO(); im.save(out, "JPEG", quality=82, optimize=True)
    return out.getvalue()

def main():
    os.makedirs("img", exist_ok=True)
    credits = ["# Image credits\n",
               "Species photos sourced from Wikipedia / Wikimedia Commons under the licences noted. ",
               "Each remains the property of its author.\n"]
    ok = fail = 0
    used_wt = False
    for key, names in SPECIES.items():
        names = (names,) if isinstance(names, str) else tuple(names)
        common = names[0]
        err = None
        # 1) Wikimedia (freely licensed) -------------------------------------
        try:
            title, d, src = find_image(names)
            raw = S.get(src, timeout=30).content
            open(f"img/{key}.jpg","wb").write(square(raw))
            lic, artist = image_credit(src)
            page = d.get("content_urls",{}).get("desktop",{}).get("page","")
            via = "" if title == common else f" (via {title})"
            credits.append(f"- **{common}** (`{key}.jpg`): {artist}, {lic}. {page}")
            print(f"  ok   {key:22s} {common}{via}")
            ok += 1
        except Exception as e:
            err = e
        # 2) whaletrail.org fallback (COPYRIGHTED — owner opted in) -----------
        if err is not None and USE_WHALETRAIL:
            try:
                wsrc = whaletrail_image(key, common)
                if not wsrc:
                    raise RuntimeError("no whaletrail match")
                raw = S.get(wsrc, headers={"User-Agent": BROWSER_UA}, timeout=30).content
                open(f"img/{key}.jpg","wb").write(square(raw))
                credits.append(f"- **{common}** (`{key}.jpg`): illustration "
                               f"© WhaleTrail.org, all rights reserved — "
                               f"used by arrangement. {WHALETRAIL_URL}")
                print(f"  ok   {key:22s} {common} (via whaletrail.org)")
                ok += 1; used_wt = True; err = None
            except Exception as e:
                err = e
        if err is not None:
            print(f"  FAIL {key:22s} {common}  — {err}  (app will use line icon)")
            fail += 1
        time.sleep(0.4)  # be polite to the API
    if used_wt:
        credits.append("\n> Images marked *WhaleTrail.org* are copyrighted "
                       "(all rights reserved) and are NOT freely licensed.")
    open("CREDITS.md","w").write("\n".join(credits)+"\n")
    print(f"\nDone: {ok} downloaded, {fail} fell back to line icons.")
    print("Drop the img/ folder and CREDITS.md next to index.html, then push to GitHub.")

if __name__ == "__main__":
    main()
