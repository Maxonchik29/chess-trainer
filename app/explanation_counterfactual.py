import chess
from dataclasses import dataclass


@dataclass
class ExplanationContext:
    """
    Единый контекст для проверки причинности ошибки.

    Здесь нет определения самой ошибки.
    Контекст только собирает необходимые позиции
    и данные из mistake.
    """

    board_before: chess.Board

    board_after_played: chess.Board

    board_after_best: chess.Board | None

    played_move: chess.Move

    best_move: chess.Move | None

    played_san: str

    best_san: str

    loss: float

    played_results: list

    best_pv: list


def build_explanation_context(mistake):
    """
    Создаёт единый ExplanationContext из существующего mistake.

    Ничего не меняет в существующей системе.
    """

    board_before = mistake.get("position_before")

    if not isinstance(board_before, chess.Board):
        return None

    played_san = (
        mistake.get("played_san")
        or mistake.get("played")
        or ""
    )

    best_san = (
        mistake.get("best")
        or ""
    )

    played_move = None

    if played_san:
        try:
            played_move = (
                board_before.parse_san(
                    played_san
                )
            )
        except Exception as e:
            print(
                "COUNTERFACTUAL PLAYED MOVE ERROR:",
                repr(e)
            )

    if played_move is None:
        return None

    board_after_played = board_before.copy()

    try:
        board_after_played.push(
            played_move
        )
    except Exception as e:
        print(
            "COUNTERFACTUAL PLAYED PUSH ERROR:",
            repr(e)
        )
        return None

    best_move = None

    if best_san:
        try:
            best_move = (
                board_before.parse_san(
                    best_san
                )
            )
        except Exception as e:
            print(
                "COUNTERFACTUAL BEST MOVE ERROR:",
                repr(e)
            )

    board_after_best = None

    if best_move is not None:

        board_after_best = board_before.copy()

        try:
            board_after_best.push(
                best_move
            )
        except Exception as e:

            print(
                "COUNTERFACTUAL BEST PUSH ERROR:",
                repr(e)
            )

            board_after_best = None

    try:
        loss = float(
            mistake.get("loss", 0)
        )
    except Exception:
        loss = 0.0

    played_results = (
        mistake.get("played_results")
        or []
    )

    best_pv = (
        mistake.get("pv")
        or mistake.get("best_pv")
        or mistake.get("best_line")
        or []
    )

    return ExplanationContext(
        board_before=board_before.copy(),
        board_after_played=board_after_played,
        board_after_best=board_after_best,
        played_move=played_move,
        best_move=best_move,
        played_san=played_san,
        best_san=best_san,
        loss=loss,
        played_results=played_results,
        best_pv=best_pv,
    )

def get_played_pv(ctx):
    """
    Возвращает PV, начинающийся с первого ответа соперника
    после сыгранной ошибки.

    played_results уже содержит позицию ПОСЛЕ сыгранного хода,
    поэтому первый ход PV должен быть ходом соперника.
    """

    if not ctx.played_results:
        return []

    first_result = ctx.played_results[0]

    if not isinstance(first_result, dict):
        return []

    pv = first_result.get("pv") or []

    if not isinstance(pv, (list, tuple)):
        return []

    return list(pv)


def get_best_pv(ctx):
    """
    Возвращает PV лучшего хода.

    В текущем формате mistake["pv"] начинается
    с самого лучшего хода.
    """

    pv = ctx.best_pv

    if not isinstance(pv, (list, tuple)):
        return []

    return list(pv)


def pv_first_move(ctx):
    """
    Возвращает:

        played PV first move
        best PV first move

    в виде UCI.

    Ничего не проверяет по позиции —
    это только чтение данных.
    """

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    played_first = (
        played_pv[0]
        if played_pv
        else None
    )

    best_first = (
        best_pv[0]
        if best_pv
        else None
    )

    return (
        played_first,
        best_first,
    )

# ============================================================
# PV CONSEQUENCE COMPARISON
# ============================================================

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def _pv_move_to_board_move(board, move):
    """
    Преобразует элемент PV в chess.Move.

    PV может содержать:
    - chess.Move
    - UCI-строку
    """
    if isinstance(move, chess.Move):
        return move

    if isinstance(move, str):
        try:
            return chess.Move.from_uci(move)
        except Exception:
            return None

    return None

def normalize_pv_for_board(board, pv):
    """
    Преобразует PV Stockfish в список chess.Move.

    Stockfish может возвращать PV как:
        ['g7c3', 'b2c3', ...]

    а некоторые детекторы ожидают:
        [chess.Move(...), chess.Move(...), ...]

    Поэтому PV преобразуется последовательно на копии доски.
    """

    if not isinstance(board, chess.Board):
        return []

    if not isinstance(pv, (list, tuple)):
        return []

    work_board = board.copy()
    result = []

    for item in pv:

        move = None

        if isinstance(item, chess.Move):
            move = item

        elif isinstance(item, str):
            try:
                move = chess.Move.from_uci(item)
            except Exception:
                move = None

        if move is None:
            break

        if not work_board.is_legal(move):
            break

        result.append(move)
        work_board.push(move)

    return result

def _material_loss_event(
    board_before,
    board_after_move,
    move,
):
    """
    Проверяет, было ли взятие фигуры/пешки данным ходом.

    Возвращает словарь события или None.
    """

    if not isinstance(move, chess.Move):
        return None

    if not board_before.is_legal(move):
        return None

    captured_piece = board_before.piece_at(
        move.to_square
    )

    # En passant
    if (
        captured_piece is None
        and board_before.is_en_passant(move)
    ):
        captured_piece = chess.Piece(
            chess.PAWN,
            not board_before.turn,
        )

    if captured_piece is None:
        return None

    return {
        "type": "capture",
        "captured_piece_type": captured_piece.piece_type,
        "captured_color": captured_piece.color,
        "captured_value": PIECE_VALUES.get(
            captured_piece.piece_type,
            0,
        ),
        "square": chess.square_name(
            move.to_square
        ),
        "move": move,
    }


def analyze_pv_material(
    board_before,
    pv,
):
    """
    Проигрывает PV и собирает последовательность
    материальных событий.

    ВАЖНО:
    Здесь мы пока не решаем, была ли ошибка.
    Мы только фиксируем факты PV.
    """

    if not isinstance(board_before, chess.Board):
        return []

    if not isinstance(pv, (list, tuple)):
        return []

    board = board_before.copy()

    events = []

    for pv_item in pv:

        move = _pv_move_to_board_move(
            board,
            pv_item,
        )

        if move is None:
            break

        if not board.is_legal(move):
            break

        event = _material_loss_event(
            board,
            None,
            move,
        )

        if event is not None:
            event["ply"] = len(events)

            event["san"] = board.san(move)

            event["mover_color"] = board.turn

            events.append(event)

        board.push(move)

    return events


def compare_pv_consequences(ctx):
    """
    Сравнивает материальные последствия сыгранной
    и лучшей PV.

    Played PV:
        начинается с позиции ПОСЛЕ сыгранного хода.

    Best PV:
        начинается с позиции ДО лучшего хода,
        потому что первый элемент PV — сам best move.
    """

    if ctx is None:
        return None

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    if not played_pv:
        return None

    played_events = analyze_pv_material(
        ctx.board_after_played,
        played_pv,
    )

    best_events = []

    if ctx.board_before is not None and best_pv:
        best_events = analyze_pv_material(
            ctx.board_before,
            best_pv,
        )

    return {
        "played": {
            "events": played_events,
        },
        "best": {
            "events": best_events,
        },
    }

# ============================================================
# MATERIAL CONSEQUENCE
# ============================================================

def _board_material(board, color):
    """
    Считает материальную стоимость всех фигур стороны.
    Король не учитывается.
    """
    if not isinstance(board, chess.Board):
        return 0

    total = 0

    for piece_type, value in PIECE_VALUES.items():

        if piece_type == chess.KING:
            continue

        total += (
            len(board.pieces(piece_type, color))
            * value
        )

    return total


def _material_balance(board):
    """
    Материальный баланс:
        белые - чёрные
    """
    return (
        _board_material(board, chess.WHITE)
        - _board_material(board, chess.BLACK)
    )


def _replay_pv(board_before, pv):
    """
    Проигрывает PV от указанной позиции.

    Возвращает:
        {
            "board": конечная позиция,
            "plies": количество реально проигранных ходов
        }

    Если PV обрывается из-за некорректного хода,
    возвращается последняя корректная позиция.
    """

    board = board_before.copy()

    if not isinstance(pv, (list, tuple)):
        return {
            "board": board,
            "plies": 0,
        }

    plies = 0

    for pv_item in pv:

        move = _pv_move_to_board_move(
            board,
            pv_item,
        )

        if move is None:
            break

        if not board.is_legal(move):
            break

        board.push(move)

        plies += 1

    return {
        "board": board,
        "plies": plies,
    }


def _side_material_change(
    board_before,
    board_after,
    color,
):
    """
    Возвращает изменение материала стороны.

    Например:

        было 20
        стало 17

    результат:

        -3
    """

    before = _board_material(
        board_before,
        color,
    )

    after = _board_material(
        board_after,
        color,
    )

    return after - before


def find_material_consequence(ctx):
    """
    Определяет, приводит ли сыгранная PV
    к существенной материальной потере,
    которой нет в PV лучшего хода.

    Это НЕ детектор шахматной причины.

    Функция отвечает только на вопрос:

        "Что произошло с материалом после
         сыгранного хода по сравнению
         с лучшим ходом?"

    Возвращает None, если существенного
    различия не найдено.
    """

    if ctx is None:
        return None

    if not isinstance(
        ctx.board_before,
        chess.Board,
    ):
        return None

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    if not played_pv:
        return None

    # --------------------------------------------------------
    # Сторона, допустившая ошибку
    # --------------------------------------------------------

    our_color = ctx.board_before.turn

    # --------------------------------------------------------
    # PLAYED PV
    #
    # Важно:
    # played PV начинается ПОСЛЕ нашего хода.
    # Поэтому стартовая позиция здесь:
    #
    #     board_after_played
    # --------------------------------------------------------

    played_result = _replay_pv(
        ctx.board_after_played,
        played_pv,
    )

    played_board = played_result["board"]

    # --------------------------------------------------------
    # BEST PV
    #
    # best PV начинается С НАШЕГО ЛУЧШЕГО ХОДА.
    # Поэтому стартовая позиция:
    #
    #     board_before
    # --------------------------------------------------------

    if not best_pv:
        return None

    best_result = _replay_pv(
        ctx.board_before,
        best_pv,
    )

    best_board = best_result["board"]

    # --------------------------------------------------------
    # Материал до обеих линий
    # --------------------------------------------------------

    initial_material = _board_material(
        ctx.board_before,
        our_color,
    )

    played_material = _board_material(
        played_board,
        our_color,
    )

    best_material = _board_material(
        best_board,
        our_color,
    )

    # --------------------------------------------------------
    # Потеря материала относительно
    # исходной позиции
    # --------------------------------------------------------

    played_loss = max(
        0,
        initial_material - played_material,
    )

    best_loss = max(
        0,
        initial_material - best_material,
    )

    # --------------------------------------------------------
    # Дополнительная потеря именно
    # в сыгранной линии
    # --------------------------------------------------------

    additional_loss = (
        played_loss - best_loss
    )

    # --------------------------------------------------------
    # Если разница меньше одной пешки,
    # не считаем это существенной
    # материальной причиной.
    # --------------------------------------------------------

    if additional_loss < 1:
        return None

    # --------------------------------------------------------
    # События взятий для объяснения
    # --------------------------------------------------------

    played_events = analyze_pv_material(
        ctx.board_after_played,
        played_pv,
    )

    best_events = analyze_pv_material(
        ctx.board_before,
        best_pv,
    )

    return {
        "found": True,

        "color": our_color,

        "initial_material": initial_material,

        "played_material": played_material,

        "best_material": best_material,

        "played_loss": played_loss,

        "best_loss": best_loss,

        "additional_loss": additional_loss,

        "played_plies": played_result["plies"],

        "best_plies": best_result["plies"],

        "played_events": played_events,

        "best_events": best_events,

        "played_board": played_board,

        "best_board": best_board,
    }

# ============================================================
# EXACT MATERIAL CONSEQUENCE
# ============================================================

def _find_own_material_captures(board_before, pv, our_color):
    """
    Возвращает только те взятия в PV, где соперник
    забирает наши фигуры/пешки.

    Это именно потеря нашего материала.
    Взятия, которые делаем мы, сюда не попадают.
    """

    if not isinstance(board_before, chess.Board):
        return []

    if not isinstance(pv, (list, tuple)):
        return []

    board = board_before.copy()
    events = []

    for ply_index, pv_item in enumerate(pv):
        move = _pv_move_to_board_move(board, pv_item)

        if move is None:
            break

        if not board.is_legal(move):
            break

        mover_color = board.turn
        captured_piece = board.piece_at(move.to_square)

        # En passant
        if captured_piece is None and board.is_en_passant(move):
            captured_piece = chess.Piece(
                chess.PAWN,
                not board.turn,
            )

        if (
            captured_piece is not None
            and captured_piece.color == our_color
            and mover_color != our_color
        ):
            events.append({
                "ply": ply_index,
                "move": move,
                "san": board.san(move),
                "square": chess.square_name(move.to_square),
                "captured_piece_type": captured_piece.piece_type,
                "captured_piece_name": (
                    chess.piece_name(captured_piece.piece_type)
                ),
                "captured_value": PIECE_VALUES.get(
                    captured_piece.piece_type,
                    0,
                ),
            })

        board.push(move)

    return events


def find_exact_material_consequence(ctx):
    """
    Строго сравнивает потерю НАШЕГО материала
    в сыгранной линии и в лучшей линии.

    Важно:
    - не просто смотрит конечный material balance;
    - учитывает конкретные взятия наших фигур;
    - отделяет реальные дополнительные потери
      от обычных разменов, которые происходят
      и в лучшей линии.
    """

    if ctx is None:
        return None

    if not isinstance(ctx.board_before, chess.Board):
        return None

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    if not played_pv or not best_pv:
        return None

    our_color = ctx.board_before.turn

    # --------------------------------------------------------
    # Реальные потери в сыгранной линии
    # --------------------------------------------------------

    played_events = _find_own_material_captures(
        ctx.board_after_played,
        played_pv,
        our_color,
    )

    # --------------------------------------------------------
    # Потери в лучшей линии
    # --------------------------------------------------------

    best_events = _find_own_material_captures(
        ctx.board_before,
        best_pv,
        our_color,
    )

    played_loss = sum(
        event["captured_value"]
        for event in played_events
    )

    best_loss = sum(
        event["captured_value"]
        for event in best_events
    )

    additional_loss = played_loss - best_loss

    if additional_loss < 1:
        return None

    # --------------------------------------------------------
    # Находим конкретные дополнительные потери.
    #
    # Сначала сопоставляем одинаковые типы материала,
    # который теряется в обеих линиях.
    # Остаток считается специфичным для сыгранной линии.
    # --------------------------------------------------------

    best_counts = {}

    for event in best_events:
        piece_type = event["captured_piece_type"]
        best_counts[piece_type] = (
            best_counts.get(piece_type, 0) + 1
        )

    causal_events = []

    for event in played_events:
        piece_type = event["captured_piece_type"]

        if best_counts.get(piece_type, 0) > 0:
            best_counts[piece_type] -= 1
            continue

        causal_events.append(event)

    causal_loss = sum(
        event["captured_value"]
        for event in causal_events
    )

    # Если типы материала распределились необычно
    # и сопоставление по типу не нашло остаток,
    # всё равно сохраняем факт дополнительной потери.
    if not causal_events and additional_loss > 0:
        causal_events = list(played_events)

        causal_loss = sum(
            event["captured_value"]
            for event in causal_events
        )

    return {
        "found": True,

        "color": our_color,

        "played_loss": played_loss,
        "best_loss": best_loss,
        "additional_loss": additional_loss,

        "causal_loss": causal_loss,

        "played_events": played_events,
        "best_events": best_events,
        "causal_events": causal_events,

        "first_causal_event": (
            causal_events[0]
            if causal_events
            else None
        ),
    }

# ============================================================
# MATERIAL CONSEQUENCE FACT
# ============================================================

def build_material_consequence_fact(ctx, result):
    """
    Преобразует результат find_exact_material_consequence()
    в компактный структурированный факт для explanation engine.

    Эта функция НИЧЕГО не решает за детектор.
    Она только формирует доказательство:
        какой материал потерян,
        каким ходом,
        в какой последовательности,
        и насколько это хуже best PV.
    """

    if ctx is None:
        return None

    if not result:
        return None

    if not result.get("found"):
        return None

    causal_events = result.get("causal_events") or []

    if not causal_events:
        return None

    first_event = causal_events[0]

    # --------------------------------------------------------
    # Все конкретные SAN-взятия в причинной последовательности
    # --------------------------------------------------------

    sequence = []

    for event in causal_events:
        san = event.get("san")

        if san:
            sequence.append(san)

    # --------------------------------------------------------
    # Информация о первом конкретном потерянном материале
    # --------------------------------------------------------

    captured_piece_type = first_event.get(
        "captured_piece_type"
    )

    captured_piece_name = first_event.get(
        "captured_piece_name"
    )

    captured_value = first_event.get(
        "captured_value",
        0,
    )

    capture_san = first_event.get("san")

    capture_square = first_event.get("square")

    # --------------------------------------------------------
    # Общий дополнительный ущерб
    # --------------------------------------------------------

    additional_loss = result.get(
        "additional_loss",
        0,
    )

    causal_loss = result.get(
        "causal_loss",
        0,
    )

    # --------------------------------------------------------
    # Формируем компактный факт
    # --------------------------------------------------------

    return {
        "type": "material_loss",

        "played_move": ctx.played_san,
        "best_move": ctx.best_san,

        "sequence": sequence,

        "first_capture": {
            "san": capture_san,
            "square": capture_square,
            "piece_type": captured_piece_type,
            "piece_name": captured_piece_name,
            "value": captured_value,
        },

        "additional_loss": additional_loss,
        "causal_loss": causal_loss,

        "played_loss": result.get(
            "played_loss",
            0,
        ),

        "best_loss": result.get(
            "best_loss",
            0,
        ),

        "played_pv_plies": result.get(
            "played_plies",
            0,
        ),

        "best_pv_plies": result.get(
            "best_plies",
            0,
        ),

        # Сохраняем исходные события для дальнейшего
        # использования explanation engine.
        "causal_events": causal_events,
        "played_events": result.get(
            "played_events",
            [],
        ),
        "best_events": result.get(
            "best_events",
            [],
        ),
    }

# ============================================================
# DIRECT MATERIAL CONSEQUENCE
# ============================================================

def _get_move_from_event(event):
    if not isinstance(event, dict):
        return None

    move = event.get("move")

    if isinstance(move, chess.Move):
        return move

    return None


def _capture_was_already_possible(
    board_before,
    capture_move,
):
    """
    Проверяет, мог ли тот же самый ход соперника
    существовать ДО нашего сыгранного хода.

    Если мог — сыгранный ход не создал возможность
    этого взятия.
    """

    if not isinstance(board_before, chess.Board):
        return False

    if not isinstance(capture_move, chess.Move):
        return False

    return board_before.is_legal(capture_move)


def find_direct_material_consequence(ctx):
    """
    Ищет прямое материальное последствие сыгранного хода.

    Логика:

        сыгранный ход
            ↓
        появляется новая возможность взятия
            ↓
        соперник использует её в played PV
            ↓
        в best PV такого последствия нет
    """

    if ctx is None:
        return None

    if not isinstance(ctx.board_before, chess.Board):
        return None

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    if not played_pv or not best_pv:
        return None

    our_color = ctx.board_before.turn

    # --------------------------------------------------------
    # Наш материал, который соперник забирает
    # в сыгранной линии.
    # --------------------------------------------------------

    played_events = _find_own_material_captures(
        ctx.board_after_played,
        played_pv,
        our_color,
    )

    if not played_events:
        return None

    # --------------------------------------------------------
    # Ищем взятие, которое стало возможным именно
    # после сыгранного хода.
    # --------------------------------------------------------

    direct_event = None

    for event in played_events:

        capture_move = _get_move_from_event(event)

        if capture_move is None:
            continue

        # Если тот же ход был легален уже ДО нашего
        # хода, значит наш ход его не создал.
        if _capture_was_already_possible(
            ctx.board_before,
            capture_move,
        ):
            continue

        direct_event = event
        break

    if direct_event is None:
        return None

    # --------------------------------------------------------
    # Смотрим события в best PV.
    # --------------------------------------------------------

    best_events = _find_own_material_captures(
        ctx.board_before,
        best_pv,
        our_color,
    )

    captured_type = direct_event.get(
        "captured_piece_type"
    )

    captured_square = direct_event.get(
        "square"
    )

    # Если best PV приводит к тому же самому
    # материальному последствию — оно не специфично
    # для ошибки.
    for event in best_events:

        if (
            event.get("captured_piece_type")
            == captured_type
            and
            event.get("square")
            == captured_square
        ):
            return None

    capture_san = direct_event.get("san")

    if not capture_san:
        return None

    return {
        "found": True,

        "type": "direct_material_loss",

        "played_move": ctx.played_san,
        "best_move": ctx.best_san,

        "event": direct_event,

        "capture_san": capture_san,

        "captured_piece_type": captured_type,

        "captured_piece_name": direct_event.get(
            "captured_piece_name"
        ),

        "captured_value": direct_event.get(
            "captured_value",
            0,
        ),

        "square": captured_square,

        "played_events": played_events,
        "best_events": best_events,
    }

# ============================================================
# MATERIAL SEQUENCE CONSEQUENCE
# ============================================================

def _material_swing_for_our_side(
    board,
    move,
    our_color,
):
    """
    Материальный эффект одного хода
    с точки зрения нашей стороны.

    Если наш ход забирает материал:
        +value

    Если соперник забирает наш материал:
        -value

    Например для белых:

        ...Qxb2+   = -1
        Rxc3       = +3
        ...Qxh1    = -5
    """

    if not isinstance(
        board,
        chess.Board,
    ):
        return 0, None

    if not isinstance(
        move,
        chess.Move,
    ):
        return 0, None

    # --------------------------------------------------------
    # Кто ходит?
    # --------------------------------------------------------

    mover_color = board.turn

    # --------------------------------------------------------
    # Что забираем?
    # --------------------------------------------------------

    captured_piece = (
        board.piece_at(
            move.to_square
        )
    )

    # En passant
    if (
        captured_piece is None
        and board.is_en_passant(move)
    ):
        captured_piece = chess.Piece(
            chess.PAWN,
            not mover_color,
        )

    if captured_piece is None:
        return 0, None

    value = PIECE_VALUES.get(
        captured_piece.piece_type,
        0,
    )

    # --------------------------------------------------------
    # Если ходит наша сторона —
    # мы получаем материал.
    # --------------------------------------------------------

    if mover_color == our_color:
        swing = value

    # --------------------------------------------------------
    # Если ходит соперник —
    # мы теряем материал.
    # --------------------------------------------------------

    else:
        swing = -value

    return swing, captured_piece

def _analyze_material_sequence(
    board_before,
    pv,
    our_color,
):
    """
    Полностью проигрывает PV и записывает
    материальный эффект каждого хода.

    Например:

        ...Bxc3   -3
        bxc3      +3
        ...Qxc3   -1

    """

    if not isinstance(board_before, chess.Board):
        return []

    if not isinstance(pv, (list, tuple)):
        return []

    board = board_before.copy()

    events = []

    for ply_index, pv_item in enumerate(pv):

        move = _pv_move_to_board_move(
            board,
            pv_item,
        )

        if move is None:
            break

        if not board.is_legal(move):
            break

        san = board.san(move)

        swing, captured_piece = (
            _material_swing_for_our_side(
                board,
                move,
                our_color,
            )
        )

        if captured_piece is not None:

            events.append({
                "ply": ply_index,
                "move": move,
                "san": san,

                "mover_color": board.turn,

                "captured_piece_type":
                    captured_piece.piece_type,

                "captured_piece_name":
                    chess.piece_name(
                        captured_piece.piece_type
                    ),

                "captured_value":
                    PIECE_VALUES.get(
                        captured_piece.piece_type,
                        0,
                    ),

                "swing": swing,
            })

        board.push(move)

    return events


def _find_material_sequences(
    board_before,
    pv,
    our_color,
):
    """
    Ищет короткие материальные последовательности.

    В отличие от старой версии:

    - не требует, чтобы вся последовательность состояла
      только из близких по времени взятий;
    - рассматривает окно до 6 полуходов;
    - сохраняет все материальные события внутри окна;
    - начинает последовательность с первого взятия нашего
      материала;
    - не объединяет весь длинный PV в один огромный размен.
    """

    events = _analyze_material_sequence(
        board_before,
        pv,
        our_color,
    )

    if not events:
        return []

    sequences = []

    # Максимальная длина причинной материальной цепочки.
    MAX_PLIES = 12

    for start_index, start_event in enumerate(events):

        # Нас интересует только начало с потерей нашего
        # материала.
        if start_event["swing"] >= 0:
            continue

        sequence_events = [
            start_event
        ]

        total_swing = start_event["swing"]

        last_ply = start_event["ply"]

        # ----------------------------------------------------
        # Добавляем следующие материальные события,
        # пока они находятся в разумном окне.
        # ----------------------------------------------------

        for next_index in range(
            start_index + 1,
            len(events),
        ):

            event = events[next_index]

            gap = event["ply"] - last_ply

            if gap > MAX_PLIES:
                break

            sequence_events.append(event)

            total_swing += event["swing"]

            last_ply = event["ply"]

        # ----------------------------------------------------
        # Нас интересуют только реальные дополнительные потери.
        # ----------------------------------------------------

        if total_swing < 0:

            sequences.append({
                "start_ply":
                    sequence_events[0]["ply"],

                "end_ply":
                    sequence_events[-1]["ply"],

                "swing":
                    total_swing,

                "events":
                    sequence_events,

                "sequence":
                    [
                        event["san"]
                        for event in sequence_events
                    ],
            })

    # --------------------------------------------------------
    # Убираем дубликаты.
    # --------------------------------------------------------

    unique = []

    seen = set()

    for sequence in sequences:

        key = (
            sequence["start_ply"],
            sequence["end_ply"],
            tuple(sequence["sequence"]),
            sequence["swing"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(sequence)

    return unique



def find_material_sequence_consequence(ctx):
    """
    Строгий поиск материального последствия ошибки.

    Ищет материальную последовательность в сыгранной PV,
    которой нет в best PV в эквивалентном виде.

    Главный принцип:

    Материальная потеря в best PV считается эквивалентной
    только тогда, когда совпадает конкретное первое
    материальное событие:

        - тип потерянной фигуры;
        - поле, на котором произошло взятие.

    Простое совпадение общего material swing недостаточно.

    Это важно, потому что одна PV может содержать несколько
    разных материальных эпизодов.

    Например:

        Bxc3 bxc3 Qxc3 Qxa3+
        ...
        Bxe4

    Если best PV тоже содержит более позднюю потерю
    на e4, это НЕ отменяет того, что именно Bxc3
    могло быть первым причинным материальным событием
    ошибки.

    Приоритет:

        1. конкретность события;
        2. отличие от best PV;
        3. самое раннее причинное событие.
    """

    if ctx is None:
        return None

    if not isinstance(
        ctx.board_before,
        chess.Board,
    ):
        return None

    # ========================================================
    # PV
    # ========================================================

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    if not played_pv or not best_pv:
        return None

    our_color = ctx.board_before.turn

    # ========================================================
    # PLAYED PV
    # ========================================================

    played_sequences = _find_material_sequences(
        ctx.board_after_played,
        played_pv,
        our_color,
    )

    if not played_sequences:
        return None

    # ========================================================
    # BEST PV
    # ========================================================

    best_sequences = _find_material_sequences(
        ctx.board_before,
        best_pv,
        our_color,
    )

    print(
        "COUNTERFACTUAL PLAYED PV:",
        played_pv
    )

    print(
        "COUNTERFACTUAL BEST PV:",
        best_pv
    )

    print(
        "COUNTERFACTUAL PLAYED SEQUENCES:",
        played_sequences
    )

    print(
        "COUNTERFACTUAL BEST SEQUENCES:",
        best_sequences
    )

    # ========================================================
    # DEBUG
    # ========================================================

    # ========================================================
    # САМЫЕ РАННИЕ КАНДИДАТЫ — ПЕРВЫМИ
    #
    # Поздняя потеря с большим swing не должна автоматически
    # вытеснять раннее материальное событие.
    # ========================================================

    played_sequences = sorted(
        played_sequences,
        key=lambda item: (
            item.get("start_ply", 999999),
            item.get("swing", 0),
        ),
    )

    # ========================================================
    # ПРОВЕРКА BEST PV
    #
    # Эквивалентность определяется НЕ только swing.
    #
    # Сначала смотрим на первое взятие нашего материала.
    # ========================================================

    valid_candidates = []

    for played_sequence in played_sequences:

        played_swing = played_sequence.get(
            "swing",
            0,
        )

        # ----------------------------------------------------
        # Должна быть реальная потеря материала.
        # ----------------------------------------------------

        if played_swing >= 0:
            continue

        # ====================================================
        # НАХОДИМ ПЕРВОЕ ВЗЯТИЕ НАШЕГО МАТЕРИАЛА
        # СОПЕРНИКОМ
        # ====================================================

        opponent_capture = None

        for event in played_sequence.get(
            "events",
            [],
        ):

            if (
                event.get("mover_color") != our_color
                and event.get("swing", 0) < 0
            ):
                opponent_capture = event
                break

        if opponent_capture is None:
            continue

        # ====================================================
        # ХАРАКТЕРИСТИКИ ПЕРВОГО ПОТЕРЯННОГО ОБЪЕКТА
        # ====================================================

        played_capture_type = (
            opponent_capture.get(
                "captured_piece_type"
            )
        )

        played_capture_square = (
            opponent_capture.get(
                "to_square"
            )
        )

        # ====================================================
        # ИЩЕМ ТОЧНО ТАКОЕ ЖЕ ПЕРВОЕ СОБЫТИЕ В BEST PV
        #
        # Совпадение только swing НЕ считается эквивалентом.
        # ====================================================

        best_has_equivalent_loss = False

        for best_sequence in best_sequences:

            best_events = best_sequence.get(
                "events",
                [],
            )

            best_first_capture = None

            for event in best_events:

                if (
                    event.get("mover_color") != our_color
                    and event.get("swing", 0) < 0
                ):
                    best_first_capture = event
                    break

            if best_first_capture is None:
                continue

            best_capture_type = (
                best_first_capture.get(
                    "captured_piece_type"
                )
            )

            best_capture_square = (
                best_first_capture.get(
                    "to_square"
                )
            )

            # ------------------------------------------------
            # Вот настоящая проверка эквивалентности.
            #
            # Например:
            #
            # Bxc3
            #
            # не эквивалентно:
            #
            # Bxe4
            #
            # даже если обе PV имеют большой отрицательный
            # material swing.
            # ------------------------------------------------

            if (
                best_capture_type
                == played_capture_type
                and
                best_capture_square
                == played_capture_square
            ):

                # --------------------------------------------
                # Дополнительно проверяем swing.
                #
                # Если best действительно допускает такую же
                # потерю или ещё большую, это не объяснение
                # ошибки сыгранного хода.
                # --------------------------------------------

                best_swing = best_sequence.get(
                    "swing",
                    0,
                )

                if best_swing <= played_swing:
                    best_has_equivalent_loss = True
                    break

        if best_has_equivalent_loss:
            continue

        # ====================================================
        # СОХРАНЯЕМ КАНДИДАТ
        # ====================================================

        valid_candidates.append(
            (
                played_sequence,
                opponent_capture,
            )
        )

    # ========================================================
    # НЕТ ПОДХОДЯЩЕГО КАНДИДАТА
    # ========================================================

    if not valid_candidates:
        return None

    # ========================================================
    # ФИНАЛЬНЫЙ ВЫБОР
    #
    # Самое раннее конкретное причинное событие.
    #
    # Если два кандидата начинаются на одном ply,
    # берём более сильную потерю.
    # ========================================================

    valid_candidates.sort(
        key=lambda item: (
            item[0].get(
                "start_ply",
                999999,
            ),
            item[0].get(
                "swing",
                0,
            ),
        )
    )

    played_sequence, opponent_capture = (
        valid_candidates[0]
    )

    played_swing = played_sequence.get(
        "swing",
        0,
    )

    # ========================================================
    # РЕЗУЛЬТАТ
    # ========================================================

    return {
        "found": True,

        "type":
            "material_sequence_loss",

        "played_move":
            ctx.played_san,

        "best_move":
            ctx.best_san,

        "swing":
            played_swing,

        "sequence":
            played_sequence.get(
                "sequence",
                [],
            ),

        "events":
            played_sequence.get(
                "events",
                [],
            ),

        "played_sequences":
            played_sequences,

        "best_sequences":
            best_sequences,

        "opponent_capture":
            opponent_capture,
    }


# ============================================================
# CAUSAL MATERIAL CONSEQUENCE
# ============================================================

def _find_causal_material_sequence(
    board_before,
    pv,
    our_color,
    max_plies=12,
):
    """
    Ищет причинную материальную последовательность.

    Важный принцип:

        берём САМОЕ РАННЕЕ событие потери нашего материала,
        после которого в этой же PV возникает дополнительное
        материальное последствие.

    Поэтому более позднее Qxh1 не должно становиться
    отдельной причиной, если до него уже была цепочка:

        Qxb2+ Rxc3 Qxh1
    """

    if not isinstance(
        board_before,
        chess.Board,
    ):
        return []

    if not isinstance(
        pv,
        (list, tuple),
    ):
        return []

    events = _analyze_material_sequence(
        board_before,
        pv,
        our_color,
    )

    if not events:
        return []

    sequences = []

    # ========================================================
    # Ищем стартовое событие.
    #
    # ВАЖНО:
    # события рассматриваются строго слева направо.
    # Если уже найдена причинная цепочка,
    # более поздние старты не нужны.
    # ========================================================

    for start_index, start_event in enumerate(events):

        # Наш материал должен быть взят соперником.
        if start_event["mover_color"] == our_color:
            continue

        if start_event["swing"] >= 0:
            continue

        sequence_events = [
            start_event
        ]

        cumulative_swing = (
            start_event["swing"]
        )

        last_ply = start_event["ply"]

        recovered = False
        final_negative_position = None

        # ====================================================
        # Идём дальше по материальным событиям.
        # ====================================================

        for next_index in range(
            start_index + 1,
            len(events),
        ):

            event = events[next_index]

            gap = (
                event["ply"]
                - last_ply
            )

            if gap > max_plies:
                break

            sequence_events.append(event)

            cumulative_swing += (
                event["swing"]
            )

            last_ply = event["ply"]

            # ========================================================
            # Если мы уже получили существенную чистую потерю
            # материала, считаем первый тактический эпизод
            # завершённым.
            #
            # Например:
            #
            # Qxb2+  -1
            # Rxc3   -3
            # Qxh1   -5
            #
            # После этого дальнейшие взятия уже могут относиться
            # к следующему эпизоду партии.
            # ========================================================

            if cumulative_swing <= -5:
                break

            # ------------------------------------------------
            # Материал был восстановлен.
            # ------------------------------------------------

            if cumulative_swing >= 0:
                recovered = True

            # ------------------------------------------------
            # После восстановления снова получили минус.
            #
            # Это и есть причинное материальное последствие.
            # ------------------------------------------------

            if (
                recovered
                and cumulative_swing < 0
            ):
                final_negative_position = (
                    len(sequence_events) - 1
                )

                break

        # ====================================================
        # Не было восстановления + новой потери.
        # Это не causal sequence.
        # ====================================================

        if final_negative_position is None:
            continue

        final_events = sequence_events[
            :final_negative_position + 1
        ]

        final_swing = sum(
            event["swing"]
            for event in final_events
        )

        if final_swing >= 0:
            continue

        # ====================================================
        # Нашли первую причинную цепочку.
        #
        # Не продолжаем искать более поздние старты.
        # ====================================================

        sequences.append({
            "start_ply":
                final_events[0]["ply"],

            "end_ply":
                final_events[-1]["ply"],

            "swing":
                final_swing,

            "events":
                final_events,

            "sequence":
                [
                    event["san"]
                    for event in final_events
                ],

            "recovered":
                recovered,
        })

        break

    return sequences

print(
    "=== LOADED _find_first_opponent_material_sequence ===",
    "max_plies default = 6"
)

def _find_first_opponent_material_sequence(
    board_before,
    pv,
    our_color,
    max_plies=6,
):
    """
    Ищет первую причинную материальную цепочку
    в PV соперника.

    Поддерживает:

    1. Одиночное конкретное материальное последствие:

        ...Qxd3

    2. Нарастающую потерю:

        -1 → -3 → -5

    3. Жертву с промежуточным возвратом материала:

        -1 → +3 → -5

    Главное правило:

    Цепочка начинается с первого материального действия
    соперника, которое ухудшает материал нашей стороны.

    ВАЖНО:

    Одного материального события достаточно, если это
    конкретное взятие фигуры стоимостью >= 2.

    Это необходимо для ситуаций вроде:

        Qf4+ Ke2 Qe4+ Kf2 Qxd3

    где между ошибкой и потерей фигуры есть несколько
    промежуточных шахов, но сама материальная потеря
    происходит одним взятием.

    Возвращается только материально отрицательная
    последовательность.
    """

    print(
        "MATERIAL SEQUENCE FUNCTION:",
        "_find_first_opponent_material_sequence",
        "max_plies=",
        max_plies,
    )

    if not isinstance(
        board_before,
        chess.Board,
    ):
        return None

    if not isinstance(
        pv,
        (list, tuple),
    ):
        return None

    board = board_before.copy()

    events = []

    for ply_index, pv_item in enumerate(pv):

        move = _pv_move_to_board_move(
            board,
            pv_item,
        )

        if move is None:
            break

        if not board.is_legal(move):
            break

        san = board.san(move)

        swing, captured_piece = (
            _material_swing_for_our_side(
                board,
                move,
                our_color,
            )
        )

        if captured_piece is not None:

            captured_value = PIECE_VALUES.get(
                captured_piece.piece_type,
                0,
            )

            events.append({
                "ply": ply_index,
                "move": move,
                "san": san,
                "mover_color": board.turn,
                "captured_piece_type":
                    captured_piece.piece_type,
                "captured_piece_name":
                    chess.piece_name(
                        captured_piece.piece_type
                    ),
                "captured_value":
                    captured_value,
                "swing": swing,
                "to_square":
                    move.to_square,
            })

        board.push(move)

        # ----------------------------------------------------
        # Не нужно продолжать анализ после max_plies.
        # ----------------------------------------------------

        if ply_index + 1 >= max_plies:
            break

    if not events:
        return None

    # ========================================================
    # Ищем первое материальное действие СОПЕРНИКА,
    # которое наносит нам материальный ущерб.
    # ========================================================

    first_opponent_index = None

    for index, event in enumerate(events):

        if (
            event["mover_color"] != our_color
            and event["swing"] < 0
        ):
            first_opponent_index = index
            break

    if first_opponent_index is None:
        return None

    first_event = events[
        first_opponent_index
    ]

    first_ply = first_event["ply"]

    sequence_events = [
        first_event
    ]

    cumulative_swing = (
        first_event["swing"]
    )

    last_ply = first_ply

    # ========================================================
    # Если первое материальное действие уже само по себе
    # является крупной потерей фигуры, оно может быть
    # полноценным причинным последствием.
    #
    # Например:
    #
    # Qf4+ Ke2 Qe4+ Kf2 Qxd3
    #
    # Здесь Qxd3 — единственное материальное событие,
    # но соперник забирает фигуру стоимостью 5.
    # ========================================================

    if (
        first_event["captured_value"] >= 2
        and cumulative_swing <= -2
    ):
        return {
            "start_ply":
                first_ply,

            "end_ply":
                first_ply,

            "swing":
                cumulative_swing,

            "events":
                sequence_events,

            "sequence":
                [
                    event["san"]
                    for event in sequence_events
                ],

            "recovered":
                False,
        }

    # ========================================================
    # Продолжаем цепочку для более сложных
    # материальных последовательностей.
    # ========================================================

    for event in events[
        first_opponent_index + 1:
    ]:

        gap = (
            event["ply"]
            - last_ply
        )

        if gap > max_plies:
            break

        sequence_events.append(
            event
        )

        cumulative_swing += (
            event["swing"]
        )

        last_ply = event["ply"]

        # ----------------------------------------------------
        # Пока итог остаётся отрицательным,
        # продолжаем собирать связанные события.
        # ----------------------------------------------------

        if cumulative_swing < 0:
            continue

        # ----------------------------------------------------
        # Временное восстановление материала допустимо.
        #
        # Например:
        #
        # -1 → +3 → -5
        #
        # Поэтому ничего здесь не удаляем.
        # ----------------------------------------------------

        continue

    # ========================================================
    # Итоговая проверка.
    # ========================================================

    if cumulative_swing >= 0:
        return None

    # ========================================================
    # Для цепочки из нескольких событий итоговая потеря
    # должна быть не менее 2 единиц.
    #
    # Одиночная потеря пешки здесь не должна превращаться
    # в causal_material_loss.
    # ========================================================

    if (
        len(sequence_events) > 1
        and cumulative_swing > -2
    ):
        return None

    return {
        "start_ply":
            first_ply,

        "end_ply":
            last_ply,

        "swing":
            cumulative_swing,

        "events":
            sequence_events,

        "sequence":
            [
                event["san"]
                for event in sequence_events
            ],

        "recovered":
            any(
                sum(
                    item["swing"]
                    for item in sequence_events[:index + 1]
                ) >= 0
                for index in range(
                    len(sequence_events)
                )
            ),
    }

def find_causal_material_consequence(ctx):
    """
    Counterfactual-проверка причинного материального последствия.

    Сравнивает:
        1. PV после сыгранного хода;
        2. PV после лучшего хода.

    Ищет первое конкретное материальное последствие
    в сыгранной линии, которого нет в best PV.

    Важный принцип:
        не достаточно просто увидеть потерю материала.
        Потеря должна быть следствием сыгранного хода
        и отсутствовать в эквивалентном виде после best move.

    Дополнительно:
        - потеря < 2 единиц отбрасывается;
        - потеря ровно 2 единицы только пешками отбрасывается;
        - предпочтение отдаётся прямой потере фигуры,
          снятию защиты и другим конкретным последствиям.
    """

    if ctx is None:
        return None

    if not isinstance(
        ctx.board_before,
        chess.Board,
    ):
        return None

    # ========================================================
    # PV
    # ========================================================

    played_pv = get_played_pv(ctx)
    best_pv = get_best_pv(ctx)

    if not played_pv:
        print(
            "COUNTERFACTUAL MATERIAL: "
            "played_pv пустой"
        )
        return None

    if not best_pv:
        print(
            "COUNTERFACTUAL MATERIAL: "
            "best_pv пустой"
        )
        return None

    our_color = ctx.board_before.turn

    print(
        "COUNTERFACTUAL CAUSAL CHECK"
    )

    print(
        "PLAYED PV:",
        played_pv,
    )

    print(
        "BEST PV:",
        best_pv,
    )

    # ========================================================
    # PLAYED
    # ========================================================

    played_sequence = (
        _find_first_opponent_material_sequence(
            ctx.board_after_played,
            played_pv,
            our_color,
            max_plies=6,
        )
    )

    print(
        "CAUSAL PLAYED SEQUENCE:",
        played_sequence,
    )

    if played_sequence is None:
        print(
            "COUNTERFACTUAL MATERIAL: "
            "нет материальной последовательности "
            "в played PV"
        )
        return None

    played_events = (
        played_sequence.get("events") or []
    )

    if not played_events:
        return None

    # ========================================================
    # BEST
    # ========================================================

    best_sequence = (
        _find_first_opponent_material_sequence(
            ctx.board_before,
            best_pv,
            our_color,
            max_plies=6,
        )
    )

    print(
        "CAUSAL BEST SEQUENCE:",
        best_sequence,
    )

    # ========================================================
    # ИТОГОВАЯ ПОТЕРЯ
    # ========================================================

    played_swing = sum(
        event.get("swing", 0)
        for event in played_events
    )

    print(
        "CAUSAL PLAYED SWING:",
        played_swing,
    )

    if played_swing >= 0:
        print(
            "COUNTERFACTUAL MATERIAL: "
            "итоговая потеря отсутствует"
        )
        return None

    # --------------------------------------------------------
    # Слишком маленькая потеря
    # --------------------------------------------------------

    if played_swing > -2:
        print(
            "COUNTERFACTUAL MATERIAL: "
            "потеря меньше 2 единиц"
        )
        return None

    # --------------------------------------------------------
    # Ровно -2:
    # допускаем только если потеряна фигура,
    # а не две пешки.
    # --------------------------------------------------------

    if played_swing == -2:

        lost_non_pawn_piece = any(
            (
                event.get("swing", 0) < 0
                and
                event.get(
                    "captured_piece_type"
                ) != chess.PAWN
            )
            for event in played_events
        )

        if not lost_non_pawn_piece:
            print(
                "COUNTERFACTUAL MATERIAL: "
                "-2 только пешками -> отбрасываем"
            )
            return None

    # ========================================================
    # ПЕРВОЕ ОТРИЦАТЕЛЬНОЕ СОБЫТИЕ СОПЕРНИКА
    # ========================================================

    first_opponent_capture = None

    for event in played_events:

        if (
            event.get("mover_color") != our_color
            and
            event.get("swing", 0) < 0
        ):
            first_opponent_capture = event
            break

    if first_opponent_capture is None:
        print(
            "COUNTERFACTUAL MATERIAL: "
            "нет первого взятия нашего материала"
        )
        return None

    played_capture_type = (
        first_opponent_capture.get(
            "captured_piece_type"
        )
    )

    played_capture_square = (
        first_opponent_capture.get(
            "to_square"
        )
    )

    played_capture_san = (
        first_opponent_capture.get(
            "san"
        )
    )

    print(
        "FIRST PLAYED CAPTURE:",
        played_capture_san,
        "type=",
        played_capture_type,
        "square=",
        played_capture_square,
    )

    # ========================================================
    # COUNTERFACTUAL ПРОВЕРКА BEST PV
    # ========================================================
    #
    # Если best PV приводит к тому же первому
    # материальному последствию:
    #
    #     та же фигура
    #     на том же поле
    #
    # то это не является следствием именно
    # сыгранного хода.
    #
    # ========================================================

    if best_sequence is not None:

        best_events = (
            best_sequence.get("events") or []
        )

        for event in best_events:

            if (
                event.get("mover_color") != our_color
                and
                event.get("swing", 0) < 0
            ):

                best_capture_type = (
                    event.get(
                        "captured_piece_type"
                    )
                )

                best_capture_square = (
                    event.get(
                        "to_square"
                    )
                )

                print(
                    "BEST CAPTURE CHECK:",
                    event.get("san"),
                    "type=",
                    best_capture_type,
                    "square=",
                    best_capture_square,
                )

                if (
                    best_capture_type
                    == played_capture_type
                    and
                    best_capture_square
                    == played_capture_square
                ):
                    print(
                        "COUNTERFACTUAL MATERIAL: "
                        "аналогичная потеря есть в best PV"
                    )
                    return None

                # Нам достаточно проверить первое
                # отрицательное материальное событие.
                break

    # ========================================================
    # ОПРЕДЕЛЯЕМ ТИП ПРИЧИННОГО ПОСЛЕДСТВИЯ
    # ========================================================

    first_move = None

    if played_events:
        first_event = played_events[0]

        first_move = first_event.get(
            "move"
        )

    # --------------------------------------------------------
    # Если первое материальное действие соперника
    # забирает именно фигуру, которую сыгранный ход
    # поставил под удар / оставил без защиты,
    # это наиболее сильный тип.
    # --------------------------------------------------------

    played_piece_square = (
        ctx.played_move.to_square
        if isinstance(
            ctx.played_move,
            chess.Move,
        )
        else None
    )

    if (
        played_piece_square is not None
        and
        played_capture_square
        == played_piece_square
    ):

        reason_type = (
            "direct_capture_of_played_piece"
        )

        strength = 2

    else:

        # ----------------------------------------------------
        # Проверяем снятие защитника.
        #
        # Если после сыгранного хода соперник
        # забирает другую фигуру, это может быть
        # следствием того, что сыгранный ход
        # снял её защиту.
        #
        # Само доказательство снятия защиты
        # оставляем следующим этапом.
        # Здесь только классифицируем
        # материальное последствие.
        # ----------------------------------------------------

        reason_type = (
            "played_move_removed_defender"
        )

        strength = 1

    # ========================================================
    # РЕЗУЛЬТАТ
    # ========================================================

    consequence = {
        "found": True,

        "type": (
            "causal_material_loss"
        ),

        "played_move": (
            ctx.played_san
        ),

        "best_move": (
            ctx.best_san
        ),

        "swing": played_swing,

        "sequence": (
            played_sequence.get(
                "sequence",
                [],
            )
        ),

        "events": played_events,

        "played_sequence": (
            played_sequence
        ),

        "best_sequence": (
            best_sequence
        ),

        "first_capture": (
            first_opponent_capture
        ),

        "first_capture_san": (
            played_capture_san
        ),

        "first_capture_square": (
            played_capture_square
        ),

        "first_capture_piece_type": (
            played_capture_type
        ),

        "reason_type": (
            reason_type
        ),

        "strength": (
            strength
        ),
    }

    print(
        "COUNTERFACTUAL MATERIAL FOUND:",
        consequence,
    )

    return consequence

def check_material_sequence_causal_connection(
    ctx,
    consequence,
):
    """
    Диагностическая проверка причинной связи.

    Проверяем НЕ только первое взятие.

    Для каждого материального события смотрим:

    1. забирается ли сама фигура, сыгравшая ошибочный ход;
    2. появились ли новые атаки после сыгранного хода;
    3. исчезли ли наши защитники;
    4. изменилось ли состояние поля взятия.

    Пока функция диагностическая и НЕ является
    окончательным фильтром.
    """

    if ctx is None:
        return None

    if consequence is None:
        return None

    if not isinstance(
        ctx.board_before,
        chess.Board,
    ):
        return None

    events = consequence.get(
        "events",
        [],
    )

    if not events:
        return None

    board_before = ctx.board_before.copy()
    board_after = ctx.board_after_played.copy()

    played_move = ctx.played_move

    # ========================================================
    # Фигура, которой был сделан ошибочный ход
    # ========================================================

    played_piece_before = (
        board_before.piece_at(
            played_move.from_square
        )
    )

    played_piece_after = (
        board_after.piece_at(
            played_move.to_square
        )
    )

    played_piece_type = (
        played_piece_before.piece_type
        if played_piece_before
        else None
    )

    # ========================================================
    # Анализ каждого материального события
    # ========================================================

    event_debug = []

    any_direct_capture = False
    any_new_attack = False
    any_removed_defender = False

    for event in events:

        move = event.get("move")

        if not isinstance(
            move,
            chess.Move,
        ):
            continue

        square = move.to_square

        # ----------------------------------------------------
        # Какая фигура находится на поле взятия
        # после сыгранного хода?
        # ----------------------------------------------------

        piece_after = board_after.piece_at(
            square
        )

        # ----------------------------------------------------
        # Прямая потеря фигуры, которой был сделан
        # ошибочный ход.
        # ----------------------------------------------------

        direct_capture = (
            square == played_move.to_square
            and
            played_piece_after is not None
            and
            piece_after is not None
            and
            piece_after.piece_type
            == played_piece_type
        )

        if direct_capture:
            any_direct_capture = True

        # ----------------------------------------------------
        # Атаки соперника на поле взятия
        # ДО нашего хода
        # ----------------------------------------------------

        opponent_color = not board_before.turn

        attackers_before = (
            board_before.attackers(
                opponent_color,
                square,
            )
        )

        attackers_after = (
            board_after.attackers(
                opponent_color,
                square,
            )
        )

        new_attackers = (
            attackers_after
            - attackers_before
        )

        if new_attackers:
            any_new_attack = True

        # ----------------------------------------------------
        # Наши защитники поля
        # ДО и ПОСЛЕ хода
        # ----------------------------------------------------

        defenders_before = (
            board_before.attackers(
                board_before.turn,
                square,
            )
        )

        defenders_after = (
            board_after.attackers(
                board_after.turn,
                square,
            )
        )

        removed_defenders = (
            defenders_before
            - defenders_after
        )

        if removed_defenders:
            any_removed_defender = True

        # ----------------------------------------------------
        # Сохраняем подробную диагностику
        # ----------------------------------------------------

        event_debug.append({
            "san": event.get("san"),

            "move":
                move.uci(),

            "square":
                chess.square_name(
                    square
                ),

            "captured_piece":
                event.get(
                    "captured_piece_name"
                ),

            "captured_value":
                event.get(
                    "captured_value"
                ),

            "direct_capture_of_played_piece":
                direct_capture,

            "new_attackers": [
                chess.square_name(s)
                for s in new_attackers
            ],

            "removed_defenders": [
                chess.square_name(s)
                for s in removed_defenders
            ],
        })

    # ========================================================
    # Итоговая диагностика
    # ========================================================

    causal = (
        any_direct_capture
        or
        any_new_attack
        or
        any_removed_defender
    )

    if any_direct_capture:

        reason = (
            "direct_capture_of_played_piece"
        )

    elif any_new_attack:

        reason = (
            "new_opponent_attack"
        )

    elif any_removed_defender:

        reason = (
            "removed_our_defender"
        )

    else:

        reason = (
            "no_direct_connection_detected"
        )

    return {
        "causal":
            causal,

        "reason":
            reason,

        "played_move":
            ctx.played_san,

        "played_piece_type":
            (
                chess.piece_name(
                    played_piece_type
                )
                if played_piece_type is not None
                else None
            ),

        "events":
            event_debug,
    }

def check_direct_capture_of_played_piece(
    ctx,
    consequence,
):
    """
    Строгая проверка:

    Было ли в найденной материальной цепочке
    прямое взятие именно той фигуры, которая
    сделала ошибочный ход.

    Это один из самых надежных признаков
    причинной связи.

    Примеры:

        21.Nb5 Rxb5
        -> TRUE

        22.Nc3 Qxb2+ Rxc3
        -> TRUE

    Здесь важно, что взятие может быть НЕ первым
    материальным событием цепочки.

    Не считаем причинностью:

        15.Bd3 Bxc3
        18.Ne2 Nxd3+
        32.Kf3 Qxd3

    потому что непосредственно сыгранная фигура
    этими взятиями не забирается.
    """

    if ctx is None:
        return False

    if consequence is None:
        return False

    if not isinstance(
        ctx.board_before,
        chess.Board,
    ):
        return False

    played_move = ctx.played_move

    if not isinstance(
        played_move,
        chess.Move,
    ):
        return False

    board_before = ctx.board_before

    played_piece = board_before.piece_at(
        played_move.from_square
    )

    if played_piece is None:
        return False

    played_piece_type = played_piece.piece_type
    played_piece_color = played_piece.color

    events = consequence.get(
        "events",
        [],
    )

    if not events:
        return False

    for event in events:

        move = event.get("move")

        if not isinstance(
            move,
            chess.Move,
        ):
            continue

        # --------------------------------------------------
        # Нас интересует именно поле, куда пришла фигура
        # после ошибочного хода.
        # --------------------------------------------------

        if move.to_square != played_move.to_square:
            continue

        # --------------------------------------------------
        # Восстанавливаем позицию непосредственно перед
        # этим материальным событием.
        #
        # Берем сыгранный ход и затем проигрываем PV
        # до нужного события.
        # --------------------------------------------------

        board = board_before.copy()

        try:
            board.push(played_move)
        except Exception:
            continue

        event_ply = event.get(
            "ply"
        )

        if not isinstance(
            event_ply,
            int,
        ):
            continue

        pv = get_played_pv(ctx)

        if not pv:
            continue

        # event["ply"] начинается с 0 относительно PV,
        # поэтому проигрываем предыдущие ходы.
        valid = True

        for index, pv_item in enumerate(pv):

            if index >= event_ply:
                break

            pv_move = _pv_move_to_board_move(
                board,
                pv_item,
            )

            if pv_move is None:
                valid = False
                break

            if not board.is_legal(
                pv_move
            ):
                valid = False
                break

            board.push(
                pv_move
            )

        if not valid:
            continue

        # --------------------------------------------------
        # Проверяем, какая фигура стоит на поле взятия
        # непосредственно перед event.
        # --------------------------------------------------

        target_piece = board.piece_at(
            move.to_square
        )

        if target_piece is None:
            continue

        # Это должна быть именно наша фигура.
        if target_piece.color != played_piece_color:
            continue

        # И именно тот же тип фигуры.
        if target_piece.piece_type != played_piece_type:
            continue

        # Ход должен действительно быть взятием.
        if board.piece_at(
            move.to_square
        ) is None:
            continue

        if not board.is_capture(move):
            continue

        return True

    return False

def check_played_move_removed_defender(
    ctx,
    consequence,
):
    """
    Строгая проверка причинного снятия защиты.

    Возвращает True только если одновременно выполнено:

    1. сыгравший ход переместил конкретную нашу фигуру;
    2. до хода эта фигура защищала конкретную нашу цель;
    3. после хода эта же фигура больше не защищает цель;
    4. цель существует после сыгранного хода;
    5. цель действительно была взята соперником в played PV;
    6. это не прямое взятие самой сыгравшей фигуры.

    То есть:

        было:
            сыгравшая фигура -> защищает цель

        сыграли ошибочный ход

        стало:
            сыгравшая фигура -> больше не защищает цель

        затем:
            соперник забирает цель
    """

    if ctx is None:
        return False

    if consequence is None:
        return False

    if not isinstance(
        ctx.board_before,
        chess.Board,
    ):
        return False

    played_move = ctx.played_move

    if not isinstance(
        played_move,
        chess.Move,
    ):
        return False

    board_before = ctx.board_before.copy()
    board_after = ctx.board_after_played.copy()

    # ==================================================
    # 1. Определяем сыгравшую фигуру
    # ==================================================

    played_piece_before = board_before.piece_at(
        played_move.from_square
    )

    if played_piece_before is None:
        return False

    played_color = played_piece_before.color

    played_piece_after = board_after.piece_at(
        played_move.to_square
    )

    if played_piece_after is None:
        return False

    if played_piece_after.color != played_color:
        return False

    if played_piece_after.piece_type != played_piece_before.piece_type:
        return False

    # ==================================================
    # 2. Получаем реальные материальные события
    # ==================================================

    events = consequence.get("events") or []

    if not events:
        return False

    pv = get_played_pv(ctx)

    if not pv:
        return False

    # ==================================================
    # 3. Проверяем каждое взятие нашей фигуры
    # ==================================================

    for event in events:

        move = event.get("move")

        if not isinstance(
            move,
            chess.Move,
        ):
            continue

        # Нас интересуют только взятия соперника.
        if event.get("mover_color") == played_color:
            continue

        event_ply = event.get("ply")

        if not isinstance(
            event_ply,
            int,
        ):
            continue

        target_square = move.to_square

        # ==================================================
        # Прямое взятие сыгравшей фигуры здесь не учитываем.
        #
        # Для этого существует:
        # check_direct_capture_of_played_piece()
        # ==================================================

        if target_square == played_move.to_square:
            continue

        # ==================================================
        # 4. На исходной позиции target должен быть нашей
        #    конкретной фигурой/пешкой.
        # ==================================================

        target_before = board_before.piece_at(
            target_square
        )

        if target_before is None:
            continue

        if target_before.color != played_color:
            continue

        # ==================================================
        # 5. Проверяем, что target действительно существует
        #    после ошибочного хода.
        # ==================================================

        target_after_initial = board_after.piece_at(
            target_square
        )

        if target_after_initial is None:
            continue

        if target_after_initial.color != played_color:
            continue

        if target_after_initial.piece_type != target_before.piece_type:
            continue

        # ==================================================
        # 6. ДО ошибочного хода:
        #
        #    сыгравшая фигура должна защищать target.
        # ==================================================

        defenders_before = board_before.attackers(
            played_color,
            target_square,
        )

        if played_move.from_square not in defenders_before:
            continue

        # ==================================================
        # 7. ПОСЛЕ ошибочного хода:
        #
        #    проверяем, что сыгравшая фигура больше НЕ
        #    защищает target.
        #
        #    ВАЖНО:
        #    проверяем именно ту же фигуру,
        #    которая была на from_square.
        # ==================================================

        defenders_after_initial = board_after.attackers(
            played_color,
            target_square,
        )

        if played_move.to_square in defenders_after_initial:
            continue

        # ==================================================
        # 8. Восстанавливаем позицию непосредственно перед
        #    материальным событием.
        #
        #    PV находится относительно позиции ПОСЛЕ
        #    сыгранного нами хода.
        # ==================================================

        event_board = board_after.copy()

        valid = True

        for index, pv_item in enumerate(pv):

            if index >= event_ply:
                break

            pv_move = _pv_move_to_board_move(
                event_board,
                pv_item,
            )

            if pv_move is None:
                valid = False
                break

            if not event_board.is_legal(
                pv_move
            ):
                valid = False
                break

            event_board.push(
                pv_move
            )

        if not valid:
            continue

        # ==================================================
        # 9. Проверяем, что target всё ещё существует
        #    непосредственно перед его взятием.
        # ==================================================

        target_before_capture = event_board.piece_at(
            target_square
        )

        if target_before_capture is None:
            continue

        if target_before_capture.color != played_color:
            continue

        if target_before_capture.piece_type != target_before.piece_type:
            continue

        # ==================================================
        # 10. Сам event должен быть легальным ходом
        #    соперника из этой позиции.
        # ==================================================

        if not event_board.is_legal(move):
            continue

        if event_board.turn == played_color:
            continue

        # ==================================================
        # 11. Это должно быть именно взятие target.
        # ==================================================

        if move.to_square != target_square:
            continue

        if not event_board.is_capture(move):
            continue

        captured_piece = event_board.piece_at(
            move.to_square
        )

        if captured_piece is None:
            continue

        if captured_piece.color != played_color:
            continue

        if captured_piece.piece_type != target_before.piece_type:
            continue

        # ==================================================
        # 12. Финальная проверка причинной связи.
        #
        # До хода:
        #
        #     played_piece -> target
        #
        # После хода:
        #
        #     played_piece больше НЕ защищает target
        #
        # И затем:
        #
        #     opponent -> target
        #
        # Это именно тот случай, который нам нужен.
        # ==================================================

        print(
            "CAUSAL DEFENDER REMOVAL FOUND:",
            "played=",
            ctx.played_san,
            "played_piece=",
            chess.piece_name(
                played_piece_before.piece_type
            ),
            "target=",
            chess.piece_name(
                target_before.piece_type
            ),
            "target_square=",
            chess.square_name(
                target_square
            ),
            "capture=",
            event_board.san(move),
        )

        return True

    return False

def debug_played_move_removed_defender(
    ctx,
    consequence,
):
    if ctx is None or consequence is None:
        return

    board_before = ctx.board_before
    board_after = ctx.board_after_played
    played_move = ctx.played_move

    played_piece = board_before.piece_at(
        played_move.from_square
    )

    if played_piece is None:
        return

    print()
    print("========================================")
    print("DEBUG REMOVED DEFENDER")
    print("PLAYED:", ctx.played_san)
    print("========================================")

    print(
        "PLAYED PIECE:",
        chess.piece_name(
            played_piece.piece_type
        ),
        chess.square_name(
            played_move.from_square
        ),
        "->",
        chess.square_name(
            played_move.to_square
        ),
    )

    events = consequence.get(
        "events",
        [],
    )

    pv = get_played_pv(ctx)

    for event in events:

        move = event.get("move")

        if not isinstance(
            move,
            chess.Move,
        ):
            continue

        if event.get("mover_color") == played_piece.color:
            continue

        target_square = move.to_square

        before_piece = board_before.piece_at(
            target_square
        )

        if before_piece is None:
            continue

        if before_piece.color != played_piece.color:
            continue

        defenders_before = board_before.attackers(
            played_piece.color,
            target_square,
        )

        defenders_after = board_after.attackers(
            played_piece.color,
            target_square,
        )

        print()
        print(
            "EVENT:",
            event.get("san"),
        )

        print(
            "TARGET:",
            chess.square_name(
                target_square
            ),
            chess.piece_name(
                before_piece.piece_type
            ),
        )

        print(
            "DEFENDERS BEFORE:",
            [
                chess.square_name(s)
                for s in defenders_before
            ],
        )

        print(
            "DEFENDERS AFTER:",
            [
                chess.square_name(s)
                for s in defenders_after
            ],
        )

        print(
            "PLAYED FROM IN BEFORE:",
            played_move.from_square
            in defenders_before,
        )

        print(
            "PLAYED TO IN AFTER:",
            played_move.to_square
            in defenders_after,
        )
def get_causal_material_reason(
    ctx,
    consequence,
):
    if ctx is None:
        return None

    if consequence is None:
        return None

    reason_type = consequence.get("reason_type")

    if reason_type == "direct_capture_of_played_piece":
        return {
            "type": "direct_capture_of_played_piece",
            "strength": 2,
        }

    if reason_type == "played_move_removed_defender":
        return {
            "type": "played_move_removed_defender",
            "strength": 1,
        }

    return None