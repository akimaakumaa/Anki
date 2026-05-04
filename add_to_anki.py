import json
import urllib.request
import sys
import os
import glob

ANKI_URL = "http://localhost:8765"
MODEL_NAME = "Basic"

# Файлы, которые не являются колодами карточек
SKIP_FILES = {"example_cards.txt"}


def anki_request(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, payload)
    response = json.load(urllib.request.urlopen(req))
    error = response.get("error")
    if error:
        # AnkiConnect иногда возвращает список ошибок для addNotes (дубликаты)
        # В этом случае не падаем — возвращаем список None для каждой карточки
        if isinstance(error, list):
            result = response.get("result")
            if result is None:
                return [None] * len(params.get("notes", []))
            return result
        raise Exception(error)
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


def ensure_deck(deck_name):
    anki_request("createDeck", deck=deck_name)


def add_cards(cards, deck_name):
    ensure_deck(deck_name)
    tag = deck_name.lower().replace(" ", "_")
    notes = [
        {
            "deckName": deck_name,
            "modelName": MODEL_NAME,
            "fields": {"Front": front, "Back": back},
            "options": {"allowDuplicate": False},
            "tags": [tag],
        }
        for front, back in cards
    ]

    results = anki_request("addNotes", notes=notes)

    added = sum(1 for r in results if r is not None)
    updated = 0

    # Для карточек, которые уже существуют (результат None), проверяем изменения
    existing_cards = [(front, back) for (front, back), r in zip(cards, results) if r is None]
    for front, back in existing_cards:
        query = f'deck:"{deck_name}" Front:"{front}"'
        note_ids = anki_request("findNotes", query=query)
        if not note_ids:
            continue
        info = anki_request("notesInfo", notes=note_ids)
        note = info[0]
        current_back = note["fields"]["Back"]["value"]
        if current_back != back:
            anki_request("updateNoteFields", note={"id": note["noteId"], "fields": {"Back": back}})
            updated += 1

    skipped = len(existing_cards) - updated
    print(f"  → {added} added, {updated} updated, {skipped} skipped (no changes)")
    return added + updated


def process_file(filepath):
    filename = os.path.basename(filepath)
    deck_name = os.path.splitext(filename)[0].replace("_", " ").title()
    print(f"\n[{filename}] → deck: \"{deck_name}\"")

    cards = parse_cards(filepath)
    print(f"  Found {len(cards)} cards")

    if not cards:
        print("  No cards found. Check the file format.")
        return 0

    return add_cards(cards, deck_name)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Если передан конкретный файл — обработать только его
    if len(sys.argv) > 1:
        files = [sys.argv[1]]
    else:
        # Иначе — найти все .txt файлы в папке скрипта
        all_txt = glob.glob(os.path.join(script_dir, "*.txt"))
        files = [f for f in all_txt if os.path.basename(f) not in SKIP_FILES]

    if not files:
        print("No .txt files found.")
        sys.exit(1)

    print(f"Found {len(files)} file(s) to process:")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    total_added = 0
    for filepath in files:
        total_added += process_file(filepath)

    print(f"\n{'='*40}")
    print(f"Total added: {total_added} new cards")
