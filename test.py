import chess.pgn

from app.analysis import analyze_game

with open("games/french.pgn", encoding="utf-8") as file:
    game = chess.pgn.read_game(file)

mistakes = analyze_game(game)

print("\nКоличество ошибок:", len(mistakes))