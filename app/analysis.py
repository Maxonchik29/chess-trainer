import chess
import chess.pgn
import chess.engine
import json
import os
from datetime import datetime


DEBUG = False


from app.tactical_themes import detect_theme
from app.explanation_generator import explain_position

from app.mistake_storage import (
    load_mistakes,
    save_mistakes,
    serialize_mistake
)

from app.mistake_explanations import explain_by_loss
from app.mistake_builder import build_mistake

from app.tactics_detector import (
    detect_hanging_piece,
    analyze_tactical_features
)

from app.mistake_storage import save_new_mistakes

from app.tactical_analyzer import TacticalAnalyzer


# ==========================================================
# ЦЕННОСТИ ФИГУР
# ==========================================================

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9
}


# ==========================================================
# НАЗВАНИЯ ФИГУР
# ==========================================================

PIECE_NAMES = {
    chess.PAWN: "пешку",
    chess.KNIGHT: "коня",
    chess.BISHOP: "слона",
    chess.ROOK: "ладью",
    chess.QUEEN: "ферзя"
}


# ==========================================================
# ПОРОГ ОШИБКИ
# ==========================================================

MISTAKE_THRESHOLD = 40


# ==========================================================
# ПОРОГ РАВНОЦЕННЫХ ХОДОВ
# ==========================================================

EQUIVALENT_MOVE_THRESHOLD = 30


# ============================================================
# НАСТРОЙКИ АНАЛИЗА
# ============================================================

if os.name == "nt":

    # Windows — полноценный анализ
    ANALYSIS_DEPTH = 12
    DEEP_ANALYSIS_DEPTH = 14

    ANALYSIS_MULTIPV = 5
    DEEP_ANALYSIS_MULTIPV = 3

else:

    # Render / Linux — облегчённый анализ
    ANALYSIS_DEPTH = 10
    DEEP_ANALYSIS_DEPTH = 10

    ANALYSIS_MULTIPV = 3
    DEEP_ANALYSIS_MULTIPV = 2


# ==========================================================
# ПУТЬ К АРХИВУ АНАЛИЗОВ
# ==========================================================

ANALYSIS_RESULTS_FILE = "data/analysis_results.json"
GROSS_MISTAKES_FILE = "data/gross_mistakes.json"


# ==========================================================
# ЗАГРУЗКА ПАРТИИ
# ==========================================================

def load_game(filename):

    with open(
        filename,
        encoding="utf-8"
    ) as file:

        game = chess.pgn.read_game(
            file
        )

    return game


# ==========================================================
# ПОЛУЧИТЬ ХОДЫ
# ==========================================================

def get_moves(game):

    return list(
        game.mainline_moves()
    )


# ==========================================================
# STOCKFISH
# ==========================================================

def get_engine():

    # ======================================================
    # STOCKFISH
    # ======================================================

    if os.name == "nt":

        # Windows
        engine_path = "engine/stockfish.exe"

    else:

        # Render / Linux
        engine_path = "/usr/games/stockfish"

    print(
        "STOCKFISH:",
        engine_path
    )

    engine = chess.engine.SimpleEngine.popen_uci(
        engine_path
    )

    # ======================================================
    # ОГРАНИЧЕНИЕ ПАМЯТИ
    # ======================================================

    try:

        engine.configure({
            "Threads": 1,
            "Hash": 8
        })

        print(
            "STOCKFISH SETTINGS:",
            "Threads=1",
            "Hash=8MB"
        )

    except Exception as error:

        print(
            "НЕ УДАЛОСЬ НАСТРОИТЬ STOCKFISH:",
            repr(error)
        )

    return engine


# ==========================================================
# ТЕСТ ДВИЖКА
# ==========================================================

def test_engine():

    engine = get_engine()

    info = engine.analyse(
        chess.Board(),
        chess.engine.Limit(
            depth=12
        )
    )

    print(
        info["score"]
    )

    engine.quit()


# ==========================================================
# АНАЛИЗ ПОЗИЦИИ
# ==========================================================

def analyze_position(board):

    engine = get_engine()

    info = engine.analyse(
        board,
        chess.engine.Limit(
            depth=15
        )
    )

    engine.quit()

    return info


# ==========================================================
# ОБЩЕЕ ОБЪЯСНЕНИЕ ОШИБКИ
# ==========================================================

def explain_mistake(loss):

    if loss < 200:

        return (
            "Небольшая неточность. "
            "Можно было найти более сильный ход."
        )

    elif loss < 500:

        return (
            "Ошибка. "
            "После этого хода позиция заметно ухудшилась."
        )

    elif loss < 1000:

        return (
            "Грубая ошибка. "
            "Вы потеряли большое преимущество."
        )

    else:

        return (
            "Зевок! "
            "Скорее всего, потеряна фигура "
            "или пропущена решающая угроза."
        )


# ==========================================================
# ФОРМАТ ОЦЕНКИ
# ==========================================================

def format_score(score):

    if score is None:
        return "?"

    if score > 0:

        return (
            f"+{score / 100:.2f}"
        )

    return (
        f"{score / 100:.2f}"
    )


# ==========================================================
# ТОЧНОСТЬ
# ==========================================================

def calculate_accuracy(scores):

    if not scores:
        return 100

    total_loss = 0

    for i in range(
        1,
        len(scores)
    ):

        loss = abs(
            scores[i] - scores[i - 1]
        )

        if loss > 0:

            total_loss += loss

    accuracy = max(
        0,
        100 - total_loss / len(scores) / 10
    )

    return round(
        accuracy
    )


# ==========================================================
# СТАТИСТИКА ОШИБОК
# ==========================================================

def calculate_statistics(mistakes):

    stats = {
        "inaccuracies": 0,
        "mistakes": 0,
        "blunders": 0
    }

    for mistake in mistakes:

        if mistake["type"] == "🟡 Неточность":

            stats["inaccuracies"] += 1

        elif mistake["type"] == "🟠 Ошибка":

            stats["mistakes"] += 1

        elif mistake["type"] == "🔴 Грубая ошибка":

            stats["blunders"] += 1

    return stats


# ==========================================================
# СРЕДНЕЕ
# ==========================================================

def average(lst):

    if not lst:
        return 0

    return round(
        sum(lst) / len(lst)
    )


# ==========================================================
# ТАКТИЧЕСКИЕ УГРОЗЫ
# ==========================================================

def detect_tactical_threat(
    board_after_move,
    engine
):
    """
    Ищет тактические угрозы соперника
    в первых ходах нескольких главных вариантов.
    """

    results = engine.analyse(

        board_after_move,

        chess.engine.Limit(

            depth=DEEP_ANALYSIS_DEPTH

        ),

        multipv=DEEP_ANALYSIS_MULTIPV

    )

    threats = []

    for engine_result in results:

        pv = engine_result.get(
            "pv",
            []
        )

        if not pv:
            continue

        test_board = (
            board_after_move.copy()
        )

        for move in pv[:5]:

            if move not in test_board.legal_moves:
                break

            san = test_board.san(
                move
            )

            test_board.push(
                move
            )

            # --------------------------------------------------
            # МАТ
            # --------------------------------------------------

            if test_board.is_checkmate():

                threats.append({
                    "move": san,
                    "uci": move.uci(),
                    "type": "mate"
                })

                break

            # --------------------------------------------------
            # ШАХ
            # --------------------------------------------------

            if test_board.is_check():

                threats.append({
                    "move": san,
                    "uci": move.uci(),
                    "type": "check"
                })

    return threats


# ==========================================================
# JSON SAFE
# ==========================================================

def make_json_safe(value):

    if isinstance(
        value,
        dict
    ):

        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        list
    ):

        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        tuple
    ):

        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        set
    ):

        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        chess.Board
    ):

        return value.fen()

    if isinstance(
        value,
        chess.Move
    ):

        return value.uci()

    if isinstance(
        value,
        chess.Piece
    ):

        return {
            "piece_type": value.piece_type,
            "color": value.color
        }

    if isinstance(
        value,
        datetime
    ):

        return value.isoformat()

    if (
        value is None
        or isinstance(
            value,
            (
                str,
                int,
                float,
                bool
            )
        )
    ):

        return value

    return str(
        value
    )


# ==========================================================
# ЗАГРУЗИТЬ АРХИВ АНАЛИЗОВ
# ==========================================================

def load_analysis_results():

    if not os.path.exists(
        ANALYSIS_RESULTS_FILE
    ):

        return []

    try:

        with open(
            ANALYSIS_RESULTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

            if isinstance(
                data,
                list
            ):

                return data

            return []

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

        return []


# ==========================================================
# СОХРАНИТЬ ГРУБЫЕ ОШИБКИ
# ==========================================================

def save_gross_mistakes(mistakes):

    gross_mistakes = []

    for mistake in mistakes:

        if not isinstance(mistake, dict):
            continue

        try:
            loss = float(
                mistake.get("loss", 0)
            )
        except (
            TypeError,
            ValueError
        ):
            continue

        # Грубая ошибка = loss > 130
        if loss > 130:
            gross_mistakes.append(
                mistake
            )

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        GROSS_MISTAKES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            make_json_safe(
                gross_mistakes
            ),
            file,
            ensure_ascii=False,
            indent=4
        )

    print(
        f"Создан/обновлён файл: "
        f"{os.path.abspath(GROSS_MISTAKES_FILE)}"
    )

    print(
        f"Грубых ошибок (loss > 130): "
        f"{len(gross_mistakes)}"
    )


# ==========================================================
# СОХРАНИТЬ РЕЗУЛЬТАТ АНАЛИЗА ПАРТИИ
# ==========================================================

def save_analysis_result(
    white_player,
    black_player,
    date,
    event,
    site,
    game_result,
    user_color,
    accuracy,
    statistics,
    phase_statistics,
    mistakes,
    analysis_start_move=1,
    analysis_end_move=None
):
    """
    Сохраняет результат анализа одной партии
    в отдельный архив.

    analysis_start_move / analysis_end_move
    позволяют сохранить информацию о том,
    какой диапазон партии был проанализирован.

    ВАЖНО:
    эта функция НИКОГДА не используется
    для построения текущего анализа.

    Она только сохраняет уже полученный результат.
    """

    os.makedirs(
        "data",
        exist_ok=True
    )

    analysis_results = (
        load_analysis_results()
    )

    # ------------------------------------------------------
    # Уникальный идентификатор конкретного анализа
    # ------------------------------------------------------

    analysis_id = (
        datetime.now()
        .strftime("%Y%m%d_%H%M%S_%f")
    )

    # ------------------------------------------------------
    # Формируем отдельную запись партии
    # ------------------------------------------------------

    analysis_record = {

        "analysis_id": analysis_id,

        "analyzed_at": (
            datetime.now().isoformat()
        ),

        # --------------------------------------------------
        # ДИАПАЗОН АНАЛИЗА
        # --------------------------------------------------

        "analysis_range": {

            "start_move": analysis_start_move,

            "end_move": analysis_end_move

        },

        "game": {

            "white": white_player,

            "black": black_player,

            "date": date,

            "event": event,

            "site": site,

            "result": game_result

        },

        "user_color": user_color,

        "accuracy": accuracy,

        "statistics": statistics,

        "phase_statistics": phase_statistics,

        "mistakes": mistakes

    }

    # ------------------------------------------------------
    # Превращаем chess-объекты в JSON
    # ------------------------------------------------------

    analysis_record = make_json_safe(
        analysis_record
    )

    # ------------------------------------------------------
    # Добавляем НОВУЮ партию
    #
    # Старые записи не заменяются.
    # ------------------------------------------------------

    analysis_results.append(
        analysis_record
    )

    # ------------------------------------------------------
    # Сохраняем архив
    # ------------------------------------------------------

    with open(
        ANALYSIS_RESULTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            analysis_results,
            file,
            ensure_ascii=False,
            indent=4
        )

    save_gross_mistakes(
        mistakes
    )

    print(
        "\n========================================"
    )

    print(
        "АНАЛИЗ ПАРТИИ СОХРАНЁН В АРХИВ"
    )

    print(
        f"Файл: {os.path.abspath(ANALYSIS_RESULTS_FILE)}"
    )

    print(
        f"ID анализа: {analysis_id}"
    )

    print(
        f"White: {white_player}"
    )

    print(
        f"Black: {black_player}"
    )

    print(
        f"Result: {game_result}"
    )

    print(
        "Диапазон анализа:",
        analysis_start_move,
        "-",
        analysis_end_move
        if analysis_end_move is not None
        else "конец"
    )

    print(
        f"Ошибок: {len(mistakes)}"
    )

    print(
        "========================================\n"
    )


# ==========================================================
# ОСНОВНОЙ АНАЛИЗ ПАРТИИ
# ==========================================================

def analyze_game(
    game,
    start_move=1,
    end_move=None,
    progress_callback=None,
    mistake_threshold=None,
    user_color=None
):

    # ======================================================
    # ПОРОГ ОШИБКИ ДЛЯ ТЕКУЩЕГО РЕЖИМА
    # ======================================================

    if mistake_threshold is None:
        mistake_threshold = MISTAKE_THRESHOLD

    try:
        mistake_threshold = int(
            mistake_threshold
        )
    except (
        TypeError,
        ValueError
    ):
        mistake_threshold = MISTAKE_THRESHOLD

    if mistake_threshold < 0:
        mistake_threshold = MISTAKE_THRESHOLD

    print(
        "ПОРОГ ОШИБКИ:",
        mistake_threshold,
        "cp"
    )

    # ======================================================
    # ЗАЩИТА ОТ ПУСТОЙ ПАРТИИ
    # ======================================================

    if game is None:

        print(
            "!!! ОШИБКА: game == None !!!"
        )

        if progress_callback:
            progress_callback(100)

        return (
            [],
            [],
            100,
            {
                "inaccuracies": 0,
                "mistakes": 0,
                "blunders": 0
            },
            {
                "opening": 0,
                "middlegame": 0,
                "endgame": 0
            },
            None
        )

    # ======================================================
    # ПРОВЕРКА ДИАПАЗОНА
    # ======================================================

    try:

        start_move = int(
            start_move
        )

    except (
        TypeError,
        ValueError
    ):

        start_move = 1

    if start_move < 1:

        start_move = 1

    if end_move is not None:

        try:

            end_move = int(
                end_move
            )

        except (
            TypeError,
            ValueError
        ):

            end_move = None

        if (
            end_move is not None
            and end_move < start_move
        ):

            print(
                "!!! ОШИБКА: "
                "end_move меньше start_move !!!"
            )

            if progress_callback:
                progress_callback(100)

            return (
                [],
                [],
                100,
                {
                    "inaccuracies": 0,
                    "mistakes": 0,
                    "blunders": 0
                },
                {
                    "opening": 0,
                    "middlegame": 0,
                    "endgame": 0
                },
                None
            )

    print(
        "\n=========================================================="
    )

    print(
        "ДИАПАЗОН АНАЛИЗА:"
    )

    print(
        f"От хода: {start_move}"
    )

    print(
        "До хода:",
        end_move
        if end_move is not None
        else "конца партии"
    )

    print(
        "=========================================================="
    )

    # ======================================================
    # ИНФОРМАЦИЯ О ПАРТИИ
    # ======================================================

    headers = game.headers

    white_player = headers.get(
        "White",
        ""
    )

    black_player = headers.get(
        "Black",
        ""
    )

    event = headers.get(
        "Event",
        ""
    )

    site = headers.get(
        "Site",
        ""
    )

    date = headers.get(
        "Date",
        ""
    )

    game_result = headers.get(
        "Result",
        ""
    )

    print(
        "\n"
        "=========================================================="
    )

    print(
        "НАЧАЛО АНАЛИЗА ПАРТИИ"
    )

    print(
        f"White: {white_player}"
    )

    print(
        f"Black: {black_player}"
    )

    print(
        f"Date: {date}"
    )

    print(
        f"Event: {event}"
    )

    print(
        f"Site: {site}"
    )

    print(
        f"Result: {game_result}"
    )

    print(
        "=========================================================="
    )

    # ======================================================
    # ОПРЕДЕЛЯЕМ ЦВЕТ ПОЛЬЗОВАТЕЛЯ
    # ======================================================

    # Если цвет уже передан из ChessGame,
    # используем именно его.
    #
    # Это основной вариант для игры против компьютера.

    if user_color not in (
        "white",
        "black"
    ):

        if user_color not in ("white", "black"):

            user_color = None

            if "Maximka2912" in white_player:
                user_color = "white"

            elif "Maximka2912" in black_player:
                user_color = "black"


    print(
        "ЦВЕТ ПОЛЬЗОВАТЕЛЯ =",
        user_color
    )

    if user_color is None:

        print(
            "!!! ВНИМАНИЕ: "
            "Не удалось определить цвет пользователя !!!"
        )

    # ======================================================
    # НАЧАЛЬНАЯ ПОЗИЦИЯ
    # ======================================================

    board = game.board()

    # ======================================================
    # STOCKFISH
    # ======================================================

    engine = get_engine()

    mistakes = []

    scores = []

    opening_scores = []
    middlegame_scores = []
    endgame_scores = []

    # ======================================================
    # ХОДЫ ПАРТИИ
    # ======================================================

    all_moves = list(
        game.mainline_moves()
    )

    # ======================================================
    # ПОДСЧЁТ ХОДОВ ПОЛЬЗОВАТЕЛЯ
    # В ВЫБРАННОМ ДИАПАЗОНЕ
    # ======================================================

    progress_board = game.board()

    total_analysis_moves = 0

    for progress_move in all_moves:

        progress_move_number = (
            progress_board.fullmove_number
        )

        if (
            progress_move_number >= start_move
            and (
                end_move is None
                or progress_move_number <= end_move
            )
            and (
                (
                    progress_board.turn == chess.WHITE
                    and user_color == "white"
                )
                or
                (
                    progress_board.turn == chess.BLACK
                    and user_color == "black"
                )
            )
        ):

            total_analysis_moves += 1

        progress_board.push(
            progress_move
        )

    print(
        "ХОДОВ ПОЛЬЗОВАТЕЛЯ ДЛЯ АНАЛИЗА:",
        total_analysis_moves
    )

    # ======================================================
    # ПРОГРЕСС
    # ======================================================

    processed_analysis_moves = 0
    last_progress = -1

    def report_progress():

        nonlocal last_progress

        if progress_callback is None:
            return

        if total_analysis_moves <= 0:

            if last_progress != 100:

                last_progress = 100

                progress_callback(100)

            return

        progress = int(
            (
                processed_analysis_moves
                /
                total_analysis_moves
            ) * 100
        )

        progress = max(
            0,
            min(
                99,
                progress
            )
        )

        if progress != last_progress:

            last_progress = progress

            progress_callback(
                progress
            )

    # ======================================================
    # ПРОХОДИМ ПО ВСЕЙ ПАРТИИ
    # ======================================================

    for number, move in enumerate(
        all_moves,
        start=1
    ):

        side = (
            "white"
            if board.turn == chess.WHITE
            else "black"
        )

        # ==================================================
        # НОМЕР ШАХМАТНОГО ХОДА
        # ==================================================

        current_move_number = (
            board.fullmove_number
        )

        # ==================================================
        # ХОДЫ ДО НАЧАЛА ДИАПАЗОНА
        # ==================================================

        if current_move_number < start_move:

            board.push(
                move
            )

            continue

        # ==================================================
        # ХОДЫ ПОСЛЕ КОНЦА ДИАПАЗОНА
        # ==================================================

        if (
            end_move is not None
            and current_move_number > end_move
        ):

            print(
                "\n=========================================================="
            )

            print(
                "ДОСТИГНУТ КОНЕЦ ДИАПАЗОНА АНАЛИЗА"
            )

            print(
                f"Остановились перед ходом {current_move_number}"
            )

            print(
                "=========================================================="
            )

            break

        # ==================================================
        # ПРОПУСКАЕМ ХОДЫ СОПЕРНИКА
        # ==================================================

        if side != user_color:

            board.push(
                move
            )

            continue

        # ==================================================
        # НАЧАЛО ОБРАБОТКИ ХОДА ПОЛЬЗОВАТЕЛЯ
        #
        # Здесь обновляем прогресс.
        #
        # Процент означает:
        # сколько пользовательских ходов
        # уже взято в работу.
        # ==================================================

        processed_analysis_moves += 1

        report_progress()

        # ==================================================
        # ПОЗИЦИЯ ДО ХОДА
        # ==================================================

        position_before = (
            board.copy()
        )

        # ==================================================
        # АНАЛИЗ ПОЗИЦИИ ДО ХОДА
        # ==================================================

        before = engine.analyse(

            board,

            chess.engine.Limit(

                depth=ANALYSIS_DEPTH

            ),

            multipv=ANALYSIS_MULTIPV

        )

        if not before:

            board.push(
                move
            )

            continue

        # ==================================================
        # ОЦЕНКА ДО ХОДА
        # ==================================================

        before_score = (
            before[0]["score"]
            .white()
            .score(
                mate_score=10000
            )
        )

        scores.append(
            before_score
        )

        # ==================================================
        # ФАЗА ПАРТИИ
        # ==================================================

        move_number = (
            board.fullmove_number
        )

        pieces_count = len(
            board.piece_map()
        )

        if move_number <= 10:

            opening_scores.append(
                before_score
            )

        elif pieces_count > 12:

            middlegame_scores.append(
                before_score
            )

        else:

            endgame_scores.append(
                before_score
            )

        # ==================================================
        # FEN
        # ==================================================

        fen = board.fen()

        # ==================================================
        # ЛУЧШИЕ ЛИНИИ
        # ==================================================

        best_lines = before

        if not best_lines:

            board.push(
                move
            )

            continue

        # ==================================================
        # ЛУЧШИЙ ХОД
        # ==================================================

        first_line = best_lines[0]

        pv = first_line.get(
            "pv",
            []
        )

        if not pv:

            board.push(
                move
            )

            continue

        best_move = pv[0]

        score = first_line.get(
            "score"
        )

        # ==================================================
        # ЛУЧШАЯ ОЦЕНКА
        # ==================================================

        best_score_for_side = None

        if score is not None:

            try:

                best_score_for_side = (
                    score
                    .white()
                    .score(
                        mate_score=10000
                    )
                )

            except Exception:

                best_score_for_side = None

        # ==================================================
        # РАВНОЦЕННЫЕ ЛУЧШИЕ ХОДЫ
        # ==================================================

        equivalent_best_moves = []

        if best_score_for_side is not None:

            for line in best_lines:

                line_pv = line.get(
                    "pv",
                    []
                )

                if not line_pv:
                    continue

                candidate_move = line_pv[0]

                if candidate_move == best_move:
                    continue

                candidate_score_obj = (
                    line.get("score")
                )

                if candidate_score_obj is None:
                    continue

                try:

                    candidate_score = (
                        candidate_score_obj
                        .white()
                        .score(
                            mate_score=10000
                        )
                    )

                except Exception:

                    continue

                if candidate_score is None:
                    continue

                if position_before.turn == chess.WHITE:

                    difference = (
                        best_score_for_side
                        - candidate_score
                    )

                else:

                    difference = (
                        candidate_score
                        - best_score_for_side
                    )

                difference = max(
                    0,
                    difference
                )

                if (
                    difference
                    <= EQUIVALENT_MOVE_THRESHOLD
                ):

                    try:

                        candidate_san = (
                            position_before.san(
                                candidate_move
                            )
                        )

                    except Exception:

                        candidate_san = (
                            candidate_move.uci()
                        )

                    equivalent_best_moves.append({

                        "move": candidate_move,

                        "san": candidate_san,

                        "score": candidate_score,

                        "difference": difference

                    })

        # ==================================================
        # SAN ЛУЧШЕГО ХОДА
        # ==================================================

        try:

            best_move_san = (
                position_before.san(
                    best_move
                )
            )

        except Exception:

            best_move_san = (
                best_move.uci()
            )

        # ==================================================
        # SAN СЫГРАННОГО ХОДА
        # ==================================================

        try:

            played_move_san = (
                position_before.san(
                    move
                )
            )

        except Exception:

            played_move_san = (
                move.uci()
            )

        # ==================================================
        # ПРОВЕРКА ЛУЧШЕГО ХОДА
        # ==================================================

        played_is_best = (
            move == best_move
        )

        # ==================================================
        # ПРОВЕРКА РАВНОЦЕННОГО ХОДА
        # ==================================================

        played_is_equivalent = any(
            item.get("move") == move
            for item in equivalent_best_moves
        )

        # ==================================================
        # ОТЛАДКА РАВНОЦЕННЫХ ХОДОВ
        # ==================================================

        print(
            "\n=== РАВНОЦЕННЫЕ ХОДЫ ==="
        )

        print(
            "NUMBER =",
            number
        )

        print(
            "FULLMOVE =",
            move_number
        )

        print(
            "SIDE =",
            side
        )

        print(
            "PLAYED MOVE =",
            move
        )

        print(
            "PLAYED SAN =",
            played_move_san
        )

        print(
            "BEST MOVE =",
            best_move
        )

        print(
            "BEST SAN =",
            best_move_san
        )

        print(
            "BEST SCORE =",
            best_score_for_side
        )

        print(
            "PLAYED IS BEST =",
            played_is_best
        )

        print(
            "PLAYED IS EQUIVALENT =",
            played_is_equivalent
        )

        if equivalent_best_moves:

            for item in equivalent_best_moves:

                print(
                    f"  {item['san']} | "
                    f"оценка {item['score']} | "
                    f"разница {item['difference']} cp"
                )

        else:

            print(
                "  Нет равноценных ходов"
            )

        print(
            "========================="
        )

        # ==================================================
        # ЛУЧШИЙ ХОД
        # ==================================================

        if played_is_best:

            print(
                f"\nХод {number}"
            )

            print(
                f"Сыграно: {move}"
            )

            print(
                f"Лучший ход: {best_move}"
            )

            print(
                "Сыгран лучший ход Stockfish"
            )

            print(
                f"Сыграно SAN: {played_move_san}"
            )

            print(
                f"Лучший SAN: {best_move_san}"
            )

            print(
                "ОШИБКА НЕ СОЗДАЁТСЯ"
            )

            print(
                "========================"
            )

            board.push(
                move
            )

            continue

        # ==================================================
        # РАВНОЦЕННЫЙ ХОД
        # ==================================================

        if played_is_equivalent:

            equivalent_difference = next(
                (
                    item["difference"]
                    for item in equivalent_best_moves
                    if item.get("move") == move
                ),
                None
            )

            print(
                f"\nХод {number}"
            )

            print(
                f"Сыграно: {move}"
            )

            print(
                f"Лучший ход: {best_move}"
            )

            print(
                "Ход практически равноценен лучшему"
            )

            print(
                f"Сыграно SAN: {played_move_san}"
            )

            print(
                f"Лучший SAN: {best_move_san}"
            )

            print(
                "ХОД НЕ СЧИТАЕТСЯ ОШИБКОЙ"
            )

            print(
                "РАЗНИЦА =",
                equivalent_difference,
                "cp"
            )

            print(
                "========================"
            )

            board.push(
                move
            )

            continue

        # ==================================================
        # ПОЗИЦИЯ ПОСЛЕ ЛУЧШЕГО ХОДА
        # ==================================================

        best_board = (
            position_before.copy()
        )

        best_board.push(
            best_move
        )

        # ==================================================
        # ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ
        # ==================================================

        best_analysis = engine.analyse(
            best_board,
            chess.engine.Limit(
                depth=12
            )
        )

        best_score_obj = (
            best_analysis["score"]
            .white()
        )

        best_score = (
            best_analysis["score"]
            .white()
            .score(
                mate_score=10000
            )
        )

        # ==================================================
        # ОТЛАДКА
        # ==================================================

        print(
            f"\nХод {number}"
        )

        print(
            f"Сыграно: {move}"
        )

        print(
            f"Лучший ход: {best_move}"
        )

        print(
            "Ход отличается от рекомендации Stockfish"
        )

        print(
            f"Оценка до хода: {score}"
        )

        print(
            f"Лучший ход SAN: "
            f"{best_move_san}"
        )

        # ==================================================
        # СТОРОНА ХОДА
        # ==================================================

        side = (
            "white"
            if position_before.turn == chess.WHITE
            else "black"
        )

        # ==================================================
        # СЫГРАННЫЙ ХОД
        # ==================================================

        board.push(
            move
        )

        position_after = (
            board.copy()
        )

        # ==================================================
        # СЛОН СТАЛ АТАКОВАН
        # ==================================================

        bishop_attack_reason = None

        moved_piece = (
            position_after.piece_at(
                move.to_square
            )
        )

        if (
            moved_piece is not None
            and moved_piece.piece_type == chess.BISHOP
            and moved_piece.color == position_before.turn
        ):

            opponent = (
                not position_before.turn
            )

            attackers_before = (
                position_before.attackers(
                    opponent,
                    move.to_square
                )
            )

            attackers_after = (
                position_after.attackers(
                    opponent,
                    move.to_square
                )
            )

            new_attackers = (
                attackers_after
                - attackers_before
            )

            if new_attackers:

                print(
                    "!!! НАЙДЕНА НОВАЯ "
                    "АТАКА НА СЛОНА !!!"
                )

                print(
                    "СЛОН:",
                    chess.square_name(
                        move.to_square
                    )
                )

                print(
                    "АТАКУЮЩИЕ:",
                    [
                        chess.square_name(
                            square
                        )
                        for square in new_attackers
                    ]
                )

                bishop_attack_reason = (
                    "Вы позволили сопернику "
                    "атаковать вашего слона."
                )

                print(
                    "!!! ПОСЛЕ ХОДА СЛОН "
                    "ПОЛУЧИЛ НОВУЮ АТАКУ !!!"
                )

        # ==================================================
        # АНАЛИЗ ПОСЛЕ СЫГРАННОГО ХОДА
        # ==================================================

        after = engine.analyse(
            board,
            chess.engine.Limit(
                depth=12
            )
        )

        after_score = (
            after["score"]
            .white()
            .score(
                mate_score=10000
            )
        )

        # ==================================================
        # ПОТЕРЯ
        # ==================================================

        if position_before.turn == chess.WHITE:

            loss = (
                before_score
                - after_score
            )

        else:

            loss = (
                after_score
                - before_score
            )

        loss = max(
            0,
            loss
        )

        # ==================================================
        # ОТЛАДКА ПОТЕРИ
        # ==================================================

        print(
            "!!! АНАЛИЗ ПОТЕРИ !!!"
        )

        print(
            "NUMBER =",
            number
        )

        print(
            "ХОД =",
            move_number
        )

        print(
            "СТОРОНА =",
            side
        )

        print(
            "BEFORE SCORE =",
            before_score
        )

        print(
            "AFTER SCORE =",
            after_score
        )

        print(
            "BEST SCORE =",
            best_score
        )

        print(
            "LOSS =",
            loss
        )

        print(
            "СЫГРАНО =",
            played_move_san
        )

        print(
            "ЛУЧШИЙ ХОД =",
            best_move_san
        )

        print(
            "========================"
        )

        # ==================================================
        # ПРОВЕРКА НА ОШИБКУ
        # ==================================================

        if loss >= mistake_threshold:

            print(
                "!!! IF LOSS СРАБОТАЛ !!!"
            )

            print(
                "NUMBER =",
                number
            )

            print(
                "LOSS =",
                loss
            )

            # ==================================================
            # ТИП ОШИБКИ
            # ==================================================

            if loss < 100:

                mistake_type = (
                    "🟡 Неточность"
                )

            elif loss < 300:

                mistake_type = (
                    "🟠 Ошибка"
                )

            else:

                mistake_type = (
                    "🔴 Грубая ошибка"
                )

            # ==================================================
            # ТАКТИЧЕСКИЙ АНАЛИЗ
            # ==================================================

            print(
                "!!! СОЗДАЮ "
                "TACTICAL ANALYZER !!!"
            )

            analyzer = TacticalAnalyzer(
                position_before,
                best_move,
                move
            )

            features = (
                analyzer.analyze()
            )

            # ==================================================
            # ПРИЧИНА ХОДА
            # ==================================================

            from app.move_reason_detector import (
                detect_move_reason
            )

            move_reasons = (
                detect_move_reason(
                    position_before,
                    position_after,
                    move
                )
            )

            # ==================================================
            # ОТЛАДКА ТАКТИКИ
            # ==================================================

            print(
                "=== TACTICAL FEATURES ==="
            )

            print(
                features
            )

            print(
                "THEME =",
                features.get(
                    "theme"
                )
            )

            print(
                "FORK =",
                features.get(
                    "fork"
                )
            )

            print(
                "FORK TARGETS =",
                features.get(
                    "fork_targets"
                )
            )

            print(
                "PIN =",
                features.get(
                    "pin"
                )
            )

            print(
                "PIN PIECE =",
                features.get(
                    "pin_piece"
                )
            )

            print(
                "PIN SQUARE =",
                features.get(
                    "pin_square"
                )
            )

            print(
                "=========================="
            )

            # ==================================================
            # ПОЗИЦИЯ ПОСЛЕ СЫГРАННОГО ХОДА
            # ==================================================

            position_after_played = (
                position_before.copy()
            )

            position_after_played.push(
                move
            )

            # ==================================================
            # ТАКТИЧЕСКИЕ УГРОЗЫ
            # ==================================================

            tactical_threats = (
                detect_tactical_threat(
                    position_after_played,
                    engine
                )
            )

            print(
                "=== ТАКТИЧЕСКИЕ УГРОЗЫ ==="
            )

            print(
                tactical_threats
            )

            print(
                "=========================="
            )

            # ==================================================
            # АНАЛИЗ ПОСЛЕ СЫГРАННОГО ХОДА
            # ==================================================

            print(
                "\n--- После сыгранного хода ---"
            )

            played_results = (

                engine.analyse(

                    position_after_played,

                    chess.engine.Limit(

                        depth=DEEP_ANALYSIS_DEPTH

                    ),

                    multipv=DEEP_ANALYSIS_MULTIPV

                )

            )

            for i, engine_result in enumerate(
                played_results,
                start=1
            ):

                pv = engine_result.get(
                    "pv",
                    []
                )

                if not pv:

                    print(
                        f"{i}. "
                        "Вариант без продолжения"
                    )

                    continue

                first_move = pv[0]

                san = (
                    position_after_played.san(
                        first_move
                    )
                )

                score_obj = engine_result.get(
                    "score"
                )

                if score_obj is not None:

                    score_value = (
                        score_obj
                        .white()
                        .score(
                            mate_score=10000
                        )
                    )

                    score_text = (
                        f"{score_value / 100:.2f}"
                    )

                else:

                    score_text = (
                        "нет оценки"
                    )

                pv_text = (
                    position_after_played.variation_san(
                        pv[:5]
                    )
                )

                print(
                    f"{i}. {san} | "
                    f"оценка {score_text} | "
                    f"продолжение: {pv_text}"
                )

            # ==================================================
            # ПОЗИЦИЯ ПОСЛЕ ЛУЧШЕГО ХОДА
            # ==================================================

            position_after_best = (
                position_before.copy()
            )

            position_after_best.push(
                best_move
            )

            # ==================================================
            # АНАЛИЗ ПОСЛЕ ЛУЧШЕГО ХОДА
            # ==================================================

            print(
                "\n--- После лучшего хода ---"
            )

            best_results = (
                engine.analyse(
                    position_after_best,
                    chess.engine.Limit(
                        depth=DEEP_ANALYSIS_DEPTH
                    ),
                    multipv=DEEP_ANALYSIS_MULTIPV
                )
            )

            for i, engine_result in enumerate(
                best_results,
                start=1
            ):

                pv = engine_result.get(
                    "pv",
                    []
                )

                if not pv:

                    print(
                        f"{i}. "
                        "Вариант без продолжения"
                    )

                    continue

                first_move = pv[0]

                san = (
                    position_after_best.san(
                        first_move
                    )
                )

                score_obj = engine_result.get(
                    "score"
                )

                if score_obj is not None:

                    score_value = (
                        score_obj
                        .white()
                        .score(
                            mate_score=10000
                        )
                    )

                    score_text = (
                        f"{score_value / 100:.2f}"
                    )

                else:

                    score_text = (
                        "нет оценки"
                    )

                pv_text = (
                    position_after_best.variation_san(
                        pv[:5]
                    )
                )

                print(
                    f"{i}. {san} | "
                    f"оценка {score_text} | "
                    f"продолжение: {pv_text}"
                )

            print(
                "=============================="
            )

            print(
                "BEST MOVE SAN =",
                best_move_san
            )

            print(
                "BEST MOVE UCI =",
                best_move
            )

            print(
                "BEFORE SCORE =",
                before_score
            )

            print(
                "AFTER SCORE =",
                after_score
            )

            print(
                "BEST SCORE =",
                best_score
            )

            print(
                "Потеря оценки =",
                loss
            )

            # ==================================================
            # АЛЬТЕРНАТИВНЫЕ ХОДЫ
            # ==================================================

            alternatives = []

            for line in best_lines:

                pv = line.get(
                    "pv",
                    []
                )

                if not pv:
                    continue

                alt_move = pv[0]

                try:

                    alt_san = (
                        position_before.san(
                            alt_move
                        )
                    )

                except Exception:

                    continue

                if alt_san not in alternatives:

                    alternatives.append(
                        alt_san
                    )

            # ==================================================
            # СОЗДАЁМ ОШИБКУ
            # ==================================================

            mistake = build_mistake(

                board=position_before,

                loss=loss,

                mistake_type=mistake_type,

                side=side,

                user_color=user_color,

                position_before=position_before,

                position_after=position_after,

                best_move=best_move,

                best_move_san=best_move_san,

                best_score_obj=best_score_obj,

                best_lines=best_lines,

                alternatives=alternatives,

                move=move,

                played_move_san=played_move_san,

                fen=fen,

                before_score=before_score,

                after_score=after_score,

                captured_piece=features.get(
                    "captured_piece"
                ),

                captured_value=features.get(
                    "captured_value"
                ),

                hanging_piece=features.get(
                    "hanging_piece"
                ),

                hanging_square=features.get(
                    "hanging_square"
                ),

                theme=features.get(
                    "theme"
                ),

                best_piece=features.get(
                    "best_piece"
                ),

                best_square=features.get(
                    "best_square"
                ),

                target_piece=features.get(
                    "target_piece"
                ),

                target_square=features.get(
                    "target_square"
                ),

                features=features,

                move_reasons=move_reasons,

                bishop_attack_reason=bishop_attack_reason,

                pawn_tempo_explanation=features.get(
                    "pawn_tempo_explanation"
                ),

                tactical_threats=tactical_threats,

                played_results=played_results,

                equivalent_best_moves=equivalent_best_moves,

            )

            # ==================================================
            # ОЦЕНКА ПОЗИЦИИ ДО ОШИБОЧНОГО ХОДА
            # ==================================================

            mistake["position_evaluation"] = before_score
            mistake["position_evaluation_before"] = before_score
            mistake["position_evaluation_best"] = best_score
            mistake["position_evaluation_after"] = after_score

            # ==================================================
            # РАВНОЦЕННЫЕ ХОДЫ
            # ==================================================

            mistake[
                "equivalent_best_moves"
            ] = (
                equivalent_best_moves
            )

            # ==================================================
            # ИНФОРМАЦИЯ О ПАРТИИ
            # ==================================================

            mistake[
                "game_white"
            ] = white_player

            mistake[
                "game_black"
            ] = black_player

            mistake[
                "game_date"
            ] = date

            mistake[
                "game_result"
            ] = game_result

            # ==================================================
            # ДОБАВЛЯЕМ В ТЕКУЩИЙ СПИСОК
            # ==================================================

            mistakes.append(
                mistake
            )

            print(
                "!!! ОШИБКА ДОБАВЛЕНА "
                "В СПИСОК !!!"
            )

        else:

            print(
                "Ход НЕ признан ошибкой."
            )

        print(
            f"Потеря оценки: {loss}"
        )

        print(
            "===================="
        )

    # ==============================================================
    # 100% — АНАЛИЗ ХОДОВ ЗАКОНЧЕН
    # ==============================================================

    if progress_callback:

        last_progress = 100

        progress_callback(
            100
        )

    # ==============================================================
    # ИТОГОВЫЕ ОШИБКИ
    # ==============================================================

    print(
        "\nНайденные ошибки:\n"
    )

    print(
        "========== TEST 1: ПОСЛЕ НАЙДЕННЫХ ОШИБОК ==========",
        flush=True
    )

    for mistake in mistakes:

        ply = mistake["move"]

        move_number_print = (
            (ply + 1) // 2
        )

        if ply % 2 == 1:

            side_print = "Белые"

            move_label = (
                f"{move_number_print}."
            )

        else:

            side_print = "Чёрные"

            move_label = (
                f"{move_number_print}..."
            )

        print(
            f"Ход {move_label} {side_print} | "
            f"Потеря {mistake['loss']} | "
            f"Лучший ход {mistake['best']}"
        )

        equivalent = mistake.get(
            "equivalent_best_moves",
            []
        )

        if equivalent:

            print(
                "  Практически равноценные:",
                ", ".join(
                    item.get(
                        "san",
                        ""
                    )
                    for item in equivalent
                    if item.get("san")
                )
            )

    # ==============================================================
    # СТАТИСТИКА
    # ==============================================================

    print(
        "========== DEBUG X: ЦИКЛ ВЫВОДА ОШИБОК ЗАКОНЧЕН ==========",
        flush=True
    )

    print(
        "========== DEBUG A: НАЧАЛО СТАТИСТИКИ =========="
    )

    accuracy = calculate_accuracy(
        scores
    )

    print(
        "========== DEBUG B: ACCURACY ГОТОВА =========="
    )

    statistics = calculate_statistics(
        mistakes
    )

    print(
        "========== DEBUG C: STATISTICS ГОТОВА =========="
    )

    phase_statistics = {

        "opening": average(
            opening_scores
        ),

        "middlegame": average(
            middlegame_scores
        ),

        "endgame": average(
            endgame_scores
        )
    }

    print(
        "========== DEBUG D: PHASE STATISTICS ГОТОВА =========="
    )

    # ==============================================================
    # ЗАКРЫВАЕМ STOCKFISH
    # ==============================================================

    print(
        "========== DEBUG E: ПЕРЕД ENGINE.QUIT =========="
    )

    engine.quit()

    print(
        "========== DEBUG F: ENGINE.QUIT ЗАВЕРШЁН =========="
    )

    # ==============================================================
    # СОХРАНЯЕМ ОШИБКИ ДЛЯ ТРЕНИРОВКИ
    # ==============================================================

    print(
        "========== DEBUG G: ПЕРЕД SAVE_NEW_MISTAKES =========="
    )

    save_new_mistakes(
        mistakes
    )

    print(
        "========== DEBUG H: SAVE_NEW_MISTAKES ЗАВЕРШЁН =========="
    )

    # ==============================================================
    # СОХРАНЯЕМ РЕЗУЛЬТАТ АНАЛИЗА
    # ==============================================================

    print(
        "========== DEBUG I: ПЕРЕД SAVE_ANALYSIS_RESULT =========="
    )

    save_analysis_result(

        white_player=white_player,

        black_player=black_player,

        date=date,

        event=event,

        site=site,

        game_result=game_result,

        user_color=user_color,

        accuracy=accuracy,

        statistics=statistics,

        phase_statistics=phase_statistics,

        mistakes=mistakes,

        analysis_start_move=start_move,

        analysis_end_move=end_move

    )

    print(
        "========== DEBUG J: SAVE_ANALYSIS_RESULT ЗАВЕРШЁН =========="
    )

    # ==============================================================
    # ЭКСПОРТ ДЛЯ МОБИЛЬНОГО ПРИЛОЖЕНИЯ
    # ==============================================================

    export_file = (
        "data/import_analysis.json"
    )

    print(
        "========== DEBUG K: ПЕРЕД MAKE_JSON_SAFE =========="
    )

    export_data = make_json_safe(
        mistakes
    )

    print(
        "========== DEBUG L: MAKE_JSON_SAFE ЗАВЕРШЁН =========="
    )

    os.makedirs(
        "data",
        exist_ok=True
    )

    print(
        "========== DEBUG M: ПАПКА DATA ГОТОВА =========="
    )

    with open(
        export_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            export_data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(
        "========== DEBUG N: JSON СОХРАНЁН =========="
    )

    print(
        "\n========================================"
    )

    print(
        "ФАЙЛ ТЕКУЩЕГО АНАЛИЗА СОЗДАН"
    )

    print(
        os.path.abspath(
            export_file
        )
    )

    print(
        "========================================\n"
    )

    # ==============================================================
    # ФИНАЛЬНАЯ ПРОВЕРКА
    # ==============================================================

    print(
        "=========================================================="
    )

    print(
        "АНАЛИЗ ПАРТИИ ЗАВЕРШЁН"
    )

    print(
        f"White: {white_player}"
    )

    print(
        f"Black: {black_player}"
    )

    print(
        f"Result: {game_result}"
    )

    print(
        "Диапазон анализа:",
        start_move,
        "-",
        end_move
        if end_move is not None
        else "конец партии"
    )

    print(
        f"Найдено ошибок: {len(mistakes)}"
    )

    print(
        "=========================================================="
    )

    print(
        "========== DEBUG O: ПЕРЕД RETURN ==========",
        flush=True
    )

    result = (
        mistakes,
        scores,
        accuracy,
        statistics,
        phase_statistics,
        user_color
    )

    print(
        "========== DEBUG P: RESULT СОЗДАН ==========",
        flush=True
    )

    return result