import json
import os

BASE_DIR = os.path.dirname(__file__)
FILE_NAME = os.path.join(BASE_DIR, "player_statistics.json")


def load_statistics():

    if not os.path.exists(FILE_NAME):
        return {
            "games": 0,
            "mistakes": 0,
            "inaccuracies": 0,
            "blunders": 0,
            "white_games": 0,
            "black_games": 0
        }

    with open(FILE_NAME, "r", encoding="utf-8") as file:
        return json.load(file)


def save_statistics(stats):

    with open(FILE_NAME, "w", encoding="utf-8") as file:
        json.dump(stats, file, indent=4)


def update_player_statistics(statistics):

    print("СТАТИСТИКА ОБНОВЛЯЕТСЯ")

    stats = load_statistics()

    stats["games"] += 1
    stats["mistakes"] += statistics["mistakes"]
    stats["inaccuracies"] += statistics["inaccuracies"]
    stats["blunders"] += statistics["blunders"]

    save_statistics(stats)

    print("Файл сохранён:", FILE_NAME)