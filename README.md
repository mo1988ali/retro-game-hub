# Retro Game Hub

A static GitHub Pages version of the 60-game retro hub. The site uses `games.json` as its game list and `assets.json` as a cached LaunchBox artwork manifest.

## Deploy

1. Upload the contents of this folder to the root of `mo1988ali/retro-game-hub` on the `main` branch.
2. In **Settings → Pages**, set **Build and deployment → Source** to **GitHub Actions**.
3. Open the **Actions** tab and run **Update artwork and deploy GitHub Pages** (or wait for the push-triggered run).
4. Once the workflow succeeds, the Pages URL appears in the deployment summary. For this repository it should be `https://mo1988ali.github.io/retro-game-hub/`.

The workflow also refreshes the artwork manifest every Monday. You can trigger it manually from Actions → Update artwork and deploy GitHub Pages → Run workflow.

## Artwork lookup notes

The browser never guesses image URLs from LaunchBox database IDs. `scripts/scrape_launchbox.py` searches public LaunchBox game pages and extracts URLs only when it can identify the image type. It uses the LaunchBox image labels **Box - Front** and **Screenshot - Game Title** (the latter is LaunchBox's title-screen category). LaunchBox's website is not a documented public API, so markup changes or ambiguous game matches can cause some images to remain blank; those can be added manually in the Settings panel. The script preserves prior successful results if a later scrape misses a game.

Manual URLs entered in the site take priority over scraped URLs. The original per-game database IDs are retained for the View Hub links, but are not used to fabricate image URLs.
