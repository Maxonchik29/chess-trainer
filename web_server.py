from flask import Flask, request, jsonify, send_from_directory
import chess
import chess.pgn
import io

from app.chess_game import ChessGame
from app.analysis import analyze_game, make_json_safe


# ============================================================
# НАСТРОЙКИ
# ============================================================

app = Flask(
    __name__,
    static_folder="web",
    static_url_path=""
)


# ============================================================
# ИГРА
# ============================================================

game = ChessGame(
    player_color=chess.WHITE
)


# ============================================================
# ГЛАВНАЯ СТРАНИЦА
# ============================================================

@app.route("/")
def index():
    return send_from_directory(
        "web",
        "index.html"
    )


# ============================================================
# ПОЛУЧИТЬ ТЕКУЩУЮ ПОЗИЦИЮ
# ============================================================

@app.route("/game", methods=["GET"])
def get_game():

    return jsonify({
        "fen": game.get_fen(),
        "legal_moves": game.get_legal_moves(),
        "player_turn": game.is_player_turn(),
        "game_over": game.is_game_over(),
        "status": game.get_status()
    })


# ============================================================
# СДЕЛАТЬ ХОД ИГРОКА
# ============================================================

@app.route("/move", methods=["POST"])
def make_move():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "Нет данных."
        }), 400

    uci_move = data.get("move")

    if not uci_move:
        return jsonify({
            "success": False,
            "error": "Не указан ход."
        }), 400

    try:

        # ====================================================
        # ХОД ИГРОКА
        # ====================================================

        player_result = game.make_player_move(
            uci_move
        )


        # ====================================================
        # ЕСЛИ ИГРА ЗАКОНЧИЛАСЬ ПОСЛЕ ХОДА ИГРОКА
        # ====================================================

        if player_result["game_over"]:

            return jsonify({
                "success": True,

                "played_move":
                    player_result["played_move"].uci(),

                "played_san":
                    player_result["played_san"],

                "best_move":
                    player_result["best_move"].uci(),

                "best_san":
                    player_result["best_san"],

                "is_best":
                    player_result["is_best"],

                "computer_move":
                    None,

                "computer_san":
                    None,

                "fen":
                    game.get_fen(),

                "legal_moves":
                    game.get_legal_moves(),

                "player_turn":
                    game.is_player_turn(),

                "game_over":
                    True,

                "status":
                    game.get_status()
            })


        # ====================================================
        # ХОД КОМПЬЮТЕРА
        # ====================================================

        computer_result = (
            game.make_computer_move()
        )


        # ====================================================
        # ФОРМИРУЕМ ОТВЕТ
        # ====================================================

        return jsonify({
            "success": True,

            # Ход игрока
            "played_move":
                player_result["played_move"].uci(),

            "played_san":
                player_result["played_san"],

            # Лучший ход Stockfish
            "best_move":
                player_result["best_move"].uci(),

            "best_san":
                player_result["best_san"],

            "is_best":
                player_result["is_best"],

            # Ответ компьютера
            "computer_move":
                computer_result["move"].uci()
                if computer_result
                else None,

            "computer_san":
                computer_result["san"]
                if computer_result
                else None,

            # Новая позиция
            "fen":
                game.get_fen(),

            "legal_moves":
                game.get_legal_moves(),

            "player_turn":
                game.is_player_turn(),

            "game_over":
                game.is_game_over(),

            "status":
                game.get_status()
        })


    except ValueError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


    except Exception as e:

        print(
            "ОШИБКА /move:",
            repr(e)
        )

        return jsonify({
            "success": False,
            "error": "Внутренняя ошибка сервера."
        }), 500
    
# ============================================================
# НОВАЯ ПАРТИЯ
# ============================================================

@app.route("/reset", methods=["POST"])
def reset_game():

    game.reset()

    return jsonify({
        "success": True,
        "fen": game.get_fen(),
        "legal_moves": game.get_legal_moves(),
        "player_turn": game.is_player_turn(),
        "game_over": game.is_game_over(),
        "status": game.get_status()
    })


@app.route("/analyze", methods=["POST"])
def analyze_pgn():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Нет данных."
            }), 400

        pgn_text = data.get("pgn", "")

        if not pgn_text.strip():
            return jsonify({
                "success": False,
                "error": "PGN пустой."
            }), 400

        start_move = data.get("start_move", 1)
        end_move = data.get("end_move")

        try:
            start_move = int(start_move)
        except (TypeError, ValueError):
            start_move = 1

        if end_move in (None, "", "null"):
            end_move = None
        else:
            try:
                end_move = int(end_move)
            except (TypeError, ValueError):
                end_move = None

        # ====================================================
        # ЧИТАЕМ PGN
        # ====================================================

        pgn_file = io.StringIO(pgn_text)

        parsed_game = chess.pgn.read_game(
            pgn_file
        )

        if parsed_game is None:
            return jsonify({
                "success": False,
                "error": "Не удалось прочитать PGN."
            }), 400

        # ====================================================
        # ЗАПУСК СУЩЕСТВУЮЩЕГО АНАЛИЗАТОРА
        # ====================================================

        print("========================================")
        print("ЗАПУСК ВЕБ-АНАЛИЗА")
        print(
            "White:",
            parsed_game.headers.get("White", "")
        )
        print(
            "Black:",
            parsed_game.headers.get("Black", "")
        )
        print("========================================")

        (
            mistakes,
            scores,
            accuracy,
            statistics,
            phase_statistics,
            user_color
        ) = analyze_game(
            parsed_game,
            start_move=start_move,
            end_move=end_move
        )

        # ====================================================
        # ВОССТАНАВЛИВАЕМ ПОЗИЦИИ ДО ХОДОВ
        # ====================================================

        board = parsed_game.board()

        move_positions = []

        for move in parsed_game.mainline_moves():

            # Позиция непосредственно ДО хода
            fen_before = board.fen()

            move_number = board.fullmove_number

            side = "white" if board.turn == chess.WHITE else "black"

            played_san = board.san(move)

            move_positions.append({
                "move_number": move_number,
                "side": side,
                "uci": move.uci(),
                "san": played_san,
                "fen": fen_before
            })

            board.push(move)

        # ====================================================
        # ДОБАВЛЯЕМ FEN К КАЖДОЙ ОШИБКЕ
        # ====================================================

        for mistake in mistakes:

            move_number = (
                mistake.get("move_number")
                or mistake.get("move")
            )

            played_uci = (
                mistake.get("played_move")
                or mistake.get("move_uci")
                or mistake.get("uci")
            )

            # Если объект хода ещё не строка,
            # пытаемся привести его к UCI.
            if hasattr(played_uci, "uci"):

                played_uci = played_uci.uci()

            matching_position = None

            # Сначала пытаемся найти по UCI
            if played_uci:

                for position in move_positions:

                    if position["uci"] == played_uci:

                        matching_position = position
                        break

            # Если UCI нет — ищем по номеру хода
            if matching_position is None and move_number:

                for position in move_positions:

                    if (
                        position["move_number"]
                        == move_number
                        and (
                            user_color is None
                            or position["side"] == user_color
                        )
                    ):

                        matching_position = position
                        break

            # Добавляем технические данные
            # для будущего экрана позиции.
            if matching_position:

                mistake["position_fen"] = (
                    matching_position["fen"]
                )

                mistake["position_move_number"] = (
                    matching_position["move_number"]
                )

                mistake["position_played_uci"] = (
                    matching_position["uci"]
                )

                mistake["position_played_san"] = (
                    matching_position["san"]
                )

            else:

                print(
                    "Не удалось найти позицию для ошибки:",
                    move_number,
                    played_uci
                )

        # ====================================================
        # ФОРМИРУЕМ ОТВЕТ
        # ====================================================

        result = {
            "success": True,

            "white": parsed_game.headers.get(
                "White",
                ""
            ),

            "black": parsed_game.headers.get(
                "Black",
                ""
            ),

            "date": parsed_game.headers.get(
                "Date",
                ""
            ),

            "result": parsed_game.headers.get(
                "Result",
                ""
            ),

            "user_color": user_color,

            "accuracy": accuracy,

            "statistics": statistics,

            "phase_statistics": phase_statistics,

            "scores": scores,

            "mistakes": mistakes
        }

        # ====================================================
        # ПРЕОБРАЗУЕМ В JSON
        # ====================================================

        result = make_json_safe(
            result
        )

        print(
            "АНАЛИЗ ЗАВЕРШЁН"
        )

        print(
            "Ошибок:",
            len(mistakes)
        )

        print(
            "Accuracy:",
            accuracy
        )

        return jsonify(result)

    except Exception as e:

        print(
            "ОШИБКА /analyze:",
            repr(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    try:

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=True
        )

    finally:

        game.close()