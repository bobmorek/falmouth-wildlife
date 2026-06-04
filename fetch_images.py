#!/usr/bin/env python3
"""
fetch_images.py  —  Falmouth Bay Wildlife Log
Downloads a freely-licensed photo for each species from Wikipedia,
resizes to a small square thumbnail, and writes credits.

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
    for key, names in SPECIES.items():
        names = (names,) if isinstance(names, str) else tuple(names)
        common = names[0]
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
            print(f"  FAIL {key:22s} {common}  — {e}  (app will use line icon)")
            fail += 1
        time.sleep(0.4)  # be polite to the API
    open("CREDITS.md","w").write("\n".join(credits)+"\n")
    print(f"\nDone: {ok} downloaded, {fail} fell back to line icons.")
    print("Drop the img/ folder and CREDITS.md next to index.html, then push to GitHub.")

if __name__ == "__main__":
    main()
