import csv
import os


def detect_opening(game):

    moves = []

    board = game.board()

    for move in game.mainline_moves():
        moves.append(move.uci())
        board.push(move)

    played = " ".join(moves)

    database = os.path.join("database", "openings.csv")

    with open(database, encoding="utf-8") as file:

        reader = csv.DictReader(file)

        best = None

        for row in reader:

            if played.startswith(row["moves"]):
                best = row

        return best