import json
import os


HISTORY_FILE = os.path.join("data", "history.json")


def load_history():

    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, encoding="utf-8") as file:
        return json.load(file)


def save_history(history):

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=4)

def update_history(record):

    history = load_history()

    for i, game in enumerate(history):

        if game["file"] == record["file"]:
            history[i] = record
            save_history(history)
            return

    history.append(record)

    save_history(history)