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

# species_key : Wikipedia page title (Latin binomial is most reliable)
SPECIES = {
    "common_dolphin":     "Common dolphin",
    "bottlenose_dolphin": "Common bottlenose dolphin",
    "rissos_dolphin":     "Risso's dolphin",
    "striped_dolphin":    "Striped dolphin",
    "white_sided_dolphin":"Atlantic white-sided dolphin",
    "harbour_porpoise":   "Harbour porpoise",
    "minke_whale":        "Common minke whale",
    "humpback_whale":     "Humpback whale",
    "fin_whale":          "Fin whale",
    "pilot_whale":        "Long-finned pilot whale",
    "orca":               "Orca",
    "gannet":             "Northern gannet",
    "shag":               "European shag",
    "cormorant":          "Great cormorant",
    "fulmar":             "Northern fulmar",
    "kittiwake":          "Black-legged kittiwake",
    "razorbill":          "Razorbill",
    "guillemot":          "Common murre",
    "puffin":             "Atlantic puffin",
    "manx_shearwater":    "Manx shearwater",
    "storm_petrel":       "European storm petrel",
    "grey_seal":          "Grey seal",
    "harbour_seal":       "Harbor seal",
    "basking_shark":      "Basking shark",
    "sunfish":            "Ocean sunfish",
    "leatherback":        "Leatherback sea turtle",
    "jellyfish":          "Jellyfish",
    # "other" intentionally omitted — uses line icon
}

S = requests.Session()
S.headers.update({"User-Agent": UA})

def summary(title):
    """Wikipedia REST summary: gives originalimage + thumbnail."""
    r = S.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ','_')}", timeout=25)
    r.raise_for_status()
    return r.json()

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
    for key, title in SPECIES.items():
        try:
            d = summary(title)
            src = (d.get("originalimage") or d.get("thumbnail") or {}).get("source")
            if not src:
                raise RuntimeError("no image in summary")
            raw = S.get(src, timeout=30).content
            open(f"img/{key}.jpg","wb").write(square(raw))
            lic, artist = image_credit(src)
            page = d.get("content_urls",{}).get("desktop",{}).get("page","")
            credits.append(f"- **{title}** (`{key}.jpg`): {artist}, {lic}. {page}")
            print(f"  ok   {key:22s} {title}")
            ok += 1
        except Exception as e:
            print(f"  FAIL {key:22s} {title}  — {e}  (app will use line icon)")
            fail += 1
        time.sleep(0.4)  # be polite to the API
    open("CREDITS.md","w").write("\n".join(credits)+"\n")
    print(f"\nDone: {ok} downloaded, {fail} fell back to line icons.")
    print("Drop the img/ folder and CREDITS.md next to index.html, then push to GitHub.")

if __name__ == "__main__":
    main()
