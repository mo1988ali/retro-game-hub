#!/usr/bin/env python3
"""Best-effort LaunchBox Games Database artwork scraper for GitHub Actions.

LaunchBox's public site is not a documented API. This scraper deliberately
checks the actual public game pages and only emits URLs it finds in page HTML.
It never invents image URLs from game database IDs.
"""
from __future__ import annotations
import json, re, time
from pathlib import Path
from urllib.parse import quote, urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
GAMES_FILE = ROOT / "games.json"
OUTPUT_FILE = ROOT / "assets.json"
BASE = "https://gamesdb.launchbox-app.com"
IMG_HOST = "https://images.launchbox-app.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RetroGameHubArtworkBot/1.0; +https://github.com/mo1988ali/retro-game-hub)"}
PLATFORM_HINTS = {
    "gba": ["game boy advance"], "snes": ["super nintendo", "super nintendo entertainment system", "snes"],
    "gb": ["game boy", "game boy color"], "genesis": ["sega genesis", "genesis", "mega drive"],
    "nes": ["nintendo entertainment system", "nes"], "ps1": ["sony playstation", "playstation"]
}
SESSION = requests.Session(); SESSION.headers.update(HEADERS)

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

def absolute_image(value: str) -> str | None:
    if not value: return None
    value = value.strip().replace("&amp;", "&")
    if value.startswith("//"): value = "https:" + value
    elif value.startswith("/"): value = urljoin(BASE, value)
    if value.startswith(IMG_HOST) and not any(x in value.lower() for x in ("placeholder", "default", "no-image")):
        return value
    return None

def search_game(game: dict) -> str | None:
    # LaunchBox documents title/platform filter-style searches in its site search.
    title = game["title"]
    platform = PLATFORM_HINTS.get(game["console"], [""])[0]
    queries = [f"title:{title} platform:{platform}", title]
    for query in queries:
        url = f"{BASE}/games/results?name={quote(query)}"
        try:
            response = SESSION.get(url, timeout=25); response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as exc:
            print(f"  search failed: {exc}"); continue
        candidates=[]
        seen=set()
        for a in soup.select('a[href*="/games/details/"]'):
            href=urljoin(BASE, a.get("href", ""))
            m=re.search(r"/games/details/(\d+)", href)
            if not m or href in seen: continue
            seen.add(href)
            surrounding=a.parent
            for _ in range(3):
                if surrounding and len(surrounding.get_text(" ", strip=True)) < 1200: break
                surrounding=surrounding.parent if surrounding else None
            text=surrounding.get_text(" ", strip=True) if surrounding else a.get_text(" ",strip=True)
            title_text=a.get_text(" ",strip=True) or text[:160]
            title_score=1.0 if norm(title_text)==norm(title) else (0.7 if norm(title) in norm(text) else 0.0)
            plat_score=1.0 if any(norm(p) in norm(text) for p in PLATFORM_HINTS.get(game["console"], [])) else 0.0
            candidates.append((title_score*2+plat_score, href, title_text, text[:250]))
        if candidates:
            candidates.sort(reverse=True)
            best=candidates[0]
            # Avoid an unrelated title match; platform may be absent in search markup.
            if best[0] >= 1.4:
                print(f"  match: {best[2]} ({best[1]})")
                return best[1]
    return None

def extract_media(detail_url: str) -> dict:
    response=SESSION.get(detail_url, timeout=25); response.raise_for_status()
    soup=BeautifulSoup(response.text,"html.parser")
    found={"boxArt":None,"titleScreen":None}
    # Inspect image elements and their nearby labels/captions. LaunchBox categorizes
    # title screens as "Screenshot - Game Title" and box fronts as "Box - Front".
    for node in soup.select("img, a[href]"):
        candidates=[]
        if node.name=="img": candidates.extend([node.get("src"),node.get("data-src"),node.get("data-original")])
        else: candidates.append(node.get("href"))
        for raw in candidates:
            image_url=absolute_image(raw or "")
            if not image_url: continue
            parent=node
            bits=[]
            for _ in range(4):
                if not parent: break
                bits += [parent.get("alt",""),parent.get("title",""),parent.get_text(" ",strip=True)[:500]]
                parent=parent.parent
            context=" ".join(bits).lower()
            if not found["boxArt"] and ("box - front" in context or "box front" in context):
                found["boxArt"]=image_url
            if not found["titleScreen"] and ("screenshot - game title" in context or "game title screenshot" in context or "title screen" in context):
                found["titleScreen"]=image_url
    # Also inspect OpenGraph/meta JSON strings for image URLs with type labels nearby.
    html=response.text
    for match in re.finditer(r"https?[^\"'<> ]+images\.launchbox-app\.com[^\"'<> ]+",html):
        image_url=absolute_image(match.group(0))
        if not image_url: continue
        around=html[max(0,match.start()-500):match.end()+500].lower()
        if not found["boxArt"] and ("box - front" in around or "box front" in around): found["boxArt"]=image_url
        if not found["titleScreen"] and ("screenshot - game title" in around or "title screen" in around): found["titleScreen"]=image_url
    return found

def main():
    games=json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    old=json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.exists() else {}
    result={}
    for index,game in enumerate(games,1):
        print(f"[{index}/{len(games)}] {game['title']} — {game['console']}")
        # Preserve prior successful scrape if LaunchBox is temporarily unavailable.
        record=dict(old.get(game["id"],{}))
        try:
            detail=search_game(game)
            if detail:
                media=extract_media(detail)
                record.update({k:v for k,v in media.items() if v})
                record["gamePage"]=detail
            else: print("  no confident database match")
        except requests.RequestException as exc:
            print(f"  detail lookup failed: {exc}")
        result[game["id"]]={k:v for k,v in record.items() if v}
        time.sleep(1.2)  # Be polite to the public database.
    OUTPUT_FILE.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    total=sum(bool(v.get("boxArt") or v.get("titleScreen")) for v in result.values())
    print(f"Wrote {OUTPUT_FILE}; artwork found for {total}/{len(games)} games.")

if __name__=="__main__": main()
