import glob
import json
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
FIXTURES = os.path.join(DATA, "fixtures")


def describe(mistakes):
    first = mistakes[0]
    moves = ", ".join(f"{m['move_text']}{m['played_san']}" for m in mistakes)
    return f"{len(mistakes)} ошибок, играли за {first.get('user_side')}: {moves}"


def make_game1():
    target = os.path.join(FIXTURES, "game1.json")
    if os.path.exists(target):
        print("game1.json уже есть, пропускаю")
        return

    files = glob.glob(os.path.join(ROOT, "mistake_*.json"))
    if not files:
        print("В корне проекта не нашёл mistake_*.json. Запускайте скрипт "
              "из корня проекта (рядом с main.py).")
        return

    mistakes = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            mistakes.append(json.load(f))

    mistakes.sort(key=lambda m: (m.get("move", 0), 0 if m.get("side") == "white" else 1))

    with open(target, "w", encoding="utf-8") as f:
        json.dump(mistakes, f, ensure_ascii=False, indent=2)
    print("Создан game1.json:", describe(mistakes))


def make_game2():
    target = os.path.join(FIXTURES, "game2.json")
    source = os.path.join(DATA, "import_analysis.json")

    if os.path.exists(target):
        print("game2.json уже есть, пропускаю")
        return
    if not os.path.exists(source):
        print("Не нашёл data/import_analysis.json")
        return

    shutil.copyfile(source, target)
    with open(target, encoding="utf-8") as f:
        mistakes = json.load(f)
    print("Создан game2.json:", describe(mistakes))


if __name__ == "__main__":
    os.makedirs(FIXTURES, exist_ok=True)
    make_game1()
    make_game2()
    print("Готово. Файлы лежат в", FIXTURES)