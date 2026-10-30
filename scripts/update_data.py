"""Extrae de MTGJSON los datos de Nicol Bolas, Dragon-God (WAR #207) y los guarda en data/card.json.

MTGJSON solo publica los últimos 90 días de precios, así que el script fusiona los
datos nuevos con los ya guardados: ejecutándolo a diario se conserva todo el histórico.
"""
import gzip
import json
import pathlib
import urllib.request

API = "https://mtgjson.com/api/v5"
SET_CODE = "WAR"
NUMBER = "207"
YEAR = "2026"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "card.json"
ICONS = OUT.parent / "icons"
# Productos principales que se marcan en el gráfico (como en MTGGoldfish), por orden de prioridad
# cuando varios salen el mismo día: p. ej. The Hobbit gana a The Hobbit Eternal.
SET_TYPES = ["expansion", "core", "masters", "draft_innovation"]


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mtg-price-pages", "Accept": "*/*"})
    with urllib.request.urlopen(req) as res:
        return res.read()


def fetch(name):
    raw = download(f"{API}/{name}")
    return json.loads(gzip.decompress(raw) if name.endswith(".gz") else raw)["data"]


def main():
    card_set = fetch(f"{SET_CODE}.json")
    card = next(c for c in card_set["cards"] if c["number"] == NUMBER)

    prices = fetch("AllPrices.json.gz").get(card["uuid"], {})
    new = prices.get("paper", {}).get("tcgplayer", {}).get("retail", {}).get("normal", {})

    old = json.loads(OUT.read_text())["prices"] if OUT.exists() else {}
    merged = {d: p for d, p in {**old, **new}.items() if d.startswith(YEAR)}

    by_date = {}
    candidates = [
        s for s in fetch("SetList.json")
        if s["type"] in SET_TYPES and s["releaseDate"].startswith(YEAR) and not s.get("isOnlineOnly")
    ]
    for s in sorted(candidates, key=lambda s: SET_TYPES.index(s["type"])):
        by_date.setdefault(s["releaseDate"], {"code": s["code"], "name": s["name"], "releaseDate": s["releaseDate"]})
    sets = list(by_date.values())

    # Iconos de edición guardados junto a los datos para no depender de Scryfall al cargar la página
    ICONS.mkdir(parents=True, exist_ok=True)
    for s in sets:
        icon = ICONS / f"{s['code'].lower()}.svg"
        if not icon.exists():
            info = json.loads(download(f"https://api.scryfall.com/sets/{s['code'].lower()}"))
            icon.write_bytes(download(info["icon_svg_uri"]))

    OUT.write_text(json.dumps({
        "card": {
            "name": card["name"],
            "set": card_set["name"],
            "number": card["number"],
            "scryfallId": card["identifiers"]["scryfallId"],
        },
        "source": "MTGJSON · TCGplayer retail (USD)",
        "prices": dict(sorted(merged.items())),
        "sets": sorted(sets, key=lambda s: s["releaseDate"]),
    }, indent=1, ensure_ascii=False))
    print(f"{len(merged)} precios guardados ({min(merged)} → {max(merged)})")


if __name__ == "__main__":
    main()
