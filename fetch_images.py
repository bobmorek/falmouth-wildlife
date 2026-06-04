#!/usr/bin/env python3
"""
fetch_images.py  —  Falmouth Bay Wildlife Log
Downloads a freely-licensed photo for each species, resizes to a small
square thumbnail, and writes credits. Sources are tried in order until
one yields an image: Wikipedia → iNaturalist → GBIF.

USAGE:
    pip install pillow requests
    python3 fetch_images.py

Output:
    img/<species_key>.jpg     (square thumbnails, ~160px)
    CREDITS.md                (licence + author per image)

Drop the img/ folder and CREDITS.md into your repo next to index.html.
Re-run any time; it overwrites. If a species fails, the app falls back
to its built-in line icon automatically, so partial runs are fine.
"""
import os, json, time, io
import requests
from PIL import Image, ImageOps

UA = "FalmouthWildlifeLog/1.0 (community wildlife recording project)"
THUMB = 160  # output square size in px

# species_key : (common name, scientific binomial)
# Both are looked up in order — the common-name page first, then the Latin
# binomial as a fallback — so a miss or a redirect on one still finds a photo.
# Keys mirror the CATEGORIES list in index.html; the icon-only catch-all keys
# (jellyfish_other, other) are intentionally omitted — they use a line icon.
SPECIES = {
    # Dolphins & porpoise
    "common_dolphin":     ("Common dolphin",                "Delphinus delphis"),
    "bottlenose_dolphin": ("Common bottlenose dolphin",     "Tursiops truncatus"),
    "rissos_dolphin":     ("Risso's dolphin",               "Grampus griseus"),
    "striped_dolphin":    ("Striped dolphin",               "Stenella coeruleoalba"),
    "white_sided_dolphin":("Atlantic white-sided dolphin",  "Lagenorhynchus acutus"),
    "harbour_porpoise":   ("Harbour porpoise",              "Phocoena phocoena"),
    # Whales
    "minke_whale":        ("Common minke whale",            "Balaenoptera acutorostrata"),
    "humpback_whale":     ("Humpback whale",                "Megaptera novaeangliae"),
    "fin_whale":          ("Fin whale",                     "Balaenoptera physalus"),
    "pilot_whale":        ("Long-finned pilot whale",       "Globicephala melas"),
    "orca":               ("Orca",                          "Orcinus orca"),
    # Seabirds
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
    # Jellyfish
    "barrel_jellyfish":   ("Barrel jellyfish",              "Rhizostoma pulmo"),
    "moon_jellyfish":     ("Moon jellyfish",                "Aurelia aurita"),
    "compass_jellyfish":  ("Compass jellyfish",             "Chrysaora hysoscella"),
    "blue_jellyfish":     ("Blue jellyfish",                "Cyanea lamarckii"),
    "lions_mane_jellyfish":("Lion's mane jellyfish",        "Cyanea capillata"),
    "mauve_stinger":      ("Mauve stinger",                 "Pelagia noctiluca"),
    # Octopus & squid
    "common_octopus":     ("Common octopus",                "Octopus vulgaris"),
    "curled_octopus":     ("Curled octopus",                "Eledone cirrhosa"),
    "cuttlefish":         ("Common cuttlefish",             "Sepia officinalis"),
    "squid":              ("Squid",                         "Loligo forbesii"),
    # Other marine life
    "grey_seal":          ("Grey seal",                     "Halichoerus grypus"),
    "harbour_seal":       ("Harbor seal",                   "Phoca vitulina"),
    "basking_shark":      ("Basking shark",                 "Cetorhinus maximus"),
    "sunfish":            ("Ocean sunfish",                 "Mola mola"),
    "leatherback":        ("Leatherback sea turtle",        "Dermochelys coriacea"),
}

S = requests.Session()
S.headers.update({"User-Agent": UA})

def summary(title):
    """Wikipedia REST summary: gives originalimage + thumbnail."""
    r = S.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ','_')}", timeout=25)
    r.raise_for_status()
    return r.json()

# ── Image sources ──────────────────────────────────────────────────────────
# Each source takes (common, binomial) and returns a record dict:
#   {src, lic, artist, page, source, via}
# where `src` is a downloadable image URL and `via` names the alternate title
# that matched (or None when the common name matched). Raises if nothing found.

def from_wikipedia(common, binomial):
    """Wikipedia REST summary — common name first, Latin binomial as fallback."""
    for title in (common, binomial):
        if not title:
            continue
        try:
            d = summary(title)
            src = (d.get("originalimage") or d.get("thumbnail") or {}).get("source")
            if src:
                lic, artist = image_credit(src)
                page = d.get("content_urls", {}).get("desktop", {}).get("page", "")
                return {"src": src, "lic": lic, "artist": artist, "page": page,
                        "source": "Wikipedia", "via": None if title == common else title}
        except Exception:
            pass
        time.sleep(0.2)  # be polite between candidate lookups
    raise RuntimeError("Wikipedia: no image")

def from_inaturalist(common, binomial):
    """iNaturalist taxon default photo — excellent wildlife coverage.
    Only accepts CC-licensed photos (license_code set); skips all-rights-reserved."""
    for q in (binomial, common):
        if not q:
            continue
        try:
            r = S.get("https://api.inaturalist.org/v1/taxa",
                      params={"q": q, "rank": "species,genus", "per_page": 5}, timeout=25)
            for t in r.json().get("results", []):
                photo = t.get("default_photo") or {}
                src = photo.get("medium_url") or photo.get("url")
                if src and photo.get("license_code"):  # license_code None == all rights reserved
                    page = f"https://www.inaturalist.org/taxa/{t.get('id')}"
                    return {"src": src, "lic": photo["license_code"].upper(),
                            "artist": photo.get("attribution", "(unknown)"), "page": page,
                            "source": "iNaturalist", "via": None if q == common else q}
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("iNaturalist: no CC photo")

def from_gbif(common, binomial):
    """GBIF occurrence media — last-resort aggregator across natural-history sources."""
    name = binomial or common
    if not name:
        raise RuntimeError("GBIF: no name")
    key = S.get("https://api.gbif.org/v1/species/match",
                params={"name": name}, timeout=25).json().get("usageKey")
    if not key:
        raise RuntimeError("GBIF: no taxon match")
    r = S.get("https://api.gbif.org/v1/occurrence/search",
              params={"taxonKey": key, "mediaType": "StillImage", "limit": 20}, timeout=25)
    for occ in r.json().get("results", []):
        for media in occ.get("media", []):
            src = media.get("identifier")
            if src:
                page = f"https://www.gbif.org/occurrence/{occ.get('key')}"
                return {"src": src, "lic": media.get("license", "(see source)"),
                        "artist": media.get("rightsHolder") or media.get("creator") or "(unknown)",
                        "page": page, "source": "GBIF",
                        "via": None if name == common else name}
    raise RuntimeError("GBIF: no media")

SOURCES = (from_wikipedia, from_inaturalist, from_gbif)

def find_image(common, binomial):
    """Try each source in order; return the first record that yields an image."""
    last_err = None
    for source in SOURCES:
        try:
            return source(common, binomial)
        except Exception as e:
            last_err = e
    raise last_err or RuntimeError("no sources configured")

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
               "Species photos sourced from Wikipedia / Wikimedia Commons, iNaturalist and GBIF ",
               "under the licences noted. Each remains the property of its author.\n"]
    ok = fail = 0
    for key, names in SPECIES.items():
        common, binomial = (names, None) if isinstance(names, str) else (names[0], names[1])
        try:
            rec = find_image(common, binomial)
            raw = S.get(rec["src"], timeout=30).content
            open(f"img/{key}.jpg","wb").write(square(raw))
            via = "" if not rec["via"] else f" (via {rec['via']})"
            credits.append(f"- **{common}** (`{key}.jpg`): {rec['artist']}, {rec['lic']}. "
                           f"Source: {rec['source']}. {rec['page']}")
            print(f"  ok   {key:22s} {common}  [{rec['source']}]{via}")
            ok += 1
        except Exception as e:
            print(f"  FAIL {key:22s} {common}  — {e}  (app will use line icon)")
            fail += 1
        time.sleep(0.4)  # be polite to the APIs
    open("CREDITS.md","w",encoding="utf-8").write("\n".join(credits)+"\n")
    print(f"\nDone: {ok} downloaded, {fail} fell back to line icons.")
    print("Drop the img/ folder and CREDITS.md next to index.html, then push to GitHub.")

if __name__ == "__main__":
    main()
