
import chess


# ==========================================================
# НАЗВАНИЯ ФИГУР
# ==========================================================

PIECE_NAMES = {
    chess.PAWN: "пешку",
    chess.KNIGHT: "коня",
    chess.BISHOP: "слона",
    chess.ROOK: "ладью",
    chess.QUEEN: "ферзя",
    chess.KING: "короля",
}


# ==========================================================
# ПРОВЕРКА: ЕСТЬ ЛИ У СТОРОНЫ СДВОЕННЫЕ ПЕШКИ
# НА ОДНОЙ ВЕРТИКАЛИ
# ==========================================================

def get_doubled_pawns(board, color):
    """
    Возвращает список вертикалей, на которых у color
    находятся две или более пешки.

    Например:
        e4 + e6 -> [4]

    где 4 = вертикаль e.
    """

    files = {}

    for square, piece in board.piece_map().items():

        if piece.color != color:
            continue

        if piece.piece_type != chess.PAWN:
            continue

        file_index = chess.square_file(square)

        files.setdefault(
            file_index,
            []
        ).append(square)

    result = []

    for file_index, squares in files.items():

        if len(squares) >= 2:

            result.append(
                {
                    "file": file_index,
                    "squares": sorted(
                        squares,
                        key=chess.square_rank
                    ),
                }
            )

    return result


# ==========================================================
# СРАВНЕНИЕ ПЕШЕЧНОЙ СТРУКТУРЫ
# ==========================================================

def find_new_doubled_pawns(
    board_before,
    board_after,
    color
):
    """
    Находит новые сдвоенные пешки, которые появились
    после хода.

    Возвращает информацию только о тех вертикалях,
    где до хода не было сдвоенных пешек, а после
    хода они появились.
    """

    before = {
        item["file"]
        for item in get_doubled_pawns(
            board_before,
            color
        )
    }

    after = {
        item["file"]
        for item in get_doubled_pawns(
            board_after,
            color
        )
    }

    new_files = after - before

    if not new_files:
        return []

    result = []

    for file_index in sorted(new_files):

        squares = []

        for square, piece in board_after.piece_map().items():

            if (
                piece.color == color
                and piece.piece_type == chess.PAWN
                and chess.square_file(square)
                == file_index
            ):

                squares.append(square)

        result.append(
            {
                "file": file_index,
                "squares": sorted(
                    squares,
                    key=chess.square_rank
                ),
            }
        )

    return result


# ==========================================================
# ОСНОВНОЙ ДЕТЕКТОР
#
# Ищет ситуацию:
#
# ЛУЧШИЙ ХОД
#      ↓
# ВЗЯТИЕ ФИГУРЫ
#      ↓
# СОПЕРНИК МОЖЕТ ВЗЯТЬ ПЕШКОЙ
#      ↓
# ПОЯВЛЯЮТСЯ СДВОЕННЫЕ ПЕШКИ
#
# Пример:
#
# 15.Rfe1? B...
#
# вместо:
#
# 15.Bxe4!
#
# dxe4
#
# и у чёрных:
#
# e6 + e4
#
# ==========================================================

def detect_pawn_structure_damage(
    position_before,
    best_move
):

    if (
        not position_before
        or not best_move
    ):
        return None

    try:

        if best_move not in position_before.legal_moves:
            return None

    except Exception:

        return None

    try:

        moving_piece = (
            position_before.piece_at(
                best_move.from_square
            )
        )

        if not moving_piece:
            return None

        # --------------------------------------------------
        # Лучший ход должен быть взятием.
        # --------------------------------------------------

        captured_piece = (
            position_before.piece_at(
                best_move.to_square
            )
        )

        if not captured_piece:
            return None

        # Не считаем взятие пешки основой такой идеи.
        if captured_piece.piece_type == chess.PAWN:
            return None

        # --------------------------------------------------
        # Делаем лучший ход.
        # --------------------------------------------------

        board_after_best = (
            position_before.copy()
        )

        board_after_best.push(
            best_move
        )

        # Теперь ход соперника.
        opponent_color = board_after_best.turn

        # --------------------------------------------------
        # Ищем пешечные взятия фигуры,
        # которую только что поставили на best_move.to_square.
        # --------------------------------------------------

        candidate_recaptures = []

        target_square = best_move.to_square

        for reply in board_after_best.legal_moves:

            if reply.to_square != target_square:
                continue

            reply_piece = (
                board_after_best.piece_at(
                    reply.from_square
                )
            )

            if not reply_piece:
                continue

            if reply_piece.color != opponent_color:
                continue

            if reply_piece.piece_type != chess.PAWN:
                continue

            # --------------------------------------------------
            # Проверяем позицию после пешечного взятия.
            # --------------------------------------------------

            board_after_reply = (
                board_after_best.copy()
            )

            try:

                reply_san = (
                    board_after_best.san(reply)
                )

            except Exception:

                reply_san = ""

            board_after_reply.push(
                reply
            )

            # --------------------------------------------------
            # Смотрим, появились ли новые сдвоенные пешки
            # у соперника.
            # --------------------------------------------------

            new_doubled = (
                find_new_doubled_pawns(
                    position_before,
                    board_after_reply,
                    opponent_color
                )
            )

            if not new_doubled:
                continue

            candidate_recaptures.append(
                {
                    "reply": reply,
                    "reply_san": reply_san,
                    "board_after_reply": board_after_reply,
                    "new_doubled": new_doubled,
                    "captured_piece": captured_piece,
                    "moving_piece": moving_piece,
                }
            )

        if not candidate_recaptures:
            return None

        # --------------------------------------------------
        # Выбираем первый подходящий вариант.
        # --------------------------------------------------

        selected = candidate_recaptures[0]

        new_doubled = selected.get(
            "new_doubled"
        ) or []

        if not new_doubled:
            return None

        doubled_info = new_doubled[0]

        file_index = doubled_info.get(
            "file"
        )

        squares = doubled_info.get(
            "squares"
        ) or []

        file_name = (
            chr(
                ord("a") + file_index
            )
            if file_index is not None
            else ""
        )

        square_names = [
            chess.square_name(square)
            for square in squares
        ]

        return {
            "best_move": best_move,
            "captured_piece": captured_piece,
            "captured_piece_name": PIECE_NAMES.get(
                captured_piece.piece_type,
                "фигуру"
            ),
            "reply": selected.get(
                "reply"
            ),
            "reply_san": selected.get(
                "reply_san"
            ),
            "doubled_file": file_name,
            "doubled_squares": square_names,
            "moving_piece": moving_piece,
        }

    except Exception as e:

        print(
            "PAWN STRUCTURE DETECTOR ERROR:",
            e
        )

        return None


# ==========================================================
# ТЕКСТ ОБЪЯСНЕНИЯ
# ==========================================================

def get_pawn_structure_text(
    info,
    best
):

    if not info:
        return ""

    reply_san = (
        info.get(
            "reply_san"
        )
        or ""
    )

    file_name = (
        info.get(
            "doubled_file"
        )
        or ""
    )

    if reply_san and file_name:

        return (
            f"После {best} соперник вынужден "
            f"забирать {reply_san}, но в результате "
            f"получает сдвоенные пешки по линии "
            f"{file_name}."
        )

    if reply_san:

        return (
            f"После {best} соперник может ответить "
            f"{reply_san}, получая сдвоенные пешки."
        )

    if file_name:

        return (
            f"Ход {best} позволял ухудшить "
            f"пешечную структуру соперника, "
            f"создав сдвоенные пешки по линии "
            f"{file_name}."
        )

    return (
        f"Ход {best} позволял ухудшить "
        "пешечную структуру соперника, "
        "создав сдвоенные пешки."
    )
