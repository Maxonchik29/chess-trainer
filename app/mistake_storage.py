import json
import os
import chess
from datetime import datetime, timedelta


MISTAKES_FILE = "mistakes.json"
GROSS_MISTAKES_FILE = "gross_mistakes.json"


# ==========================================================
# ЗАГРУЗКА
# ==========================================================

def load_mistakes():

    if not os.path.exists(MISTAKES_FILE):
        return []

    try:

        with open(
            MISTAKES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

        return []


# ==========================================================
# БЕЗОПАСНАЯ СЕРИАЛИЗАЦИЯ
# ==========================================================

def make_json_safe(value):
    """
    Превращает шахматные объекты и другие
    несериализуемые значения в обычные JSON-значения.
    """

    # chess.Move
    if isinstance(value, chess.Move):

        return value.uci()

    # chess.Board
    if isinstance(value, chess.Board):

        return value.fen()

    # chess.Piece
    if isinstance(value, chess.Piece):

        return {
            "piece_type": value.piece_type,
            "color": value.color
        }

    # chess.SquareSet / set
    if isinstance(value, (set, frozenset)):

        return [
            make_json_safe(item)
            for item in value
        ]

    # tuple
    if isinstance(value, tuple):

        return [
            make_json_safe(item)
            for item in value
        ]

    # list
    if isinstance(value, list):

        return [
            make_json_safe(item)
            for item in value
        ]

    # dict
    if isinstance(value, dict):

        return {
            str(key): make_json_safe(val)
            for key, val in value.items()
        }

    # datetime
    if isinstance(value, datetime):

        return value.isoformat()

    # Обычные JSON-типы
    if (
        value is None
        or isinstance(
            value,
            (str, int, float, bool)
        )
    ):

        return value

    # Если встретился неизвестный объект —
    # сохраняем его как строку, чтобы анализ
    # не падал при сохранении.
    return str(value)


# ==========================================================
# СОХРАНЕНИЕ
# ==========================================================

# ==========================================================
# СОХРАНЕНИЕ
# ==========================================================

def save_mistakes(mistakes):

    safe_mistakes = make_json_safe(
        mistakes
    )

    # ======================================================
    # СОХРАНЯЕМ ВСЕ ОШИБКИ
    # ======================================================

    with open(
        MISTAKES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            safe_mistakes,
            file,
            ensure_ascii=False,
            indent=4
        )

    # ======================================================
    # ФОРМИРУЕМ ТОЛЬКО ГРУБЫЕ ОШИБКИ
    #
    # loss хранится в centipawns:
    #
    # 50  = 0.50
    # 100 = 1.00
    # 101 = 1.01
    # 200 = 2.00
    #
    # Грубая ошибка:
    # loss > 100
    # ======================================================

    gross_mistakes = []

    for mistake in mistakes:

        try:

            loss = float(
                mistake.get(
                    "loss",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            loss = 0

        if loss > 100:

            gross_mistakes.append(
                mistake
            )

    safe_gross_mistakes = make_json_safe(
        gross_mistakes
    )

    # ======================================================
    # СОХРАНЯЕМ ГРУБЫЕ ОШИБКИ
    # ======================================================

    with open(
        GROSS_MISTAKES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            safe_gross_mistakes,
            file,
            ensure_ascii=False,
            indent=4
        )

    # ======================================================
    # DEBUG
    # ======================================================

    print(
        "=============================================="
    )

    print(
        "Сохранён файл:",
        os.path.abspath(MISTAKES_FILE)
    )

    print(
        "Всего ошибок:",
        len(mistakes)
    )

    print(
        "Создан/обновлён файл:",
        os.path.abspath(GROSS_MISTAKES_FILE)
    )

    print(
        "Грубых ошибок (loss > 100):",
        len(gross_mistakes)
    )

    print(
        "=============================================="
    )

# ==========================================================
# ID ОШИБКИ
# ==========================================================

def mistake_id(mistake):
    """
    Создаём уникальный идентификатор ошибки.
    Используем позицию + лучший ход.
    """

    return (
        mistake.get("fen", ""),
        mistake.get("best_uci", "")
    )


# ==========================================================
# СЕРИАЛИЗАЦИЯ ОДНОЙ ОШИБКИ
# ==========================================================

def serialize_mistake(mistake):
    """
    Подготавливает ошибку для сохранения в JSON.

    Здесь сохраняем все данные, которые нужны
    для последующего отображения объяснения.
    """

    serialized = {

        "move": mistake.get(
            "move"
        ),

        "move_text": mistake.get(
            "move_text"
        ),

        "played_san": mistake.get(
            "played_san"
        ),

        "symbol": mistake.get(
            "symbol"
        ),

        "theme": mistake.get(
            "theme"
        ),

        "best": mistake.get(
            "best"
        ),

        "best_uci": mistake.get(
            "best_uci"
        ),

        "alternatives": mistake.get(
            "alternatives",
            []
        ),

        # ==================================================
        # ПРАКТИЧЕСКИ РАВНОЦЕННЫЕ ЛУЧШИЕ ХОДЫ
        # ==================================================

        "equivalent_best_moves": mistake.get(
            "equivalent_best_moves",
            []
        ),

        "loss": mistake.get(
            "loss"
        ),

        "type": mistake.get(
            "type"
        ),

        "side": mistake.get(
            "side"
        ),

        "user_side": mistake.get(
            "user_side"
        ),

        "fen": mistake.get(
            "fen"
        ),

        "before_score": mistake.get(
            "before_score"
        ),

        "after_score": mistake.get(
            "after_score"
        ),

        "explanation": mistake.get(
            "explanation"
        ),

        # ==================================================
        # ТАКТИЧЕСКИЕ ДАННЫЕ
        # ==================================================

        "features": mistake.get(
            "features",
            {}
        ),

        "captured_piece": mistake.get(
            "captured_piece"
        ),

        "captured_value": mistake.get(
            "captured_value"
        ),

        "hanging_piece": mistake.get(
            "hanging_piece"
        ),

        "hanging_square": mistake.get(
            "hanging_square"
        ),

        "fork_targets": mistake.get(
            "fork_targets"
        ),

        # ==================================================
        # АТАКА СЛОНА
        # ==================================================

        "bishop_attack_reason": mistake.get(
            "bishop_attack_reason"
        ),

        # ==================================================
        # УГРОЗА ПЕШКОЙ
        # ==================================================

        "pawn_threat_explanation": mistake.get(
            "pawn_threat_explanation"
        ),

        "pawn_attack_piece": mistake.get(
            "pawn_attack_piece"
        ),

        "pawn_attack_square": mistake.get(
            "pawn_attack_square"
        ),

        "pawn_attacker_square": mistake.get(
            "pawn_attacker_square"
        ),

        "pawn_king_attack": mistake.get(
            "pawn_king_attack",
            False
        ),

        # ==================================================
        # ЖЕРТВА КОНЯ
        # ==================================================

        "knight_sacrifice_attack": mistake.get(
            "knight_sacrifice_attack",
            False
        ),

        "knight_sacrifice": mistake.get(
            "knight_sacrifice",
            False
        ),

        "knight_sacrifice_explanation": mistake.get(
            "knight_sacrifice_explanation"
        ),

        # ==================================================
        # АТАКА КОРОЛЯ
        # ==================================================

        "pawn_king_attack_explanation": mistake.get(
            "pawn_king_attack_explanation"
        ),

        # ==================================================
        # ДРУГИЕ ДАННЫЕ
        # ==================================================

        "best_piece": mistake.get(
            "best_piece"
        ),

        "best_square": mistake.get(
            "best_square"
        ),

        "target_piece": mistake.get(
            "target_piece"
        ),

        "target_square": mistake.get(
            "target_square"
        ),

        "move_reasons": mistake.get(
            "move_reasons",
            []
        ),

        "hidden_until": mistake.get(
            "hidden_until"
        )
    }

    # На всякий случай полностью очищаем
    # всё от chess.Move / Board / set и т.д.
    return make_json_safe(
        serialized
    )


# ==========================================================
# ОТЛОЖИТЬ ОШИБКУ
# ==========================================================

def postpone_mistake(
    mistake,
    days
):

    mistakes = load_mistakes()

    target_id = mistake_id(
        mistake
    )

    until = (
        datetime.now()
        + timedelta(days=days)
    )

    for item in mistakes:

        if mistake_id(item) == target_id:

            item["hidden_until"] = (
                until.isoformat()
            )

            break

    save_mistakes(
        mistakes
    )


# ==========================================================
# УДАЛИТЬ ОШИБКУ
# ==========================================================

def delete_mistake(mistake):

    mistakes = load_mistakes()

    target_id = mistake_id(
        mistake
    )

    mistakes = [
        item
        for item in mistakes
        if mistake_id(item) != target_id
    ]

    save_mistakes(
        mistakes
    )


# ==========================================================
# ПРОВЕРКА СКРЫТИЯ
# ==========================================================

def is_mistake_hidden(mistake):

    hidden_until = mistake.get(
        "hidden_until"
    )

    if not hidden_until:
        return False

    try:

        until = datetime.fromisoformat(
            hidden_until
        )

    except ValueError:

        return False

    return datetime.now() < until


# ==========================================================
# ВИДИМЫЕ ОШИБКИ
# ==========================================================

def get_visible_mistakes(mistakes):

    return [
        mistake
        for mistake in mistakes
        if not is_mistake_hidden(mistake)
    ]

# ==========================================================
# СОХРАНЕНИЕ НОВЫХ ОШИБОК
# ==========================================================

def save_new_mistakes(new_mistakes):
    """
    Добавляет новые ошибки к уже сохранённым.

    analysis.json:
        сохраняет ВСЕ ошибки.

    gross_mistakes.json:
        сохраняет только грубые ошибки,
        где потеря материала/оценки больше 1 пешки.

    В нашей системе loss хранится в сотых долях пешки:

        50  = 0.50
        100 = 1.00
        101 = 1.01
        200 = 2.00

    Поэтому грубая ошибка:
        loss > 100
    """

    mistakes = load_mistakes()

    existing_ids = {
        mistake_id(item): index
        for index, item in enumerate(mistakes)
    }

    for mistake in new_mistakes:

        serialized = serialize_mistake(
            mistake
        )

        current_id = mistake_id(
            serialized
        )

        # ==================================================
        # НОВАЯ ОШИБКА
        # ==================================================

        if current_id not in existing_ids:

            mistakes.append(
                serialized
            )

            existing_ids[current_id] = (
                len(mistakes) - 1
            )

        # ==================================================
        # ОШИБКА УЖЕ ЕСТЬ —
        # ОБНОВЛЯЕМ ЕЁ
        # ==================================================

        else:

            index = existing_ids[
                current_id
            ]

            old_hidden_until = mistakes[index].get(
                "hidden_until"
            )

            mistakes[index] = serialized

            # Не теряем состояние "отложено"
            if old_hidden_until:

                mistakes[index][
                    "hidden_until"
                ] = old_hidden_until

    # ======================================================
    # СОХРАНЯЕМ ВСЕ ОШИБКИ
    # ======================================================

    save_mistakes(
        mistakes
    )