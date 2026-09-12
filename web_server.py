
from flask import Flask, request, jsonify, send_from_directory

import chess
import chess.pgn

import io
import os
import json

import psycopg2

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
# БАЗА ДАННЫХ SUPABASE
# ============================================================

def get_db_connection():

    database_url = os.environ.get(
        "DATABASE_URL"
    )

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL не задан."
        )

    return psycopg2.connect(
        database_url
    )


# ============================================================
# БЕЗОПАСНОЕ ПРЕОБРАЗОВАНИЕ В INT
# ============================================================

def safe_int(value):

    if value is None:
        return None

    try:
        return int(value)

    except (TypeError, ValueError):

        return None


# ============================================================
# БЕЗОПАСНОЕ ПРЕОБРАЗОВАНИЕ В TEXT
# ============================================================

def safe_text(value):

    if value is None:
        return None

    if isinstance(value, str):

        return value

    if hasattr(value, "uci"):

        try:
            return value.uci()

        except Exception:
            pass

    try:

        return json.dumps(
            value,
            ensure_ascii=False
        )

    except Exception:

        return str(value)


# ============================================================
# СОХРАНЕНИЕ АНАЛИЗА В SUPABASE
# ============================================================

def save_analysis_to_database(
    telegram_user,
    pgn_text,
    parsed_game,
    mistakes
):

    # --------------------------------------------------------
    # ПРОВЕРЯЕМ TELEGRAM USER
    # --------------------------------------------------------

    if not telegram_user:

        print(
            "DB: Telegram user не передан."
        )

        return False

    telegram_id = telegram_user.get(
        "id"
    )

    if not telegram_id:

        print(
            "DB: Telegram ID не передан."
        )

        return False

    username = telegram_user.get(
        "username"
    )

    # --------------------------------------------------------
    # ПОДКЛЮЧАЕМСЯ К SUPABASE
    # --------------------------------------------------------

    conn = get_db_connection()

    try:

        with conn:

            with conn.cursor() as cur:

                # ====================================================
                # USERS
                # ====================================================

                cur.execute(
                    """
                    INSERT INTO public.users
                    (
                        telegram_id,
                        username
                    )

                    VALUES
                    (
                        %s,
                        %s
                    )

                    ON CONFLICT (telegram_id)

                    DO UPDATE SET
                        username = EXCLUDED.username

                    RETURNING id
                    """,
                    (
                        safe_int(telegram_id),
                        username
                    )
                )

                user_row = cur.fetchone()

                if not user_row:

                    raise RuntimeError(
                        "Не удалось получить user_id."
                    )

                user_id = user_row[0]

                print(
                    "DB: user_id =",
                    user_id
                )

                # ====================================================
                # GAMES
                # ====================================================

                game_result = (
                    parsed_game.headers.get(
                        "Result",
                        ""
                    )
                )

                cur.execute(
                    """
                    INSERT INTO public.games
                    (
                        user_id,
                        pgn,
                        result
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )

                    RETURNING id
                    """,
                    (
                        user_id,
                        pgn_text,
                        game_result
                    )
                )

                game_row = cur.fetchone()

                if not game_row:

                    raise RuntimeError(
                        "Не удалось получить game_id."
                    )

                game_id = game_row[0]

                print(
                    "DB: game_id =",
                    game_id
                )

                # ====================================================
                # MISTAKES
                # ====================================================

                saved_count = 0

                for mistake in mistakes:

                    # ------------------------------------------------
                    # НОМЕР ХОДА
                    # ------------------------------------------------

                    move_number = (
                        mistake.get(
                            "move_number"
                        )
                        or mistake.get(
                            "move"
                        )
                    )

                    # ------------------------------------------------
                    # FEN
                    # ------------------------------------------------

                    fen = mistake.get(
                        "position_fen"
                    )

                    # ------------------------------------------------
                    # СЫГРАННЫЙ ХОД
                    # ------------------------------------------------

                    played_move = (
                        mistake.get(
                            "position_played_uci"
                        )
                        or mistake.get(
                            "played_move"
                        )
                        or mistake.get(
                            "move_uci"
                        )
                        or mistake.get(
                            "uci"
                        )
                    )

                    # ------------------------------------------------
                    # ЛУЧШИЙ ХОД
                    # ------------------------------------------------

                    best_move = (
                        mistake.get(
                            "best_move"
                        )
                        or mistake.get(
                            "best_move_uci"
                        )
                        or mistake.get(
                            "move_best"
                        )
                    )

                    # ------------------------------------------------
                    # ОЦЕНКА ДО ХОДА
                    # ------------------------------------------------

                    evaluation_before = (
                        mistake.get(
                            "position_evaluation_before"
                        )
                    )

                    if evaluation_before is None:

                        evaluation_before = (
                            mistake.get(
                                "position_evaluation"
                            )
                        )

                    if evaluation_before is None:

                        evaluation_before = (
                            mistake.get(
                                "before_score"
                            )
                        )

                    # ------------------------------------------------
                    # ОЦЕНКА ПОСЛЕ ХОДА
                    # ------------------------------------------------

                    evaluation_after = (
                        mistake.get(
                            "position_evaluation_after"
                        )
                    )

                    if evaluation_after is None:

                        evaluation_after = (
                            mistake.get(
                                "after_score"
                            )
                        )

                    # ------------------------------------------------
                    # LOSS
                    # ------------------------------------------------

                    loss = mistake.get(
                        "loss"
                    )

                    if loss is None:

                        loss = mistake.get(
                            "evaluation_loss"
                        )

                    # ------------------------------------------------
                    # ОБЪЯСНЕНИЕ
                    # ------------------------------------------------

                    explanation = (
                        mistake.get(
                            "explanation"
                        )
                    )

                    # ------------------------------------------------
                    # СОХРАНЯЕМ ОШИБКУ
                    # ------------------------------------------------

                    cur.execute(
                        """
                        INSERT INTO public.mistakes
                        (
                            game_id,
                            user_id,
                            move_number,
                            fen,
                            played_move,
                            best_move,
                            evaluation_before,
                            evaluation_after,
                            loss,
                            explanation,
                            solved
                        )

                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            game_id,
                            user_id,
                            safe_int(move_number),
                            fen,
                            safe_text(played_move),
                            safe_text(best_move),
                            safe_int(
                                evaluation_before
                            ),
                            safe_int(
                                evaluation_after
                            ),
                            safe_int(loss),
                            safe_text(explanation),
                            False
                        )
                    )

                    saved_count += 1

                print(
                    "DB: сохранено ошибок =",
                    saved_count
                )

        print(
            "DB: анализ успешно сохранён."
        )

        return True

    finally:

        conn.close()


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

@app.route(
    "/game",
    methods=["GET"]
)
def get_game():

    return jsonify({

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


# ============================================================
# СДЕЛАТЬ ХОД ИГРОКА
# ============================================================

@app.route(
    "/move",
    methods=["POST"]
)
def make_move():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "error": "Нет данных."
        }), 400

    uci_move = data.get(
        "move"
    )

    if not uci_move:

        return jsonify({
            "success": False,
            "error": "Не указан ход."
        }), 400

    try:

        # ====================================================
        # ХОД ИГРОКА
        # ====================================================

        player_result = (
            game.make_player_move(
                uci_move
            )
        )

        # ====================================================
        # ЕСЛИ ИГРА ЗАКОНЧИЛАСЬ
        # ====================================================

        if player_result["game_over"]:

            return jsonify({

                "success": True,

                "played_move":
                    player_result[
                        "played_move"
                    ].uci(),

                "played_san":
                    player_result[
                        "played_san"
                    ],

                "best_move":
                    player_result[
                        "best_move"
                    ].uci(),

                "best_san":
                    player_result[
                        "best_san"
                    ],

                "is_best":
                    player_result[
                        "is_best"
                    ],

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
        # ОТВЕТ
        # ====================================================

        return jsonify({

            "success": True,

            # ------------------------------------------------
            # ХОД ИГРОКА
            # ------------------------------------------------

            "played_move":
                player_result[
                    "played_move"
                ].uci(),

            "played_san":
                player_result[
                    "played_san"
                ],

            # ------------------------------------------------
            # ЛУЧШИЙ ХОД
            # ------------------------------------------------

            "best_move":
                player_result[
                    "best_move"
                ].uci(),

            "best_san":
                player_result[
                    "best_san"
                ],

            "is_best":
                player_result[
                    "is_best"
                ],

            # ------------------------------------------------
            # ХОД КОМПЬЮТЕРА
            # ------------------------------------------------

            "computer_move":
                computer_result[
                    "move"
                ].uci()
                if computer_result
                else None,

            "computer_san":
                computer_result[
                    "san"
                ]
                if computer_result
                else None,

            # ------------------------------------------------
            # НОВАЯ ПОЗИЦИЯ
            # ------------------------------------------------

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
            "error":
                "Внутренняя ошибка сервера."

        }), 500


# ============================================================
# НОВАЯ ПАРТИЯ
# ============================================================

@app.route(
    "/reset",
    methods=["POST"]
)
def reset_game():

    game.reset()

    return jsonify({

        "success": True,

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


# ============================================================
# АНАЛИЗ PGN
# ============================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze_pgn():

    try:

        # ====================================================
        # ПОЛУЧАЕМ ДАННЫЕ
        # ====================================================

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,
                "error": "Нет данных."

            }), 400

        # ----------------------------------------------------
        # TELEGRAM USER
        # ----------------------------------------------------

        telegram_user = data.get(
            "telegram_user"
        )

        # ----------------------------------------------------
        # PGN
        # ----------------------------------------------------

        pgn_text = data.get(
            "pgn",
            ""
        )

        if not pgn_text.strip():

            return jsonify({

                "success": False,
                "error": "PGN пустой."

            }), 400

        # ====================================================
        # ДИАПАЗОН АНАЛИЗА
        # ====================================================

        start_move = data.get(
            "start_move",
            1
        )

        end_move = data.get(
            "end_move"
        )

        try:

            start_move = int(
                start_move
            )

        except (
            TypeError,
            ValueError
        ):

            start_move = 1

        if end_move in (
            None,
            "",
            "null"
        ):

            end_move = None

        else:

            try:

                end_move = int(
                    end_move
                )

            except (
                TypeError,
                ValueError
            ):

                end_move = None

        # ====================================================
        # ЧИТАЕМ PGN
        # ====================================================

        pgn_file = io.StringIO(
            pgn_text
        )

        parsed_game = (
            chess.pgn.read_game(
                pgn_file
            )
        )

        if parsed_game is None:

            return jsonify({

                "success": False,
                "error":
                    "Не удалось прочитать PGN."

            }), 400

        # ====================================================
        # ЗАПУСК АНАЛИЗАТОРА
        # ====================================================

        print(
            "========================================"
        )

        print(
            "ЗАПУСК ВЕБ-АНАЛИЗА"
        )

        print(
            "White:",
            parsed_game.headers.get(
                "White",
                ""
            )
        )

        print(
            "Black:",
            parsed_game.headers.get(
                "Black",
                ""
            )
        )

        print(
            "Telegram user:",
            telegram_user
        )

        print(
            "========================================"
        )

        print(
            "========== DEBUG BEFORE ANALYZE_GAME ==========",
            flush=True
        )

        analysis_result = analyze_game(
            parsed_game,
            start_move=start_move,
            end_move=end_move
        )

        print(
            "========== DEBUG AFTER ANALYZE_GAME ==========",
            flush=True
        )

        (
            mistakes,
            scores,
            accuracy,
            statistics,
            phase_statistics,
            user_color
        ) = analysis_result

        print(
            "========== DEBUG AFTER UNPACK ==========",
            flush=True
        )

        print(
            "MISTAKES =",
            len(mistakes),
            flush=True
        )
        print("MISTAKES =", len(mistakes))
        print("========== DEBUG 2: ИДЁМ ДАЛЬШЕ ПО /analyze ==========")

        # ====================================================
        # ВОССТАНАВЛИВАЕМ ПОЗИЦИИ
        # ====================================================

        board = parsed_game.board()

        move_positions = []

        for move in (
            parsed_game.mainline_moves()
        ):

            # ------------------------------------------------
            # FEN ДО ХОДА
            # ------------------------------------------------

            fen_before = (
                board.fen()
            )

            move_number = (
                board.fullmove_number
            )

            side = (
                "white"
                if board.turn == chess.WHITE
                else "black"
            )

            played_san = (
                board.san(move)
            )

            move_positions.append({

                "move_number":
                    move_number,

                "side":
                    side,

                "uci":
                    move.uci(),

                "san":
                    played_san,

                "fen":
                    fen_before
            })

            board.push(move)

        # ====================================================
        # ДОБАВЛЯЕМ FEN К ОШИБКАМ
        # ====================================================

        for mistake in mistakes:

            move_number = (

                mistake.get(
                    "move_number"
                )

                or

                mistake.get(
                    "move"
                )
            )

            played_uci = (

                mistake.get(
                    "played_move"
                )

                or

                mistake.get(
                    "move_uci"
                )

                or

                mistake.get(
                    "uci"
                )
            )

            # ------------------------------------------------
            # ЕСЛИ UCI ЯВЛЯЕТСЯ ОБЪЕКТОМ CHESS MOVE
            # ------------------------------------------------

            if hasattr(
                played_uci,
                "uci"
            ):

                played_uci = (
                    played_uci.uci()
                )

            matching_position = None

            # =================================================
            # ИЩЕМ ПО UCI
            # =================================================

            if played_uci:

                for position in (
                    move_positions
                ):

                    if (
                        position["uci"]
                        == played_uci
                    ):

                        matching_position = (
                            position
                        )

                        break

            # =================================================
            # ЕСЛИ ПО UCI НЕ НАШЛИ —
            # ИЩЕМ ПО НОМЕРУ ХОДА
            # =================================================

            if (
                matching_position is None
                and move_number
            ):

                for position in (
                    move_positions
                ):

                    if (

                        position[
                            "move_number"
                        ]
                        == move_number

                        and

                        (
                            user_color is None

                            or

                            position[
                                "side"
                            ]
                            == user_color
                        )
                    ):

                        matching_position = (
                            position
                        )

                        break

            # =================================================
            # СОХРАНЯЕМ ДАННЫЕ ПОЗИЦИИ
            # =================================================

            if matching_position:

                mistake[
                    "position_fen"
                ] = (
                    matching_position[
                        "fen"
                    ]
                )

                mistake[
                    "position_move_number"
                ] = (
                    matching_position[
                        "move_number"
                    ]
                )

                mistake[
                    "position_played_uci"
                ] = (
                    matching_position[
                        "uci"
                    ]
                )

                mistake[
                    "position_played_san"
                ] = (
                    matching_position[
                        "san"
                    ]
                )

            else:

                print(

                    "Не удалось найти "
                    "позицию для ошибки:",

                    move_number,

                    played_uci
                )

        # ====================================================
        # СОХРАНЯЕМ АНАЛИЗ В SUPABASE
        # ====================================================

        print(
            "========== ПЕРЕД СОХРАНЕНИЕМ В БД ==========",
            flush=True
        )
        print(
            "TELEGRAM USER =",
            telegram_user,
            flush=True
        )

        print(
            "MISTAKES COUNT =",
            len(mistakes),
            flush=True
        )

        print(
            "========== DB BLOCK VERSION 2026-09-12 ==========",
            flush=True
        )
        
        saved_to_database = False

        try:

            saved_to_database = (
                save_analysis_to_database(

                    telegram_user,

                    pgn_text,

                    parsed_game,

                    mistakes
                )
            )

        except Exception as db_error:

            print(
                "ОШИБКА СОХРАНЕНИЯ В БД:",
                repr(db_error)
            )

        print("========== ПОСЛЕ СОХРАНЕНИЯ В БД ==========")
        print("SAVED TO DATABASE =", saved_to_database)

            # ------------------------------------------------
            # ВАЖНО:
            # АНАЛИЗ НЕ ЛОМАЕМ.
            # ЕСЛИ БД НЕДОСТУПНА,
            # РЕЗУЛЬТАТ ВСЁ РАВНО ВЕРНЁТСЯ.
            # ------------------------------------------------

        # ====================================================
        # ФОРМИРУЕМ ОТВЕТ
        # ====================================================

        result = {

            "success":
                True,

            "saved_to_database":
                saved_to_database,

            "white":
                parsed_game.headers.get(
                    "White",
                    ""
                ),

            "black":
                parsed_game.headers.get(
                    "Black",
                    ""
                ),

            "date":
                parsed_game.headers.get(
                    "Date",
                    ""
                ),

            "result":
                parsed_game.headers.get(
                    "Result",
                    ""
                ),

            "user_color":
                user_color,

            "accuracy":
                accuracy,

            "statistics":
                statistics,

            "phase_statistics":
                phase_statistics,

            "scores":
                scores,

            "mistakes":
                mistakes
        }

        # ====================================================
        # ПРЕОБРАЗУЕМ В JSON
        # ====================================================

        result = make_json_safe(
            result
        )

        # ====================================================
        # ЛОГ
        # ====================================================

        print(
            "========================================"
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

        print(
            "Сохранено в БД:",
            saved_to_database
        )

        print(
            "========================================"
        )

        return jsonify(
            result
        )

    except Exception as e:

        print(
            "ОШИБКА /analyze:",
            repr(e)
        )

        return jsonify({

            "success": False,

            "error":
                str(e)

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

