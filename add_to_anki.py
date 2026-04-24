import json
import urllib.request
import sys

ANKI_URL = "http://localhost:8765"
DECK_NAME = "Oxford 3000"
MODEL_NAME = "Basic"


def anki_request(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, payload)
    response = json.load(urllib.request.urlopen(req))
    if response.get("error"):
        raise Exception(response["error"])
    return response["result"]


def md_to_html(text):
    import re
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)


def parse_cards(filepath):
    import re
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    cards = []
    sections = re.split(r'(?=^FRONT:)', content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section.startswith("FRONT:"):
            continue
        if "BACK:" not in section:
            continue

        parts = re.split(r'^BACK:', section, maxsplit=1, flags=re.MULTILINE)
        if len(parts) != 2:
            continue

        front_raw = parts[0][len("FRONT:"):].strip()
        back_raw = parts[1].strip()

        front_lines = [l.strip() for l in front_raw.splitlines() if l.strip()]
        back_lines = [l.strip() for l in back_raw.splitlines() if l.strip()]

        front = "<br>".join(front_lines)
        back = "<br>".join(md_to_html(l) for l in back_lines)

        if front and back:
            cards.append((front, back))

    return cards


def add_cards(cards):
    notes = [
        {
            "deckName": DECK_NAME,
            "modelName": MODEL_NAME,
            "fields": {"Front": front, "Back": back},
            "options": {"allowDuplicate": False},
            "tags": ["oxford3000", "collocation"],
        }
        for front, back in cards
    ]

    results = anki_request("addNotes", notes=notes)

    added = sum(1 for r in results if r is not None)
    skipped = sum(1 for r in results if r is None)
    print(f"Done: {added} added, {skipped} skipped (duplicates)")


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "cards.txt"
    print(f"Reading: {filepath}")
    cards = parse_cards(filepath)
    print(f"Found {len(cards)} cards")

    if not cards:
        print("No cards found. Check the file format.")
        sys.exit(1)

    add_cards(cards)
