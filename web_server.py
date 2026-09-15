from flask import Flask, request, jsonify, send_from_directory

import chess
import chess.pgn

import io
import os
import json
import threading
import uuid

import psycopg2


from app.chess_game import ChessGame
from app.analysis import analyze_game, make_json_safe

# ==========================================================
# ЗАДАЧИ АНАЛИЗА
# ==========================================================

ANALYSIS_JOBS = {}

ANALYSIS_JOBS_LOCK = threading.Lock()

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
# СТАТИСТИКА TELEGRAM-БОТА
# ============================================================

def update_bot_user(
    telegram_user,
    count_analysis=False,
    count_game=False,
    count_mini_app=False
):

    # --------------------------------------------------------
    # ПРОВЕРЯЕМ TELEGRAM USER
    # --------------------------------------------------------

    if not telegram_user:

        return False

    telegram_id = telegram_user.get(
        "id"
    )

    if not telegram_id:

        return False

    telegram_id = safe_int(
        telegram_id
    )

    if telegram_id is None:

        return False

    username = telegram_user.get(
        "username"
    )

    first_name = telegram_user.get(
        "first_name"
    )

    conn = None

    try:

        conn = get_db_connection()

        with conn:

            with conn.cursor() as cur:

                # ====================================================
                # СОЗДАЁМ ПОЛЬЗОВАТЕЛЯ, ЕСЛИ ЕГО ЕЩЁ НЕТ
                # ====================================================

                cur.execute(
                    """
                    INSERT INTO public.bot_users
                    (
                        telegram_id,
                        username,
                        first_name
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (telegram_id)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_seen = NOW()
                    """,
                    (
                        telegram_id,
                        username,
                        first_name
                    )
                )

                # ====================================================
                # ОБНОВЛЯЕМ СЧЁТЧИКИ
                # ====================================================

                updates = []

                if count_analysis:

                    updates.append(
                        "analyses_count = analyses_count + 1"
                    )

                if count_game:

                    updates.append(
                        "games_count = games_count + 1"
                    )

                if count_mini_app:

                    updates.append(
                        "mini_app_opens = mini_app_opens + 1"
                    )

                if updates:

                    query = f"""
                        UPDATE public.bot_users
                        SET
                            last_seen = NOW(),
                            {", ".join(updates)}
                        WHERE telegram_id = %s
                    """

                    cur.execute(
                        query,
                        (
                            telegram_id,
                        )
                    )

                return True

    except Exception as error:

        print(
            "BOT STATS ERROR:",
            repr(error)
        )

        return False

    finally:

        if conn:

            conn.close()


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
                            safe_int(
                                move_number
                            ),
                            fen,
                            safe_text(
                                played_move
                            ),
                            safe_text(
                                best_move
                            ),
                            safe_int(
                                evaluation_before
                            ),
                            safe_int(
                                evaluation_after
                            ),
                            safe_int(
                                loss
                            ),
                            safe_text(
                                explanation
                            ),
                            False
                        )
                    )

                    saved_count += 1

                print(
                    "DB: Анализ сохранён.",
                    "user_id =",
                    user_id,
                    "game_id =",
                    game_id,
                    "ошибок =",
                    saved_count
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
# АКТИВНОСТЬ TELEGRAM MINI APP
# ============================================================

@app.route(
    "/track_activity",
    methods=["POST"]
)
def track_activity():

    data = request.get_json(
        silent=True
    ) or {}

    telegram_user = data.get(
        "telegram_user"
    )

    if not telegram_user:

        return jsonify({
            "success": False,
            "error": "Telegram user не передан."
        }), 400

    success = update_bot_user(
        telegram_user,
        count_mini_app=True
    )

    return jsonify({
        "success": success
    })


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
            game.get_status(),

        "player_color":
            "white"
            if game.player_color == chess.WHITE
            else "black"
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

        player_result = game.make_player_move(
            uci_move
        )

        if not player_result.get(
            "success"
        ):

            return jsonify({

                "success": False,

                "error":
                    player_result.get(
                        "error",
                        "Неверный ход."
                    )

            }), 400

        # ====================================================
        # ДАННЫЕ ХОДА ИГРОКА
        # ====================================================

        played_move = (
            player_result.get(
                "played_move"
            )
        )

        if played_move is None:

            played_move = uci_move

        if hasattr(
            played_move,
            "uci"
        ):

            played_move_uci = (
                played_move.uci()
            )

        else:

            played_move_uci = (
                played_move
            )

        played_san = (
            player_result.get(
                "san"
            )
        )

        if played_san is None:

            played_san = ""

        # ====================================================
        # ПОКА ЛУЧШИЙ ХОД НЕ АНАЛИЗИРУЕМ
        # ====================================================

        best_move_uci = None

        is_best = False

        # ====================================================
        # ИГРА ЗАКОНЧИЛАСЬ
        # ====================================================

        if player_result.get(
            "game_over",
            False
        ):

            return jsonify({

                "success": True,

                "played_move":
                    played_move_uci,

                "played_san":
                    played_san,

                "best_move":
                    None,

                "best_san":
                    None,

                "is_best":
                    False,

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
                    game.get_status(),

                "need_computer_move":
                    False
            })

        # ====================================================
        # ВАЖНО:
        # ЗДЕСЬ НЕ ДЕЛАЕМ ХОД КОМПЬЮТЕРА
        #
        # Браузер должен сначала получить ход игрока.
        # ====================================================

        return jsonify({

            "success": True,

            # ------------------------------------------------
            # ХОД ИГРОКА
            # ------------------------------------------------

            "played_move":
                played_move_uci,

            "played_san":
                played_san,

            # ------------------------------------------------
            # ЛУЧШИЙ ХОД
            # ------------------------------------------------

            "best_move":
                best_move_uci,

            "best_san":
                None,

            "is_best":
                is_best,

            # ------------------------------------------------
            # КОМПЬЮТЕР ПОКА НЕ ХОДИЛ
            # ------------------------------------------------

            "computer_move":
                None,

            "computer_san":
                None,

            # ------------------------------------------------
            # ТЕКУЩАЯ ПОЗИЦИЯ
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
                game.get_status(),

            # ------------------------------------------------
            # ГОВОРИМ JAVASCRIPT:
            # НУЖЕН ХОД КОМПЬЮТЕРА
            # ------------------------------------------------

            "need_computer_move":
                True
        })

    except ValueError as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

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

@app.route(
    "/computer_move",
    methods=["POST"]
)
def computer_move():

    try:

        # ====================================================
        # ХОД КОМПЬЮТЕРА
        # ====================================================

        computer_result = (
            game.make_computer_move()
        )

        computer_move_uci = None
        computer_san = None

        if computer_result:

            computer_move = (
                computer_result.get(
                    "move"
                )
            )

            if hasattr(
                computer_move,
                "uci"
            ):

                computer_move_uci = (
                    computer_move.uci()
                )

            else:

                computer_move_uci = (
                    computer_move
                )

            computer_san = (
                computer_result.get(
                    "san"
                )
            )

        # ====================================================
        # ОТВЕТ
        # ====================================================

        return jsonify({

            "success": True,

            "computer_move":
                computer_move_uci,

            "computer_san":
                computer_san,

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

    except Exception as e:

        print(
            "ОШИБКА /computer_move:",
            repr(e)
        )

        return jsonify({

            "success": False,

            "error":
                "Ошибка хода компьютера."

        }), 500
    
# ============================================================
# НОВАЯ ПАРТИЯ
# ============================================================

@app.route("/reset", methods=["POST"])
def reset_game():
    global game

    try:
        data = request.get_json(silent=True) or {}

        # ====================================================
        # СТОРОНА ИГРОКА
        # ====================================================

        player_color = data.get(
            "player_color",
            "white"
        )

        if player_color == "black":
            color = chess.BLACK
        else:
            color = chess.WHITE

        # ====================================================
        # ВЫБРАННЫЙ ДЕБЮТ
        # ====================================================

        opening = data.get(
            "opening",
            "none"
        )

        # Защита от неизвестного значения
        allowed_openings = {
            "none",
            "french",
            "sicilian",
            "old_indian",
            "kings_indian",
            "queens_gambit",
            "catalan",
        }

        if opening not in allowed_openings:
            opening = "none"

        print(
            "Новая партия:",
            "player_color =", player_color,
            "opening =", opening
        )

        # ====================================================
        # ЗАКРЫВАЕМ СТАРУЮ ИГРУ
        # ====================================================

        try:
            game.close()
        except Exception as error:
            print(
                "Не удалось закрыть старую игру:",
                repr(error)
            )

        # ====================================================
        # СОЗДАЁМ НОВУЮ ИГРУ
        # ====================================================

        game = ChessGame(
            player_color=color,
            opening=opening
        )

        computer_result = None

        # ====================================================
        # ЕСЛИ ИГРОК ЧЁРНЫМИ —
        # КОМПЬЮТЕР ДЕЛАЕТ ПЕРВЫЙ ХОД
        # ====================================================

        if color == chess.BLACK:

            computer_result = (
                game.make_computer_move()
            )

        # ====================================================
        # ОТВЕТ
        # ====================================================

        return jsonify({
            "success": True,
            "fen": game.get_fen(),
            "legal_moves": game.get_legal_moves(),
            "player_turn": game.is_player_turn(),
            "game_over": game.is_game_over(),
            "status": game.get_status(),
            "player_color": player_color,
            "opening": game.opening,
            "opening_active": game.opening_active,
            "computer_move": (
                computer_result.get("move")
                if computer_result
                else None
            ),
            "computer_san": (
                computer_result.get("san")
                if computer_result
                else None
            ),
        })

    except Exception as error:

        print(
            "ОШИБКА /reset:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

# ============================================================
# ПОЛУЧИТЬ PGN ТЕКУЩЕЙ ПАРТИИ
# ============================================================

@app.route(
    "/game_pgn",
    methods=["GET"]
)
def get_game_pgn():

    try:

        pgn = game.get_pgn()

        return jsonify({

            "success": True,

            "pgn": pgn,

            "result":
                game.get_result(),

            "game_over":
                game.is_game_over()

        })

    except Exception as error:

        print(
            "ОШИБКА /game_pgn:",
            repr(error)
        )

        return jsonify({

            "success": False,

            "error":
                "Не удалось получить PGN."

        }), 500

# ==========================================================
# ОБНОВЛЕНИЕ ПРОГРЕССА АНАЛИЗА
# ==========================================================

def update_analysis_progress(
    job_id,
    progress
):

    with ANALYSIS_JOBS_LOCK:

        job = ANALYSIS_JOBS.get(
            job_id
        )

        if job is None:
            return

        job["progress"] = int(
            progress
        )


# ==========================================================
# ЗАПУСК АНАЛИЗА В ФОНОВОМ ПОТОКЕ
# ==========================================================

def run_analysis_job(
    job_id,
    pgn_text,
    telegram_user,
    start_move,
    end_move
):

    try:

        print(
            "========================================"
        )

        print(
            "ФОНОВЫЙ АНАЛИЗ ЗАПУЩЕН"
        )

        print(
            "JOB ID:",
            job_id
        )

        print(
            "========================================"
        )

        # ==================================================
        # ЧИТАЕМ PGN
        # ==================================================

        pgn_file = io.StringIO(
            pgn_text
        )

        parsed_game = chess.pgn.read_game(
            pgn_file
        )

        if parsed_game is None:

            with ANALYSIS_JOBS_LOCK:

                ANALYSIS_JOBS[job_id][
                    "status"
                ] = "error"

                ANALYSIS_JOBS[job_id][
                    "error"
                ] = (
                    "Не удалось прочитать PGN."
                )

            return

        # ==================================================
        # CALLBACK ПРОГРЕССА
        # ==================================================

        def progress_callback(
            progress
        ):

            update_analysis_progress(
                job_id,
                progress
            )

        # ==================================================
        # АНАЛИЗ
        # ==================================================

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
            end_move=end_move,
            progress_callback=progress_callback
        )

        # ==================================================
        # ПОЗИЦИИ ХОДОВ
        # ==================================================

        board = parsed_game.board()

        move_positions = []

        for move in parsed_game.mainline_moves():

            fen_before = board.fen()

            move_number = (
                board.fullmove_number
            )

            side = (
                "white"
                if board.turn == chess.WHITE
                else "black"
            )

            played_san = board.san(
                move
            )

            move_positions.append({

                "move_number": move_number,

                "side": side,

                "uci": move.uci(),

                "san": played_san,

                "fen": fen_before

            })

            board.push(
                move
            )

        # ==================================================
        # ДОБАВЛЯЕМ ПОЗИЦИИ К ОШИБКАМ
        # ==================================================

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

            if hasattr(
                played_uci,
                "uci"
            ):

                played_uci = (
                    played_uci.uci()
                )

            matching_position = None

            if played_uci:

                for position in move_positions:

                    if (
                        position["uci"]
                        == played_uci
                    ):

                        matching_position = (
                            position
                        )

                        break

            if (
                matching_position is None
                and move_number
            ):

                for position in move_positions:

                    if (
                        position["move_number"]
                        == move_number
                        and (
                            user_color is None
                            or position["side"]
                            == user_color
                        )
                    ):

                        matching_position = (
                            position
                        )

                        break

            if matching_position:

                mistake[
                    "position_fen"
                ] = matching_position[
                    "fen"
                ]

                mistake[
                    "position_move_number"
                ] = matching_position[
                    "move_number"
                ]

                mistake[
                    "position_played_uci"
                ] = matching_position[
                    "uci"
                ]

                mistake[
                    "position_played_san"
                ] = matching_position[
                    "san"
                ]

            else:

                print(
                    "Не удалось найти позицию "
                    "для ошибки:",
                    move_number,
                    played_uci
                )

        # ==================================================
        # СОХРАНЕНИЕ В БД
        # ==================================================

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

        if saved_to_database:

            update_bot_user(
                telegram_user,
                count_analysis=True
            )

        # ==================================================
        # ФИНАЛЬНЫЙ РЕЗУЛЬТАТ
        # ==================================================

        result = {

            "success": True,

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

        result = make_json_safe(
            result
        )

        # ==================================================
        # СОХРАНЯЕМ РЕЗУЛЬТАТ ЗАДАЧИ
        # ==================================================

        with ANALYSIS_JOBS_LOCK:

            ANALYSIS_JOBS[job_id][
                "status"
            ] = "completed"

            ANALYSIS_JOBS[job_id][
                "progress"
            ] = 100

            ANALYSIS_JOBS[job_id][
                "result"
            ] = result

        print(
            "========================================"
        )

        print(
            "ФОНОВЫЙ АНАЛИЗ ЗАВЕРШЁН"
        )

        print(
            "JOB ID:",
            job_id
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

    except Exception as e:

        print(
            "ОШИБКА ФОНОВОГО АНАЛИЗА:",
            repr(e)
        )

        with ANALYSIS_JOBS_LOCK:

            if job_id in ANALYSIS_JOBS:

                ANALYSIS_JOBS[job_id][
                    "status"
                ] = "error"

                ANALYSIS_JOBS[job_id][
                    "error"
                ] = str(e)

# ==========================================================
# ЗАПУСК АНАЛИЗА ПАРТИИ
# ==========================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze_pgn():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "error": "Нет данных."
            }), 400

        telegram_user = data.get(
            "telegram_user"
        )

        pgn_text = data.get(
            "pgn",
            ""
        )

        if not pgn_text.strip():

            return jsonify({
                "success": False,
                "error": "PGN пустой."
            }), 400

        # ==================================================
        # НАЧАЛЬНЫЙ ХОД
        # ==================================================

        start_move = data.get(
            "start_move",
            1
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

        # ==================================================
        # КОНЕЧНЫЙ ХОД
        # ==================================================

        end_move = data.get(
            "end_move"
        )

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

        # ==================================================
        # ПРОВЕРЯЕМ PGN ДО ЗАПУСКА ПОТОКА
        # ==================================================

        pgn_file = io.StringIO(
            pgn_text
        )

        parsed_game = chess.pgn.read_game(
            pgn_file
        )

        if parsed_game is None:

            return jsonify({
                "success": False,
                "error":
                    "Не удалось прочитать PGN."
            }), 400

        print(
            "========================================"
        )

        print(
            "ЗАПУСК ФОНОВОГО ВЕБ-АНАЛИЗА"
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

        # ==================================================
        # СОЗДАЁМ ID ЗАДАЧИ
        # ==================================================

        job_id = str(
            uuid.uuid4()
        )

        # ==================================================
        # СОЗДАЁМ ЗАДАЧУ
        # ==================================================

        with ANALYSIS_JOBS_LOCK:

            ANALYSIS_JOBS[job_id] = {

                "status": "running",

                "progress": 0,

                "result": None,

                "error": None

            }

        # ==================================================
        # ЗАПУСКАЕМ АНАЛИЗ В ФОНОВОМ ПОТОКЕ
        # ==================================================

        thread = threading.Thread(

            target=run_analysis_job,

            args=(

                job_id,

                pgn_text,

                telegram_user,

                start_move,

                end_move

            ),

            daemon=True

        )

        thread.start()

        # ==================================================
        # СРАЗУ ОТВЕЧАЕМ БРАУЗЕРУ
        # ==================================================

        return jsonify({

            "success": True,

            "job_id": job_id

        })

    except Exception as e:

        print(
            "ОШИБКА /analyze:",
            repr(e)
        )

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500

# ==========================================================
# ПРОГРЕСС АНАЛИЗА
# ==========================================================

@app.route(
    "/analyze/progress/<job_id>",
    methods=["GET"]
)
def analyze_progress(
    job_id
):

    with ANALYSIS_JOBS_LOCK:

        job = ANALYSIS_JOBS.get(
            job_id
        )

        if job is None:

            return jsonify({

                "success": False,

                "error":
                    "Задача анализа не найдена."

            }), 404

        response = {

            "success": True,

            "status":
                job.get(
                    "status",
                    "running"
                ),

            "progress":
                job.get(
                    "progress",
                    0
                )

        }

        # ==================================================
        # АНАЛИЗ ЗАКОНЧЕН
        # ==================================================

        if job.get(
            "status"
        ) == "completed":

            response[
                "result"
            ] = job.get(
                "result"
            )

        # ==================================================
        # ОШИБКА
        # ==================================================

        elif job.get(
            "status"
        ) == "error":

            response[
                "error"
            ] = job.get(
                "error",
                "Неизвестная ошибка."
            )

        return jsonify(
            response
        )

# ============================================================
# ПОЛУЧИТЬ МОИ ОШИБКИ
# ============================================================

@app.route(
    "/mistakes",
    methods=["POST"]
)
def get_mistakes():

    data = request.get_json(
        silent=True
    ) or {}

    telegram_user = data.get(
        "telegram_user"
    )

    if not telegram_user:

        return jsonify({
            "ok": False,
            "error":
                "Telegram user не передан."
        }), 400

    telegram_id = telegram_user.get(
        "id"
    )

    if not telegram_id:

        return jsonify({
            "ok": False,
            "error":
                "Telegram ID не передан."
        }), 400

    conn = get_db_connection()

    try:

        with conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        m.id,
                        m.game_id,
                        m.move_number,
                        m.fen,
                        m.played_move,
                        m.best_move,
                        m.evaluation_before,
                        m.evaluation_after,
                        m.loss,
                        m.explanation,
                        m.solved,
                        g.pgn,
                        g.result
                    FROM public.mistakes m
                    JOIN public.games g
                        ON g.id = m.game_id
                    JOIN public.users u
                        ON u.id = m.user_id
                    WHERE u.telegram_id = %s
                    ORDER BY m.id DESC
                    """,
                    (
                        safe_int(
                            telegram_id
                        ),
                    )
                )

                rows = cur.fetchall()

                mistakes = []

                for row in rows:

                    mistakes.append({

                        "id":
                            row[0],

                        "game_id":
                            row[1],

                        "move_number":
                            row[2],

                        "fen":
                            row[3],

                        "played_move":
                            row[4],

                        "best_move":
                            row[5],

                        "evaluation_before":
                            row[6],

                        "evaluation_after":
                            row[7],

                        "loss":
                            row[8],

                        "explanation":
                            row[9],

                        "solved":
                            row[10],

                        "pgn":
                            row[11],

                        "result":
                            row[12]

                    })

                return jsonify({

                    "ok": True,

                    "mistakes":
                        mistakes,

                    "count":
                        len(mistakes)

                })

    except Exception as error:

        print(
            "ОШИБКА ПОЛУЧЕНИЯ ОШИБОК:",
            repr(error)
        )

        return jsonify({

            "ok": False,

            "error":
                str(error)

        }), 500

    finally:

        conn.close()

# ============================================================
# УДАЛИТЬ МОЮ ОШИБКУ
# ============================================================

@app.route(
    "/mistakes/<int:mistake_id>",
    methods=["DELETE"]
)
def delete_mistake(mistake_id):

    data = request.get_json(
        silent=True
    ) or {}

    telegram_user = data.get(
        "telegram_user"
    )

    if not telegram_user:

        return jsonify({
            "ok": False,
            "error":
                "Telegram пользователь не передан."
        }), 400

    telegram_id = telegram_user.get(
        "id"
    )

    if not telegram_id:

        return jsonify({
            "ok": False,
            "error":
                "Telegram ID не передан."
        }), 400

    telegram_id = safe_int(
        telegram_id
    )

    if telegram_id is None:

        return jsonify({
            "ok": False,
            "error":
                "Некорректный Telegram ID."
        }), 400

    conn = None

    try:

        conn = get_db_connection()

        with conn:

            with conn.cursor() as cur:

                # ====================================================
                # УДАЛЯЕМ ТОЛЬКО ОШИБКУ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
                # ====================================================

                cur.execute(
                    """
                    DELETE FROM public.mistakes
                    WHERE id = %s
                    AND user_id = (
                        SELECT id
                        FROM public.users
                        WHERE telegram_id = %s
                    )
                    """,
                    (
                        mistake_id,
                        telegram_id
                    )
                )

                deleted = cur.rowcount

        # ========================================================
        # ОШИБКА НЕ НАЙДЕНА
        # ========================================================

        if deleted == 0:

            return jsonify({
                "ok": False,
                "error":
                    "Ошибка не найдена."
            }), 404

        # ========================================================
        # УСПЕШНО
        # ========================================================

        print(
            "DB: Ошибка удалена.",
            "mistake_id =",
            mistake_id,
            "telegram_id =",
            telegram_id
        )

        return jsonify({

            "ok": True,

            "deleted_id":
                mistake_id

        })

    except Exception as error:

        print(
            "ОШИБКА УДАЛЕНИЯ ОШИБКИ:",
            repr(error)
        )

        return jsonify({

            "ok": False,

            "error":
                "Ошибка базы данных."

        }), 500

    finally:

        if conn:

            conn.close()

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