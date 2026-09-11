import chess

from app.explanation_utils import (
    piece_value,
    piece_name,
    get_captured_piece,
    make_position_after,
    get_best_move,
    PIECE_VALUES,
    CENTER_SQUARES,
    PIECE_NAMES,
)

from app.pawn_structure_detector import (
    detect_pawn_structure_damage,
    get_pawn_structure_text,
)


def detect_equal_trade_info(
    board,
    best_move
):

    if not board or not best_move:
        return None

    try:

        moving_piece = board.piece_at(
            best_move.from_square
        )

        if not moving_piece:
            return None

        if moving_piece.piece_type in (
            chess.PAWN,
            chess.KING,
        ):
            return None

        board_after = make_position_after(
            board,
            best_move
        )

        if not board_after:
            return None

        our_color = moving_piece.color
        opponent_color = not our_color
        our_square = best_move.to_square

        # ==================================================
        # 1. ПРЯМОЙ РАЗМЕН
        # ==================================================

        targets = get_equal_targets_after_move(
            board_after,
            our_square,
            our_color
        )

        if targets:

            for target_square, target_piece in targets:

                if can_opponent_capture_piece(
                    board_after,
                    our_square,
                    opponent_color
                ):

                    return {
                        "moving_piece": moving_piece,
                        "target_piece": target_piece,
                        "moving_square": our_square,
                        "target_square": target_square,
                        "direct": True,
                    }

            for target_square, target_piece in targets:

                return {
                    "moving_piece": moving_piece,
                    "target_piece": target_piece,
                    "moving_square": our_square,
                    "target_square": target_square,
                    "direct": False,
                }

        # ==================================================
        # 2. РАЗМЕН ЧЕРЕЗ ОСВОБОЖДЕНИЕ ЛИНИИ
        # ==================================================

        for attacker_square, attacker_piece in (
            board_after.piece_map().items()
        ):

            if attacker_piece.color != our_color:
                continue

            if attacker_piece.piece_type not in (
                chess.KNIGHT,
                chess.BISHOP,
                chess.ROOK,
            ):
                continue

            if attacker_square == our_square:
                continue

            attacks_after = board_after.attacks(
                attacker_square
            )

            for target_square in attacks_after:

                target_piece = board_after.piece_at(
                    target_square
                )

                if not target_piece:
                    continue

                if target_piece.color != opponent_color:
                    continue

                if target_piece.piece_type not in (
                    chess.KNIGHT,
                    chess.BISHOP,
                    chess.ROOK,
                ):
                    continue

                attacks_before = board.attacks(
                    attacker_square
                )

                if target_square in attacks_before:
                    continue

                if not can_opponent_capture_piece(
                    board_after,
                    attacker_square,
                    opponent_color
                ):
                    continue

                return {
                    "moving_piece": attacker_piece,
                    "target_piece": target_piece,
                    "moving_square": attacker_square,
                    "target_square": target_square,
                    "trigger_piece": moving_piece,
                    "trigger_square": our_square,
                    "direct": False,
                    "opened_line": True,
                }

        return None

    except Exception as e:

        print(
            "Ошибка detect_equal_trade_info:",
            e
        )

        return None

def get_equal_targets_after_move(
    board_after,
    our_square,
    our_color
):

    if not board_after:
        return []

    try:

        opponent_color = not our_color

        moving_piece = board_after.piece_at(
            our_square
        )

        if not moving_piece:
            return []

        moving_value = piece_value(
            moving_piece
        )

        result = []

        for target_square in board_after.attacks(
            our_square
        ):

            target_piece = board_after.piece_at(
                target_square
            )

            if not target_piece:
                continue

            if target_piece.color != opponent_color:
                continue

            if target_piece.piece_type in (
                chess.PAWN,
                chess.KING,
            ):
                continue

            target_value = piece_value(
                target_piece
            )

            if abs(
                moving_value - target_value
            ) > 1:

                continue

            result.append(
                (
                    target_square,
                    target_piece
                )
            )

        return result

    except Exception:

        return []

def can_opponent_capture_piece(
    board,
    square,
    opponent_color
):

    if not board:
        return False

    try:

        attackers = board.attackers(
            opponent_color,
            square
        )

        for attacker_square in attackers:

            attacker_piece = board.piece_at(
                attacker_square
            )

            if not attacker_piece:
                continue

            if attacker_piece.piece_type == chess.KING:
                continue

            capture_move = chess.Move(
                attacker_square,
                square
            )

            if capture_move in board.legal_moves:
                return True

        return False

    except Exception:

        return False

def detect_material_gain(
    board,
    move
):

    captured = get_captured_piece(
        board,
        move
    )

    if not captured:
        return None

    return piece_name(
        captured
    )

def detect_castling(
    board,
    best_move
):

    if not board or not best_move:
        return False

    try:

        return board.is_castling(
            best_move
        )

    except Exception:

        return False

def detect_mate(
    board,
    move
):

    after = make_position_after(
        board,
        move
    )

    if not after:
        return False

    return after.is_checkmate()


# ==========================================================
# ШАХ
# ==========================================================

def detect_check(
    board,
    move
):

    after = make_position_after(
        board,
        move
    )

    if not after:
        return False

    return after.is_check()


# ==========================================================
# СВЯЗКА С ПОСЛЕДУЮЩИМ ВЫИГРЫШЕМ МАТЕРИАЛА
#
# ВАЖНО:
#
# Этот детектор работает ТОЛЬКО в позиции ПОСЛЕ
# сыгранного пользователем хода.
#
# Ищем последовательность:
#
#     наш ход
#          ↓
#     соперник создаёт связку
#          ↓
#     связанная фигура не может уйти
#          ↓
#     соперник может забрать эту фигуру
#
# Поддерживаются:
#
# 1. абсолютная связка с королём;
# 2. относительная связка с более ценной фигурой.
#
# Главное условие:
#
# связка должна быть НОВОЙ после сыгранного хода.
#
# Поэтому обычные старые связки в позиции
# этот детектор не трогают.
# ==========================================================

def find_pawn_attack_threat(
    board_before,
    board_after,
    our_color
):

    if not board_before or not board_after:
        return None

    try:

        opponent_color = not our_color

        candidates = []

        # ==================================================
        # НАШИ ФИГУРЫ
        # ==================================================

        our_pieces = []

        for square, piece in board_after.piece_map().items():

            if piece.color != our_color:
                continue

            if piece.piece_type in (
                chess.KING,
                chess.PAWN,
            ):
                continue

            our_pieces.append(
                (
                    square,
                    piece
                )
            )

        # ==================================================
        # ИЩЕМ ПЕШЕЧНЫЕ ХОДЫ СОПЕРНИКА
        # ==================================================

        for opponent_move in board_after.legal_moves:

            pawn = board_after.piece_at(
                opponent_move.from_square
            )

            if not pawn:
                continue

            if pawn.color != opponent_color:
                continue

            if pawn.piece_type != chess.PAWN:
                continue

            # ==================================================
            # ПОСЛЕ ЭТОГО ХОДА
            # ПЕШКА ДОЛЖНА АТАКОВАТЬ НАШУ ФИГУРУ
            # ==================================================

            test_board = board_after.copy()

            try:

                test_board.push(
                    opponent_move
                )

            except Exception:

                continue

            attacker_square = (
                opponent_move.to_square
            )

            for target_square, target_piece in our_pieces:

                current_piece = (
                    test_board.piece_at(
                        target_square
                    )
                )

                if not current_piece:
                    continue

                if current_piece.color != our_color:
                    continue

                if current_piece.piece_type in (
                    chess.KING,
                    chess.PAWN,
                ):
                    continue

                # ==================================================
                # ПЕШКА ДЕЙСТВИТЕЛЬНО АТАКУЕТ ФИГУРУ?
                # ==================================================

                attackers = test_board.attackers(
                    opponent_color,
                    target_square
                )

                if attacker_square not in attackers:
                    continue

                # ==================================================
                # НЕ БЫЛА ЛИ ЭТА ПЕШЕЧНАЯ АТАКА УЖЕ ВОЗМОЖНА?
                # ==================================================

                before_target_piece = (
                    board_before.piece_at(
                        target_square
                    )
                )

                if (
                    before_target_piece
                    and before_target_piece.color
                    == our_color
                    and before_target_piece.piece_type
                    == target_piece.piece_type
                ):

                    before_attackers = (
                        board_before.attackers(
                            opponent_color,
                            target_square
                        )
                    )

                    # Пешка уже атаковала эту фигуру
                    # до нашего хода.
                    if (
                        opponent_move.from_square
                        in before_attackers
                    ):

                        before_attacker_piece = (
                            board_before.piece_at(
                                opponent_move.from_square
                            )
                        )

                        if (
                            before_attacker_piece
                            and before_attacker_piece.piece_type
                            == chess.PAWN
                        ):

                            continue

                # ==================================================
                # ТЕПЕРЬ ПРОВЕРЯЕМ:
                #
                # МОЖЕТ ЛИ ПЕШКА ПОСЛЕ СВОЕГО ХОДА
                # РЕАЛЬНО ВЫИГРАТЬ ФИГУРУ?
                # ==================================================

                pawn_can_capture = False

                for enemy_capture in (
                    test_board.legal_moves
                ):

                    if (
                        enemy_capture.from_square
                        != attacker_square
                    ):
                        continue

                    if (
                        enemy_capture.to_square
                        != target_square
                    ):
                        continue

                    if not test_board.is_capture(
                        enemy_capture
                    ):
                        continue

                    pawn_can_capture = True
                    break

                if not pawn_can_capture:
                    continue

                # ==================================================
                # ПРОВЕРЯЕМ, МОЖЕМ ЛИ МЫ ПОСЛЕ ВЗЯТИЯ
                # НОРМАЛЬНО ЗАБРАТЬ ПЕШКУ.
                #
                # Если можем — это не полноценная потеря фигуры.
                # ==================================================

                capture_board = test_board.copy()

                try:

                    capture_board.push(
                        enemy_capture
                    )

                except Exception:

                    continue

                pawn_after_capture_square = (
                    enemy_capture.to_square
                )

                recapture_found = False

                for our_response in (
                    capture_board.legal_moves
                ):

                    if (
                        our_response.to_square
                        != pawn_after_capture_square
                    ):
                        continue

                    captured_piece = (
                        capture_board.piece_at(
                            our_response.to_square
                        )
                    )

                    if not captured_piece:
                        continue

                    if (
                        captured_piece.color
                        == our_color
                    ):
                        continue

                    response_board = (
                        capture_board.copy()
                    )

                    try:

                        response_board.push(
                            our_response
                        )

                    except Exception:

                        continue

                    if response_board.is_check():
                        continue

                    recapture_found = True
                    break

                # ==================================================
                # ЕСЛИ ПЕШКУ МОЖНО БЕСПРОБЛЕМНО ЗАБРАТЬ —
                # НЕ СЧИТАЕМ ЭТО СЕРЬЁЗНОЙ УГРОЗОЙ.
                # ==================================================

                if recapture_found:
                    continue

                # ==================================================
                # КАНДИДАТ ДЕЙСТВИТЕЛЬНО ОПАСЕН
                # ==================================================

                candidates.append(
                    {
                        "piece_name": piece_name(
                            target_piece
                        ),
                        "piece_type": (
                            target_piece.piece_type
                        ),
                        "target_square": (
                            target_square
                        ),
                        "attacker_type": chess.PAWN,
                        "attacker_square": (
                            attacker_square
                        ),
                        "pawn_move": opponent_move,
                    }
                )

        # ==================================================
        # НЕТ РЕАЛЬНОЙ УГРОЗЫ
        # ==================================================

        if not candidates:
            return None

        # ==================================================
        # ПРИОРИТЕТ ПО ЦЕННОСТИ ФИГУРЫ
        # ==================================================

        candidates.sort(
            key=lambda x: PIECE_VALUES.get(
                x.get("piece_type"),
                0
            ),
            reverse=True
        )

        return candidates[0]

    except Exception as e:

        print(
            "Ошибка find_pawn_attack_threat:",
            e
        )

        return None

def find_queen_tempo(
    position_before,
    board_after_played,
    played_move
):
    """
    Проверяет, позволил ли сыгранный ход сопернику
    получить НОВУЮ непосредственную атаку на нашего ферзя.

    Условия:

    1. Ферзь принадлежит нашей стороне.
    2. Ферзь существует до и после нашего хода.
    3. До нашего хода конкретная клетка ферзя
       не атаковалась этой фигурой.
    4. После нашего хода существует легальный ход соперника.
    5. Именно фигура, которая делает этот ход,
       после своего хода непосредственно атакует ферзя.
    6. Ход не является просто открытием линии
       другой фигуре.
    7. Взятие ферзя также считается атакой.
    """

    if (
        position_before is None
        or board_after_played is None
        or played_move is None
    ):
        return None

    try:

        # ==================================================
        # СТОРОНЫ
        # ==================================================

        our_color = position_before.turn
        opponent_color = not our_color

        # ==================================================
        # ФЕРЗИ ДО ХОДА
        # ==================================================

        queen_before = set(
            position_before.pieces(
                chess.QUEEN,
                our_color
            )
        )

        if not queen_before:
            return None

        # ==================================================
        # ФЕРЗИ ПОСЛЕ ХОДА
        # ==================================================

        queen_after = set(
            board_after_played.pieces(
                chess.QUEEN,
                our_color
            )
        )

        if not queen_after:
            return None

        # ==================================================
        # ЕСЛИ ФЕРЗЬ БЫЛ ВЗЯТ — НЕТ TEMPO
        # ==================================================

        # Если после сыгранного хода количество ферзей
        # уменьшилось и наш ферзь исчез — проверять нечего.
        #
        # Обычно этого достаточно, но оставляем отдельную
        # проверку для надёжности.

        # ==================================================
        # ПРОВЕРЯЕМ КАЖДОГО НАШЕГО ФЕРЗЯ
        # ==================================================

        candidates = []

        for queen_square in queen_after:

            queen_piece = (
                board_after_played.piece_at(
                    queen_square
                )
            )

            if (
                not queen_piece
                or queen_piece.piece_type != chess.QUEEN
                or queen_piece.color != our_color
            ):
                continue

            # ==================================================
            # КТО АТАКОВАЛ ЭТОГО ФЕРЗЯ ДО НАШЕГО ХОДА?
            # ==================================================

            before_attackers = set(
                position_before.attackers(
                    opponent_color,
                    queen_square
                )
            )

            # ==================================================
            # КТО АТАКУЕТ ФЕРЗЯ ПОСЛЕ НАШЕГО ХОДА?
            # ==================================================

            after_attackers = set(
                board_after_played.attackers(
                    opponent_color,
                    queen_square
                )
            )

            # ==================================================
            # НОВЫЕ АТАКУЮЩИЕ
            # ==================================================

            new_attackers = (
                after_attackers
                - before_attackers
            )

            if not new_attackers:
                continue

            # ==================================================
            # ПРОВЕРЯЕМ РЕАЛЬНЫЕ ХОДЫ СОПЕРНИКА
            # ==================================================

            for opponent_move in board_after_played.legal_moves:

                attacker_square = (
                    opponent_move.from_square
                )

                target_square = (
                    opponent_move.to_square
                )

                # Фигура должна быть одной из тех,
                # кто действительно появился среди
                # новых атакующих.
                if attacker_square not in new_attackers:
                    continue

                attacker_before = (
                    board_after_played.piece_at(
                        attacker_square
                    )
                )

                if not attacker_before:
                    continue

                if (
                    attacker_before.color
                    != opponent_color
                ):
                    continue

                if (
                    attacker_before.piece_type
                    == chess.KING
                ):
                    continue

                # ==================================================
                # ПРОВЕРЯЕМ ХОД
                # ==================================================

                test_board = (
                    board_after_played.copy()
                )

                try:

                    test_board.push(
                        opponent_move
                    )

                except Exception:

                    continue

                # ==================================================
                # ГДЕ ОКАЗАЛАСЬ ФИГУРА ПОСЛЕ ХОДА?
                # ==================================================

                moved_piece = (
                    test_board.piece_at(
                        target_square
                    )
                )

                if not moved_piece:
                    continue

                if (
                    moved_piece.color
                    != opponent_color
                ):
                    continue

                if (
                    moved_piece.piece_type
                    == chess.KING
                ):
                    continue

                # ==================================================
                # КЛЮЧЕВАЯ ПРОВЕРКА
                #
                # ИМЕННО ПЕРЕМЕСТИВШАЯСЯ ФИГУРА
                # должна атаковать ферзя.
                #
                # Это исключает ложные случаи,
                # когда ход просто открывает линию
                # другой фигуре.
                # ==================================================

                moved_piece_attacks_queen = (
                    queen_square
                    in test_board.attacks(
                        target_square
                    )
                )

                if not moved_piece_attacks_queen:
                    continue

                # ==================================================
                # ДОПОЛНИТЕЛЬНО:
                # убеждаемся, что ферзь действительно
                # находится под атакой после хода.
                # ==================================================

                actual_attackers = set(
                    test_board.attackers(
                        opponent_color,
                        queen_square
                    )
                )

                if target_square not in actual_attackers:
                    continue

                # ==================================================
                # SAN
                # ==================================================

                try:

                    move_san = (
                        board_after_played.san(
                            opponent_move
                        )
                    )

                except Exception:

                    move_san = ""

                # ==================================================
                # ДОБАВЛЯЕМ КАНДИДАТА
                # ==================================================

                candidates.append(
                    {
                        "queen_square": queen_square,

                        "attacker_square": (
                            attacker_square
                        ),

                        "attacker_piece": (
                            attacker_before
                        ),

                        "move": opponent_move,

                        "san": move_san,
                    }
                )

        # ==================================================
        # НИ ОДНОЙ РЕАЛЬНОЙ АТАКИ НЕТ
        # ==================================================

        if not candidates:
            return None

        # ==================================================
        # ПРИОРИТЕТ ФИГУР
        # ==================================================

        attacker_priority = {
            chess.PAWN: 1,
            chess.KNIGHT: 2,
            chess.BISHOP: 3,
            chess.ROOK: 4,
            chess.QUEEN: 5,
        }

        candidates.sort(
            key=lambda item:
            attacker_priority.get(
                (
                    item["attacker_piece"].piece_type
                    if item.get("attacker_piece")
                    else None
                ),
                0
            ),
            reverse=True
        )

        selected = candidates[0]

        # ==================================================
        # DEBUG
        # ==================================================

        print(
            "\n========== NEW QUEEN TEMPO =========="
        )

        print(
            "QUEEN:",
            chess.square_name(
                selected["queen_square"]
            )
        )

        print(
            "ATTACKER:",
            (
                selected["attacker_piece"].symbol()
                if selected.get("attacker_piece")
                else None
            )
        )

        print(
            "ATTACKER SQUARE:",
            chess.square_name(
                selected["attacker_square"]
            )
        )

        print(
            "ATTACK MOVE:",
            selected.get("san")
        )

        print(
            "========== END QUEEN TEMPO ==========\n"
        )

        return selected

    except Exception as e:

        print(
            "Ошибка find_queen_tempo:",
            e
        )

        return None

def find_newly_attacked_piece_info(
    board_before,
    board_after,
    our_color
):

    if not board_before or not board_after:
        return None

    try:

        piece_order = [
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ]

        candidates = []

        # ==================================================
        # ИЩЕМ НАШИ ФИГУРЫ, КОТОРЫЕ ПОСЛЕ ХОДА
        # ОКАЗАЛИСЬ ПОД НОВОЙ АТАКОЙ
        # ==================================================

        for piece_type in piece_order:

            before_squares = set(
                board_before.pieces(
                    piece_type,
                    our_color
                )
            )

            after_squares = set(
                board_after.pieces(
                    piece_type,
                    our_color
                )
            )

            for square in after_squares:

                piece = board_after.piece_at(square)

                if not piece:
                    continue

                attackers_after = set(
                    board_after.attackers(
                        not our_color,
                        square
                    )
                )

                if not attackers_after:
                    continue

                # --------------------------------------------------
                # Какие атаки существовали ДО нашего хода?
                # --------------------------------------------------

                if square in before_squares:

                    attackers_before = set(
                        board_before.attackers(
                            not our_color,
                            square
                        )
                    )

                else:

                    # Фигура появилась на новом поле вследствие
                    # нашего хода. До хода атак на этом поле для
                    # неё не существовало.
                    attackers_before = set()

                new_attackers = (
                    attackers_after
                    - attackers_before
                )

                if not new_attackers:
                    continue

                # ==================================================
                # ПРОВЕРЯЕМ НОВЫХ АТАКУЮЩИХ
                # ==================================================

                for attacker_square in new_attackers:

                    attacker_piece = (
                        board_after.piece_at(
                            attacker_square
                        )
                    )

                    if not attacker_piece:
                        continue

                    # ==================================================
                    # ПЕШЕЧНАЯ АТАКА
                    # ==================================================

                    if attacker_piece.piece_type == chess.PAWN:

                        # ------------------------------------------------
                        # ВАЖНО:
                        #
                        # Если наша фигура появилась на этом поле
                        # именно после нашего хода и теперь её может
                        # сразу взять пешка соперника, это может быть
                        # обычным разменом.
                        #
                        # Поэтому сначала проверяем непосредственную
                        # ответную взятие.
                        # ------------------------------------------------

                        immediate_pawn_capture = None

                        for enemy_move in board_after.legal_moves:

                            if (
                                enemy_move.from_square
                                != attacker_square
                            ):
                                continue

                            if (
                                enemy_move.to_square
                                != square
                            ):
                                continue

                            if not board_after.is_capture(
                                enemy_move
                            ):
                                continue

                            moving_piece = (
                                board_after.piece_at(
                                    enemy_move.from_square
                                )
                            )

                            if not moving_piece:
                                continue

                            if (
                                moving_piece.piece_type
                                != chess.PAWN
                            ):
                                continue

                            if (
                                moving_piece.color
                                != (not our_color)
                            ):
                                continue

                            immediate_pawn_capture = enemy_move
                            break

                        # ------------------------------------------------
                        # Если фигура пришла на это поле нашим последним
                        # ходом и пешка может немедленно её взять,
                        # проверяем, не является ли это обычным разменом.
                        #
                        # Например:
                        #
                        # Bxd6 cxd6
                        #
                        # Здесь НЕ нужно писать:
                        #
                        # "Вы позволили сопернику атаковать вашего слона
                        # пешкой."
                        # ------------------------------------------------

                        if (
                            square not in before_squares
                            and immediate_pawn_capture is not None
                        ):

                            test_board = (
                                board_after.copy()
                            )

                            try:

                                test_board.push(
                                    immediate_pawn_capture
                                )

                            except Exception:

                                continue

                            # ------------------------------------------------
                            # После ответной взятия смотрим, может ли
                            # наша сторона вернуть пешку/фигуру.
                            # ------------------------------------------------

                            recapture_found = False

                            capture_square = (
                                immediate_pawn_capture.to_square
                            )

                            for response_move in (
                                test_board.legal_moves
                            ):

                                if (
                                    response_move.to_square
                                    != capture_square
                                ):
                                    continue

                                target_piece = (
                                    test_board.piece_at(
                                        response_move.to_square
                                    )
                                )

                                if not target_piece:
                                    continue

                                if (
                                    target_piece.color
                                    != (not our_color)
                                ):
                                    continue

                                response_board = (
                                    test_board.copy()
                                )

                                try:

                                    response_board.push(
                                        response_move
                                    )

                                except Exception:

                                    continue

                                # Ответ не должен оставлять нашего
                                # короля под шахом.
                                if response_board.is_check():
                                    continue

                                recapture_found = True
                                break

                            # ------------------------------------------------
                            # Если после cxd6 мы можем спокойно забрать
                            # пешку обратно, это обычный размен.
                            # НЕ считаем его атакой фигуры.
                            # ------------------------------------------------

                            if recapture_found:

                                continue

                        # ------------------------------------------------
                        # Теперь проверяем более общий случай:
                        # пешка действительно создаёт материальную угрозу.
                        # ------------------------------------------------

                        pawn_capture = (
                            immediate_pawn_capture
                        )

                        if pawn_capture is None:

                            # Пешка формально атакует фигуру,
                            # но прямо сейчас взять её не может.
                            continue

                        test_board = (
                            board_after.copy()
                        )

                        try:

                            test_board.push(
                                pawn_capture
                            )

                        except Exception:

                            continue

                        pawn_square_after = (
                            pawn_capture.to_square
                        )

                        # ------------------------------------------------
                        # Может ли наша сторона после взятия
                        # вернуть пешку?
                        # ------------------------------------------------

                        recapture_found = False

                        for response_move in (
                            test_board.legal_moves
                        ):

                            if (
                                response_move.to_square
                                != pawn_square_after
                            ):
                                continue

                            target_piece = (
                                test_board.piece_at(
                                    response_move.to_square
                                )
                            )

                            if not target_piece:
                                continue

                            if (
                                target_piece.color
                                != (not our_color)
                            ):
                                continue

                            response_board = (
                                test_board.copy()
                            )

                            try:

                                response_board.push(
                                    response_move
                                )

                            except Exception:

                                continue

                            if response_board.is_check():
                                continue

                            recapture_found = True
                            break

                        # ------------------------------------------------
                        # Если пешку можно спокойно забрать обратно,
                        # это не серьёзная пешечная угроза.
                        # ------------------------------------------------

                        if recapture_found:
                            continue

                    # ==================================================
                    # СОХРАНЯЕМ КАНДИДАТА
                    # ==================================================

                    candidates.append(
                        {
                            "piece_name": piece_name(
                                piece
                            ),
                            "piece_type": piece_type,
                            "square": square,
                            "attacker_piece": attacker_piece,
                            "attacker_type": (
                                attacker_piece.piece_type
                            ),
                            "attacker_square": (
                                attacker_square
                            ),
                        }
                    )

        # ==================================================
        # НИЧЕГО НЕ НАЙДЕНО
        # ==================================================

        if not candidates:
            return None

        # ==================================================
        # ПЕШЕЧНЫЕ АТАКИ — ПРИОРИТЕТНЫЕ
        # НО ТОЛЬКО ПОСЛЕ ВСЕХ ФИЛЬТРОВ
        # ==================================================

        pawn_attacks = [
            candidate
            for candidate in candidates
            if candidate.get(
                "attacker_type"
            ) == chess.PAWN
        ]

        if pawn_attacks:

            pawn_attacks.sort(
                key=lambda x: PIECE_VALUES.get(
                    x.get("piece_type"),
                    0
                ),
                reverse=True
            )

            return pawn_attacks[0]

        # ==================================================
        # ОСТАЛЬНЫЕ АТАКИ
        # ==================================================

        candidates.sort(
            key=lambda x: PIECE_VALUES.get(
                x.get("piece_type"),
                0
            ),
            reverse=True
        )

        return candidates[0]

    except Exception as e:

        print(
            "Ошибка find_newly_attacked_piece_info:",
            e
        )

        return None


def find_newly_attacked_piece(
    board_before,
    board_after,
    our_color
):

    info = find_newly_attacked_piece_info(
        board_before,
        board_after,
        our_color
    )

    if not info:
        return None

    return (
        info.get("piece_name"),
        info.get("square")
    )

def detect_tempo_material_loss(
    board,
    played_move,
    best_move_obj,
    best_move
):

    if (
        not board
        or not played_move
        or not best_move_obj
        or not best_move
    ):
        return None

    try:

        captured_name = detect_material_gain(
            board,
            played_move
        )

        if not captured_name:
            return None

        if detect_material_gain(
            board,
            best_move_obj
        ):
            return None

        best_piece = board.piece_at(
            best_move_obj.from_square
        )

        if not best_piece:
            return None

        after_played = make_position_after(
            board,
            played_move
        )

        if not after_played:
            return None

        opponent_color = after_played.turn
        our_color = not opponent_color

        # --------------------------------------------------
        # СНАЧАЛА ПРОВЕРЯЕМ ПЕШЕЧНУЮ УГРОЗУ
        # --------------------------------------------------

        pawn_threat = (
            find_pawn_attack_threat(
                board,
                after_played,
                our_color
            )
        )

        if pawn_threat:

            attacked_piece_name = (
                pawn_threat.get(
                    "piece_name"
                )
            )

            attacked_square = (
                pawn_threat.get(
                    "target_square"
                )
            )

            square_name = chess.square_name(
                attacked_square
            )

            return (
                f"Вместо взятия {captured_name} "
                f"ходом {played_move} стоило сыграть "
                f"{best_move}. После взятия соперник "
                f"может атаковать вашу "
                f"{attacked_piece_name} пешкой "
                f"на {square_name}, получая темп "
                f"и усиливая свою инициативу."
            )

        # --------------------------------------------------
        # ТЕМП НА ФЕРЗЯ
        # --------------------------------------------------

        queen_tempo = find_queen_tempo(
            board,
            after_played,
            played_move
        )

        if queen_tempo:

            return (
                f"Вместо взятия {captured_name} "
                f"ходом {played_move} стоило сыграть "
                f"{best_move}. После взятия соперник "
                f"получает темп, атакуя ферзя, "
                f"и усиливает свою инициативу."
            )

        # --------------------------------------------------
        # ШАХ
        # --------------------------------------------------

        for reply in after_played.legal_moves:

            if after_played.gives_check(reply):

                return (
                    f"Вместо взятия {captured_name} "
                    f"ходом {played_move} стоило сыграть "
                    f"{best_move}. После взятия соперник "
                    f"получает темп с шахом и усиливает "
                    f"свою инициативу."
                )

        # --------------------------------------------------
        # НОВАЯ АТАКА НА ФИГУРУ
        # --------------------------------------------------

        attacked = find_newly_attacked_piece(
            board,
            after_played,
            our_color
        )

        if attacked:

            attacked_piece_name, attacked_square = attacked

            square_name = chess.square_name(
                attacked_square
            )

            best_piece_name = piece_name(
                best_piece
            )

            if best_piece_name:

                return (
                    f"Вместо взятия {captured_name} "
                    f"ходом {played_move} стоило улучшить "
                    f"{best_piece_name} ходом {best_move}. "
                    f"После взятия соперник получает темп, "
                    f"атакуя вашу {attacked_piece_name} "
                    f"на {square_name}, и усиливает "
                    f"свою инициативу."
                )

            return (
                f"Вместо взятия {captured_name} "
                f"ходом {played_move} стоило сыграть "
                f"{best_move}. После взятия соперник "
                f"получает темп, атакуя вашу "
                f"{attacked_piece_name} на {square_name}, "
                f"и усиливает свою инициативу."
            )

        # --------------------------------------------------
        # СОПЕРНИК МОЖЕТ СРАЗУ ЗАБРАТЬ ФИГУРУ
        # --------------------------------------------------

        for reply in after_played.legal_moves:

            captured_piece = get_captured_piece(
                after_played,
                reply
            )

            if not captured_piece:
                continue

            if captured_piece.piece_type in (
                chess.PAWN,
                chess.KING,
            ):
                continue

            captured_name_by_reply = piece_name(
                captured_piece
            )

            if not captured_name_by_reply:
                continue

            return (
                f"Вместо взятия {captured_name} "
                f"ходом {played_move} стоило сыграть "
                f"{best_move}. После взятия соперник "
                f"получает темп и может сразу забрать "
                f"{captured_name_by_reply}, усиливая "
                f"свою инициативу."
            )

        return None

    except Exception as e:

        print(
            "Ошибка detect_tempo_material_loss:",
            e
        )

        return None

def detect_equal_trade(
    board,
    best_move
):

    return (
        detect_equal_trade_info(
            board,
            best_move
        )
        is not None
    )

def get_equal_trade_text(
    trade_info
):

    if not trade_info:
        return ""

    moving_piece = trade_info.get(
        "moving_piece"
    )

    target_piece = trade_info.get(
        "target_piece"
    )

    if not moving_piece or not target_piece:
        return ""

    moving_name = piece_name(
        moving_piece
    )

    target_name = piece_name(
        target_piece
    )

    if (
        moving_piece.piece_type
        == target_piece.piece_type
    ):

        return (
            f"предложить равноценный "
            f"размен {moving_name}."
        )

    if moving_piece.piece_type in (
        chess.KNIGHT,
        chess.BISHOP,
    ) and target_piece.piece_type in (
        chess.KNIGHT,
        chess.BISHOP,
    ):

        return (
            f"предложить равноценный "
            f"размен {moving_name} и {target_name}."
        )

    return (
        f"предложить равноценный "
        f"размен {moving_name} и {target_name}."
    )

def detect_center_pawn_move(
    board,
    best_move
):

    if not board or not best_move:
        return False

    try:

        piece = board.piece_at(
            best_move.from_square
        )

        if not piece:
            return False

        if piece.piece_type != chess.PAWN:
            return False

        if (
            best_move.to_square
            in CENTER_SQUARES
        ):
            return True

        after = make_position_after(
            board,
            best_move
        )

        if not after:
            return False

        attacked_squares = (
            after.attacks(
                best_move.to_square
            )
        )

        return any(
            square in CENTER_SQUARES
            for square in attacked_squares
        )

    except Exception:

        return False

def _find_pin_material_sequence(
    board_before,
    board_after,
    our_color
):

    if (
        board_before is None
        or board_after is None
    ):
        return None

    try:

        opponent_color = not our_color

        slider_types = {
            chess.ROOK,
            chess.BISHOP,
            chess.QUEEN,
        }

        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 100,
        }

        def get_value(piece):

            if not piece:
                return 0

            return piece_values.get(
                piece.piece_type,
                0
            )

        # ==================================================
        # ПРОВЕРКА: МОЖНО ЛИ ПОСЛЕ ВЗЯТИЯ ОТБИТЬ ФИГУРУ
        # ==================================================

        def can_recapture(
            position,
            capture_move
        ):

            try:

                test = position.copy()

                attacker_square = (
                    capture_move.from_square
                )

                test.push(capture_move)

                for reply in list(test.legal_moves):

                    if (
                        reply.to_square
                        != attacker_square
                    ):
                        continue

                    piece = test.piece_at(
                        reply.from_square
                    )

                    if not piece:
                        continue

                    if piece.color != our_color:
                        continue

                    target = test.piece_at(
                        reply.to_square
                    )

                    if not target:
                        continue

                    if target.color != opponent_color:
                        continue

                    after = test.copy()

                    try:
                        after.push(reply)
                    except Exception:
                        continue

                    if after.is_check():
                        continue

                    return True

            except Exception:
                pass

            return False

        # ==================================================
        # ПРОВЕРКА АБСОЛЮТНОЙ СВЯЗКИ
        # ==================================================

        def get_absolute_pin_info(
            position,
            pin_move,
            pinned_square
        ):

            try:

                pinned_piece = position.piece_at(
                    pinned_square
                )

                if not pinned_piece:
                    return None

                if pinned_piece.color != our_color:
                    return None

                if pinned_piece.piece_type == chess.KING:
                    return None

                king_square = position.king(
                    our_color
                )

                if king_square is None:
                    return None

                # Фигура действительно абсолютна связана.
                if not position.is_pinned(
                    our_color,
                    pinned_square
                ):
                    return None

                attacker_square = (
                    pin_move.to_square
                )

                attacker_piece = position.piece_at(
                    attacker_square
                )

                if not attacker_piece:
                    return None

                if attacker_piece.color != opponent_color:
                    return None

                if attacker_piece.piece_type not in slider_types:
                    return None

                attacker_file = chess.square_file(
                    attacker_square
                )

                attacker_rank = chess.square_rank(
                    attacker_square
                )

                pinned_file = chess.square_file(
                    pinned_square
                )

                pinned_rank = chess.square_rank(
                    pinned_square
                )

                king_file = chess.square_file(
                    king_square
                )

                king_rank = chess.square_rank(
                    king_square
                )

                # --------------------------------------------------
                # Все три точки должны лежать на одной линии.
                # --------------------------------------------------

                same_file = (
                    attacker_file
                    == pinned_file
                    == king_file
                )

                same_rank = (
                    attacker_rank
                    == pinned_rank
                    == king_rank
                )

                same_diag = (
                    abs(
                        attacker_file
                        - pinned_file
                    )
                    ==
                    abs(
                        attacker_rank
                        - pinned_rank
                    )
                    and
                    abs(
                        pinned_file
                        - king_file
                    )
                    ==
                    abs(
                        pinned_rank
                        - king_rank
                    )
                )

                if not (
                    same_file
                    or same_rank
                    or same_diag
                ):
                    return None

                # --------------------------------------------------
                # Направление:
                #
                # attacker -> pinned -> king
                # --------------------------------------------------

                dx1 = pinned_file - attacker_file
                dy1 = pinned_rank - attacker_rank

                dx2 = king_file - pinned_file
                dy2 = king_rank - pinned_rank

                if dx1 != 0:
                    dx1 = 1 if dx1 > 0 else -1

                if dy1 != 0:
                    dy1 = 1 if dy1 > 0 else -1

                if dx2 != 0:
                    dx2 = 1 if dx2 > 0 else -1

                if dy2 != 0:
                    dy2 = 1 if dy2 > 0 else -1

                if (
                    dx1 != dx2
                    or dy1 != dy2
                ):
                    return None

                # --------------------------------------------------
                # Проверяем, что между связующей фигурой
                # и связанной фигурой нет другой фигуры.
                # --------------------------------------------------

                current_file = (
                    attacker_file + dx1
                )

                current_rank = (
                    attacker_rank + dy1
                )

                while (
                    0 <= current_file < 8
                    and
                    0 <= current_rank < 8
                ):

                    square = chess.square(
                        current_file,
                        current_rank
                    )

                    if square == pinned_square:
                        break

                    if position.piece_at(square):
                        return None

                    current_file += dx1
                    current_rank += dy1

                king_piece = position.piece_at(
                    king_square
                )

                if not king_piece:
                    return None

                # --------------------------------------------------
                # Очень важно:
                #
                # Связующая фигура должна реально атаковать
                # связанную фигуру.
                # --------------------------------------------------

                if pinned_square not in position.attacks(
                    attacker_square
                ):
                    return None

                return {
                    "pin_type": "absolute",
                    "pinned_square": pinned_square,
                    "pinned_piece": pinned_piece,
                    "behind_square": king_square,
                    "behind_piece": king_piece,
                    "attacker_square": attacker_square,
                    "attacker_piece": attacker_piece,
                }

            except Exception:
                return None

        # ==================================================
        # БЫЛА ЛИ СВЯЗКА ДО НАШЕГО ХОДА?
        # ==================================================

        def pin_already_existed(
            pinned_square,
            pin_move
        ):

            try:

                before_piece = board_before.piece_at(
                    pinned_square
                )

                if not before_piece:
                    return True

                if before_piece.color != our_color:
                    return True

                # Если фигура уже была абсолютно связана,
                # это не новая тактическая причина.
                if board_before.is_pinned(
                    our_color,
                    pinned_square
                ):
                    return True

                # --------------------------------------------------
                # ВАЖНО:
                #
                # pin_move.to_square в старой позиции может быть
                # пустым, поэтому здесь нельзя считать отсутствие
                # фигуры доказательством отсутствия связки.
                #
                # Нас интересует именно новая связка после хода.
                # --------------------------------------------------

                return False

            except Exception:
                return False

        # ==================================================
        # ИЩЕМ ХОД СОПЕРНИКА, КОТОРЫЙ СОЗДАЁТ НОВУЮ СВЯЗКУ
        # ==================================================

        candidates = []

        for pin_move in list(
            board_after.legal_moves
        ):

            try:

                attacker = board_after.piece_at(
                    pin_move.from_square
                )

                if not attacker:
                    continue

                if attacker.color != opponent_color:
                    continue

                if attacker.piece_type not in slider_types:
                    continue

                # --------------------------------------------------
                # Делаем ход соперника.
                #
                # ВАЖНО:
                # Здесь разрешаем шах!
                #
                # Именно это исправляет проблему Qh4+.
                # --------------------------------------------------

                test_board = board_after.copy()

                try:
                    test_board.push(pin_move)
                except Exception:
                    continue

                # --------------------------------------------------
                # Если ход создаёт новую абсолютную связку,
                # перебираем наши фигуры.
                # --------------------------------------------------

                for pinned_square, pinned_piece in list(
                    test_board.piece_map().items()
                ):

                    if pinned_piece.color != our_color:
                        continue

                    if pinned_piece.piece_type == chess.KING:
                        continue

                    # Связывать пешку для этого объяснения
                    # не считаем выигрышем фигуры.
                    if pinned_piece.piece_type == chess.PAWN:
                        continue

                    # Нужна хотя бы лёгкая фигура.
                    if get_value(pinned_piece) < 3:
                        continue

                    pin_info = get_absolute_pin_info(
                        test_board,
                        pin_move,
                        pinned_square
                    )

                    if not pin_info:
                        continue

                    if pin_already_existed(
                        pinned_square,
                        pin_move
                    ):
                        continue

                    # ==================================================
                    # НОВОЕ:
                    #
                    # Если pin_move даёт шах, сначала ищем ответы
                    # на шах, а уже после них проверяем возможность
                    # выиграть связанную фигуру.
                    # ==================================================

                    legal_replies = list(
                        test_board.legal_moves
                    )

                    # --------------------------------------------------
                    # Если это не шах — всё равно рассматриваем
                    # позицию непосредственно после pin_move.
                    # --------------------------------------------------

                    positions_after_pin = [
                        (
                            test_board,
                            None
                        )
                    ]

                    # --------------------------------------------------
                    # Если это шах, добавляем позиции после каждого
                    # нормального ответа на шах.
                    # --------------------------------------------------

                    if test_board.is_check():

                        for reply in legal_replies:

                            reply_board = (
                                test_board.copy()
                            )

                            try:
                                reply_board.push(reply)
                            except Exception:
                                continue

                            positions_after_pin.append(
                                (
                                    reply_board,
                                    reply
                                )
                            )

                    # ==================================================
                    # ИЩЕМ РЕАЛЬНЫЙ ВЫИГРЫШ СВЯЗАННОЙ ФИГУРЫ
                    # ==================================================

                    best_capture = None
                    best_capture_board = None
                    best_reply = None

                    for position_after_pin, reply in (
                        positions_after_pin
                    ):

                        # --------------------------------------------------
                        # Проверяем: может ли соперник взять связанную
                        # фигуру следующим ходом?
                        # --------------------------------------------------

                        for capture_move in list(
                            position_after_pin.legal_moves
                        ):

                            if (
                                capture_move.to_square
                                != pinned_square
                            ):
                                continue

                            captured_piece = (
                                get_captured_piece(
                                    position_after_pin,
                                    capture_move
                                )
                            )

                            if not captured_piece:
                                continue

                            if captured_piece.color != our_color:
                                continue

                            if captured_piece.piece_type in (
                                chess.PAWN,
                                chess.KING,
                            ):
                                continue

                            capturing_piece = (
                                position_after_pin.piece_at(
                                    capture_move.from_square
                                )
                            )

                            if not capturing_piece:
                                continue

                            if (
                                capturing_piece.color
                                != opponent_color
                            ):
                                continue

                            captured_value = get_value(
                                captured_piece
                            )

                            attacker_value = get_value(
                                capturing_piece
                            )

                            # Не считаем размен выигрышем материала,
                            # если более дорогая фигура берёт более
                            # дешёвую.
                            if attacker_value > captured_value:
                                continue

                            # Если после взятия наша фигура спокойно
                            # отбивает атакующего — это не выигрыш.
                            if can_recapture(
                                position_after_pin,
                                capture_move
                            ):
                                continue

                            candidate = {
                                "move": capture_move,
                                "board": position_after_pin,
                                "reply": reply,
                                "captured_value": captured_value,
                                "attacker_value": attacker_value,
                            }

                            if (
                                best_capture is None
                                or
                                candidate["captured_value"]
                                >
                                best_capture["captured_value"]
                            ):
                                best_capture = candidate
                                best_capture_board = (
                                    position_after_pin
                                )
                                best_reply = reply

                    # ==================================================
                    # ЕСЛИ НЕМЕДЛЕННОГО ВЗЯТИЯ НЕТ
                    #
                    # Всё равно разрешаем детектору признать новую
                    # абсолютную связку, если она делает фигуру
                    # фактически неподвижной.
                    #
                    # Это особенно важно для шаха + связки.
                    # ==================================================

                    if best_capture is None:

                        # Фигура должна действительно быть
                        # неподвижна из-за абсолютной связки.
                        movable = False

                        for escape_move in list(
                            test_board.legal_moves
                        ):

                            if (
                                escape_move.from_square
                                != pinned_square
                            ):
                                continue

                            movable = True
                            break

                        # При шахе legal_moves могут вообще не
                        # содержать ход связанной фигуры.
                        #
                        # Поэтому здесь ориентируемся прежде всего
                        # на сам факт абсолютной связки.
                        if movable:
                            continue

                        # Если связующая фигура сама атакует
                        # связанную фигуру — это достаточное
                        # тактическое подтверждение.
                        attacker_square = pin_info.get(
                            "attacker_square"
                        )

                        if attacker_square is None:
                            continue

                        if pinned_square not in (
                            test_board.attacks(
                                attacker_square
                            )
                        ):
                            continue

                    # ==================================================
                    # SAN
                    # ==================================================

                    try:
                        pin_san = board_after.san(
                            pin_move
                        )
                    except Exception:
                        pin_san = ""

                    if not pin_san:
                        continue

                    capture_san = ""

                    if best_capture is not None:

                        try:
                            capture_san = (
                                best_capture_board.san(
                                    best_capture["move"]
                                )
                            )
                        except Exception:
                            capture_san = ""

                    # ==================================================
                    # ИМЕНА
                    # ==================================================

                    pinned_name = piece_name(
                        pinned_piece
                    )

                    if not pinned_name:
                        continue

                    # ==================================================
                    # СОХРАНЯЕМ КАНДИДАТ
                    # ==================================================

                    candidates.append(
                        {
                            "pin_move": pin_move,
                            "pin_san": pin_san,

                            "capture_move": (
                                best_capture["move"]
                                if best_capture
                                else None
                            ),

                            "capture_san": capture_san,

                            "pinned_piece": pinned_piece,

                            "pinned_piece_name": pinned_name,

                            "pinned_square": pinned_square,

                            "capturing_piece": (
                                position_after_pin.piece_at(
                                    best_capture["move"].from_square
                                )
                                if (
                                    best_capture
                                    and
                                    position_after_pin
                                )
                                else None
                            ),

                            "capturing_piece_name": (
                                piece_name(
                                    position_after_pin.piece_at(
                                        best_capture["move"].from_square
                                    )
                                )
                                if (
                                    best_capture
                                    and
                                    position_after_pin
                                )
                                else ""
                            ),

                            "behind_piece": pin_info.get(
                                "behind_piece"
                            ),

                            "behind_piece_name": (
                                piece_name(
                                    pin_info.get(
                                        "behind_piece"
                                    )
                                )
                                if pin_info.get(
                                    "behind_piece"
                                )
                                else ""
                            ),

                            "behind_square": pin_info.get(
                                "behind_square"
                            ),

                            "pin_type": "absolute",

                            "priority": (
                                1000,
                                get_value(
                                    pinned_piece
                                ),
                                (
                                    best_capture["captured_value"]
                                    if best_capture
                                    else 0
                                ),
                            ),
                        }
                    )

            except Exception as e:

                print(
                    "PIN MOVE ANALYSIS ERROR:",
                    e
                )

                continue

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item.get(
                "priority",
                (0, 0, 0)
            ),
            reverse=True
        )

        return candidates[0]

    except Exception as e:

        print(
            "Ошибка _find_pin_material_sequence:",
            e
        )

        return None

def detect_pin_material_loss(
    board_before,
    board_after,
    played_move,
    loss=0
):

    if (
        board_before is None
        or board_after is None
        or played_move is None
    ):
        return None

    try:

        try:
            numeric_loss = float(loss)
        except Exception:
            numeric_loss = 0

        if numeric_loss < 100:
            return None

        our_color = board_before.turn

        info = _find_pin_material_sequence(
            board_before,
            board_after,
            our_color
        )

        if not info:
            return None

        info["played_move"] = played_move
        info["loss"] = numeric_loss

        return info

    except Exception as e:

        print(
            "Ошибка detect_pin_material_loss:",
            e
        )

        return None

def get_pin_material_loss_text(
    info,
    played
):

    if not info:
        return ""

    pinned_name = (
        info.get(
            "pinned_piece_name"
        )
        or "фигуру"
    )

    pin_san = (
        info.get(
            "pin_san"
        )
        or ""
    )

    capture_san = (
        info.get(
            "capture_san"
        )
        or ""
    )

    # ------------------------------------------------------
    # Именно формулировка, которую ты хочешь видеть.
    #
    # Не расписываем Qh4+, не говорим про шах,
    # не говорим "фигура не может уйти".
    # Сначала называем саму идею:
    # выигрыш материала через связку.
    # ------------------------------------------------------

    if capture_san:

        return (
            "Вы позволили сопернику выиграть "
            "материал, связав вашу фигуру "
            "с королём."
        )

    return (
        "Вы позволили сопернику выиграть "
        "материал, связав вашу фигуру "
        "с королём."
    )

def detect_apparent_piece_loss_but_recapturable(
    board,
    played_move,
    best_move,
    loss=0
):

    if (
        not board
        or not played_move
        or not best_move
    ):
        return None

    try:

        # ==================================================
        # БАЗОВЫЕ ДАННЫЕ
        # ==================================================

        try:
            numeric_loss = float(loss)
        except Exception:
            numeric_loss = 0

        # Эта причина нужна только для серьёзных ошибок
        if numeric_loss < 200:
            return None

        board_after = make_position_after(
            board,
            played_move
        )

        if not board_after:
            return None

        our_color = board.turn
        opponent_color = not our_color

        candidate_replies = []

        # ==================================================
        # ИЩЕМ ХОДЫ СОПЕРНИКА, КОТОРЫЕ ЗАБИРАЮТ
        # НАШУ ФИГУРУ
        # ==================================================

        for opponent_move in board_after.legal_moves:

            captured_piece = get_captured_piece(
                board_after,
                opponent_move
            )

            if not captured_piece:
                continue

            # Берём только НАШУ фигуру
            if captured_piece.color != our_color:
                continue

            # Пешки здесь не рассматриваем.
            # Король тоже не рассматривается.
            if captured_piece.piece_type in (
                chess.PAWN,
                chess.KING,
            ):
                continue

            attacker_piece = board_after.piece_at(
                opponent_move.from_square
            )

            if not attacker_piece:
                continue

            if attacker_piece.color != opponent_color:
                continue

            if attacker_piece.piece_type == chess.KING:
                continue

            captured_value = piece_value(
                captured_piece
            )

            attacker_value = piece_value(
                attacker_piece
            )

            # ==================================================
            # КРИТИЧЕСКАЯ ПРОВЕРКА
            #
            # Если соперник отдаёт БОЛЕЕ ЦЕННУЮ фигуру
            # за нашу менее ценную фигуру, это НЕ потеря.
            #
            # Например:
            #
            # Qxf7+ Kxf7
            #
            # captured_piece = ладья = 5
            # attacker_piece = ферзь = 9
            #
            # Соперник отдаёт 9 за 5.
            # Такой вариант НЕ должен попадать сюда.
            # ==================================================

            # Равный обмен тоже не является потерей фигуры.
            # Например Qxf7+ Kxf7 — это размен ферзей,
            # а не "потеря" ферзя.
            if attacker_value >= captured_value:
                continue

            candidate_replies.append(
                {
                    "move": opponent_move,
                    "captured_piece": captured_piece,
                    "attacker_piece": attacker_piece,
                    "captured_value": captured_value,
                    "attacker_value": attacker_value,
                }
            )

        if not candidate_replies:
            return None

        # ==================================================
        # СНАЧАЛА ПРОВЕРЯЕМ САМЫЕ ЦЕННЫЕ НАШИ ФИГУРЫ
        # ==================================================

        candidate_replies.sort(
            key=lambda item: (
                item.get(
                    "captured_value",
                    0
                ),
                -item.get(
                    "attacker_value",
                    0
                )
            ),
            reverse=True
        )

        # ==================================================
        # ПРОВЕРЯЕМ КАЖДЫЙ ВАРИАНТ
        # ==================================================

        for candidate in candidate_replies:

            opponent_move = candidate.get(
                "move"
            )

            captured_piece = candidate.get(
                "captured_piece"
            )

            attacker_piece = candidate.get(
                "attacker_piece"
            )

            captured_value = candidate.get(
                "captured_value",
                0
            )

            attacker_value = candidate.get(
                "attacker_value",
                0
            )

            if (
                not opponent_move
                or not captured_piece
                or not attacker_piece
            ):
                continue

            # ==================================================
            # ЕЩЁ РАЗ ПРОВЕРЯЕМ СООТНОШЕНИЕ
            # ==================================================

            # Равный обмен тоже не является потерей фигуры.
            # Например Qxf7+ Kxf7 — это размен ферзей,
            # а не "потеря" ферзя.
            if attacker_value >= captured_value:
                continue

            # ==================================================
            # ДЕЛАЕМ ХОД СОПЕРНИКА
            # ==================================================

            board_after_capture = (
                board_after.copy()
            )

            try:

                board_after_capture.push(
                    opponent_move
                )

            except Exception:

                continue

            # ==================================================
            # ИЩЕМ НАШУ РЕАЛЬНУЮ ОТВЕТНУЮ ВЗЯТИЕ
            # ==================================================

            recapture_candidates = []

            for our_reply in (
                board_after_capture.legal_moves
            ):

                # Ответ должен забирать именно фигуру,
                # которая только что взяла нашу фигуру.
                if (
                    our_reply.to_square
                    != opponent_move.to_square
                ):
                    continue

                recaptured_piece = (
                    get_captured_piece(
                        board_after_capture,
                        our_reply
                    )
                )

                if not recaptured_piece:
                    continue

                if (
                    recaptured_piece.color
                    != opponent_color
                ):
                    continue

                if (
                    recaptured_piece.piece_type
                    == chess.KING
                ):
                    continue

                our_recapturing_piece = (
                    board_after_capture.piece_at(
                        our_reply.from_square
                    )
                )

                if not our_recapturing_piece:
                    continue

                if (
                    our_recapturing_piece.color
                    != our_color
                ):
                    continue

                # ==================================================
                # ВАЖНАЯ ПРОВЕРКА:
                #
                # После нашего взятия фигура действительно
                # должна исчезнуть.
                # ==================================================

                test_exchange = (
                    board_after_capture.copy()
                )

                try:

                    test_exchange.push(
                        our_reply
                    )

                except Exception:

                    continue

                if (
                    test_exchange.piece_at(
                        our_reply.to_square
                    ) is None
                ):
                    continue

                final_piece = (
                    test_exchange.piece_at(
                        our_reply.to_square
                    )
                )

                if not final_piece:
                    continue

                if (
                    final_piece.color
                    != our_color
                ):
                    continue

                recapture_candidates.append(
                    {
                        "move": our_reply,
                        "piece": our_recapturing_piece,
                        "captured_piece":
                            recaptured_piece,
                        "board_after":
                            test_exchange,
                    }
                )

            # ==================================================
            # НЕТ РЕАЛЬНОГО ОТВЕТНОГО ВЗЯТИЯ
            # ==================================================

            if not recapture_candidates:
                continue

            # ==================================================
            # ВЫБИРАЕМ ЛУЧШЕЕ ОТВЕТНОЕ ВЗЯТИЕ
            # ==================================================

            recapture_candidates.sort(
                key=lambda item:
                piece_value(
                    item.get(
                        "captured_piece"
                    )
                ),
                reverse=True
            )

            selected_recapture = (
                recapture_candidates[0]
            )

            recapture_move = (
                selected_recapture.get(
                    "move"
                )
            )

            recapturing_piece = (
                selected_recapture.get(
                    "piece"
                )
            )

            recaptured_attacker = (
                selected_recapture.get(
                    "captured_piece"
                )
            )

            board_after_exchange = (
                selected_recapture.get(
                    "board_after"
                )
            )

            if not recapture_move:
                continue

            if not recapturing_piece:
                continue

            if not recaptured_attacker:
                continue

            if not board_after_exchange:
                continue

            # ==================================================
            # КРИТИЧЕСКАЯ ПРОВЕРКА МАТЕРИАЛЬНОГО РЕЗУЛЬТАТА
            #
            # Если после размена мы получаем более ценную
            # фигуру, чем отдали, это не "потеря фигуры".
            #
            # Пример:
            #
            # Qxf7+ Kxf7
            #
            # Мы отдаём ладью = 5
            # Забираем ферзя = 9
            #
            # Такой вариант полностью исключается.
            # ==================================================

            recaptured_value = piece_value(
                recaptured_attacker
            )

            # Если мы возвращаем фигуру той же или большей
            # ценности, это обычный размен, а не потеря.
            if recaptured_value >= captured_value:
                continue

            # ==================================================
            # SAN
            # ==================================================

            try:

                opponent_san = (
                    board_after.san(
                        opponent_move
                    )
                )

            except Exception:

                opponent_san = ""

            try:

                recapture_san = (
                    board_after_capture.san(
                        recapture_move
                    )
                )

            except Exception:

                recapture_san = ""

            if not opponent_san:
                continue

            if not recapture_san:
                continue

            # ==================================================
            # НАЗВАНИЯ ФИГУР
            # ==================================================

            captured_name = piece_name(
                captured_piece
            )

            attacker_name = piece_name(
                attacker_piece
            )

            recapturing_name = piece_name(
                recapturing_piece
            )

            recaptured_attacker_name = piece_name(
                recaptured_attacker
            )

            if not captured_name:
                continue

            if not attacker_name:
                continue

            if not recapturing_name:
                continue

            if not recaptured_attacker_name:
                continue

            # ==================================================
            # ВОЗВРАЩАЕМ ИНФОРМАЦИЮ
            # ==================================================

            return {
                "opponent_move":
                    opponent_move,

                "opponent_san":
                    opponent_san,

                "captured_piece":
                    captured_piece,

                "captured_piece_name":
                    captured_name,

                "captured_value":
                    captured_value,

                "attacker_piece":
                    attacker_piece,

                "attacker_piece_name":
                    attacker_name,

                "attacker_value":
                    attacker_value,

                "recapture_move":
                    recapture_move,

                "recapture_san":
                    recapture_san,

                "recapturing_piece":
                    recapturing_piece,

                "recapturing_piece_name":
                    recapturing_name,

                "recaptured_attacker":
                    recaptured_attacker,

                "recaptured_attacker_name":
                    recaptured_attacker_name,

                "recaptured_value":
                    recaptured_value,

                "loss":
                    numeric_loss,

                "board_after_exchange":
                    board_after_exchange,
            }

        return None

    except Exception as e:

        print(
            "Ошибка detect_apparent_piece_loss_but_recapturable:",
            e
        )

        return None

def detect_newly_pinned_pawn(
    board_before,
    board_after,
    played_move=None,
    preferred_move=None
):
    """
    Ищет новую дополнительную связку нашей пешки после хода.

    Важно:
    - Если пешка уже была связана до нашего хода, это НЕ мешает
      обнаружить новую связку другим атакующим.
    - Если среди возможных новых связок есть та, которую первым
      предлагает Stockfish (preferred_move), выбираем именно её.
    - Ход, который просто забирает только что передвинутую нами
      фигуру/пешку, не используется как объяснение новой связки.
    """

    if not board_before or not board_after:
        return None

    try:
        our_color = not board_after.turn
        opponent_color = board_after.turn

        piece_names = {
            chess.PAWN: "пешку",
            chess.KNIGHT: "коня",
            chess.BISHOP: "слона",
            chess.ROOK: "ладью",
            chess.QUEEN: "ферзя",
            chess.KING: "короля",
        }

        piece_instrumental = {
            chess.PAWN: "пешкой",
            chess.KNIGHT: "конём",
            chess.BISHOP: "слоном",
            chess.ROOK: "ладьёй",
            chess.QUEEN: "ферзём",
            chess.KING: "королём",
        }

        valuable_types = {
            chess.KNIGHT,
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN,
        }

        sliding_types = {
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN,
        }

        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 100,
        }

        attacker_priority = {
            chess.QUEEN: 3,
            chess.ROOK: 2,
            chess.BISHOP: 1,
        }

        def piece_can_use_line(piece_type, from_square, to_square):
            """
            Проверяет, может ли фигура данного типа атаковать
            target по прямой/диагонали.
            """

            from_file = chess.square_file(from_square)
            from_rank = chess.square_rank(from_square)

            to_file = chess.square_file(to_square)
            to_rank = chess.square_rank(to_square)

            df = to_file - from_file
            dr = to_rank - from_rank

            if piece_type == chess.ROOK:
                return df == 0 or dr == 0

            if piece_type == chess.BISHOP:
                return abs(df) == abs(dr)

            if piece_type == chess.QUEEN:
                return (
                    df == 0
                    or dr == 0
                    or abs(df) == abs(dr)
                )

            return False

        def find_pin_on_board(board, pawn_square):
            """
            Ищет связку:

                соперник → наша пешка → наша ценная фигура

            Возвращает информацию о первой найденной связке.
            """

            pawn = board.piece_at(pawn_square)

            if not pawn:
                return None

            if pawn.piece_type != chess.PAWN:
                return None

            if pawn.color != our_color:
                return None

            pawn_file = chess.square_file(pawn_square)
            pawn_rank = chess.square_rank(pawn_square)

            # Ищем наши ценные фигуры, которые находятся за пешкой.
            for pinned_square in chess.SQUARES:

                pinned_piece = board.piece_at(pinned_square)

                if not pinned_piece:
                    continue

                if pinned_piece.color != our_color:
                    continue

                if pinned_piece.piece_type not in valuable_types:
                    continue

                # Пешка и фигура должны лежать на одной линии,
                # которую может использовать атакующая фигура.
                for attacker_square in chess.SQUARES:

                    attacker = board.piece_at(attacker_square)

                    if not attacker:
                        continue

                    if attacker.color != opponent_color:
                        continue

                    if attacker.piece_type not in sliding_types:
                        continue

                    if not piece_can_use_line(
                        attacker.piece_type,
                        attacker_square,
                        pinned_square
                    ):
                        continue

                    # Все три фигуры должны находиться на одной линии:
                    # attacker -> pawn -> pinned piece.
                    if not piece_can_use_line(
                        attacker.piece_type,
                        attacker_square,
                        pawn_square
                    ):
                        continue

                    # Проверяем направление.
                    af = chess.square_file(attacker_square)
                    ar = chess.square_rank(attacker_square)

                    pf = chess.square_file(pawn_square)
                    pr = chess.square_rank(pawn_square)

                    xf = chess.square_file(pinned_square)
                    xr = chess.square_rank(pinned_square)

                    direction1_file = pf - af
                    direction1_rank = pr - ar

                    direction2_file = xf - pf
                    direction2_rank = xr - pr

                    # Нормализуем направление.
                    def normalize(value):
                        if value > 0:
                            return 1
                        if value < 0:
                            return -1
                        return 0

                    d1 = (
                        normalize(direction1_file),
                        normalize(direction1_rank)
                    )

                    d2 = (
                        normalize(direction2_file),
                        normalize(direction2_rank)
                    )

                    if d1 != d2:
                        continue

                    # Проверяем, что между атакующей фигурой и
                    # пешкой ничего нет.
                    between_1 = chess.SquareSet(
                        chess.between(
                            attacker_square,
                            pawn_square
                        )
                    )

                    blocked = False

                    for square in between_1:
                        if board.piece_at(square):
                            blocked = True
                            break

                    if blocked:
                        continue

                    # Проверяем, что между пешкой и защищаемой
                    # фигурой ничего нет.
                    between_2 = chess.SquareSet(
                        chess.between(
                            pawn_square,
                            pinned_square
                        )
                    )

                    blocked = False

                    for square in between_2:
                        if board.piece_at(square):
                            blocked = True
                            break

                    if blocked:
                        continue

                    return {
                        "pawn_square": pawn_square,
                        "attacker_square": attacker_square,
                        "attacker": attacker,
                        "pinned_square": pinned_square,
                        "pinned_piece": pinned_piece,
                    }

            return None

        # ---------------------------------------------------------
        # 1. Какие пешки уже были связаны ДО нашего хода?
        # ---------------------------------------------------------

        pins_before = {}

        for pawn_square in chess.SQUARES:

            piece = board_before.piece_at(pawn_square)

            if not piece:
                continue

            if piece.color != our_color:
                continue

            if piece.piece_type != chess.PAWN:
                continue

            pin_info = find_pin_on_board(
                board_before,
                pawn_square
            )

            if pin_info:
                pins_before[pawn_square] = pin_info

        # ---------------------------------------------------------
        # 2. Проверяем все легальные ходы соперника после
        #    нашего хода.
        # ---------------------------------------------------------

        candidates = []

        for opponent_move in board_after.legal_moves:

            moving_piece = board_after.piece_at(
                opponent_move.from_square
            )

            if not moving_piece:
                continue

            if moving_piece.color != opponent_color:
                continue

            if moving_piece.piece_type not in sliding_types:
                continue

            # -----------------------------------------------------
            # Если этот ход просто забирает фигуру/пешку, которую
            # мы только что передвинули, не используем его как
            # объяснение "новой связки".
            #
            # Например:
            #
            # f2-f3 Qxf3
            #
            # Qxf3 — это непосредственное взятие пешки, а не
            # полезное объяснение того, что пешка g2 оказалась
            # связана с ладьёй h1.
            # -----------------------------------------------------

            captures_played_piece = False

            if played_move is not None:

                if opponent_move.to_square == played_move.to_square:

                    captured_piece = board_after.piece_at(
                        opponent_move.to_square
                    )

                    # После нашего хода на этой клетке находится
                    # именно наша только что передвинутая фигура.
                    if captured_piece and (
                        captured_piece.color == our_color
                    ):
                        captures_played_piece = True

            # Делаем копию позиции и выполняем потенциальный
            # ответ соперника.
            test_board = board_after.copy()

            try:
                test_board.push(opponent_move)
            except Exception:
                continue

            # После хода соперника наша сторона уже НЕ ходит.
            # Ищем пешки, которые теперь оказываются связаны.
            for pawn_square in chess.SQUARES:

                pawn = test_board.piece_at(pawn_square)

                if not pawn:
                    continue

                if pawn.color != our_color:
                    continue

                if pawn.piece_type != chess.PAWN:
                    continue

                pin_info = find_pin_on_board(
                    test_board,
                    pawn_square
                )

                if not pin_info:
                    continue

                old_pin = pins_before.get(pawn_square)

                # -------------------------------------------------
                # Если пешка не была связана раньше — это обычная
                # новая связка.
                # -------------------------------------------------

                if old_pin is None:

                    is_new_pin = True

                else:

                    # -------------------------------------------------
                    # Пешка уже была связана.
                    #
                    # Но если после нашего хода её связал ДРУГОЙ
                    # атакующий, это новая ДОПОЛНИТЕЛЬНАЯ связка.
                    # -------------------------------------------------

                    old_attacker_square = old_pin[
                        "attacker_square"
                    ]

                    new_attacker_square = pin_info[
                        "attacker_square"
                    ]

                    old_attacker_type = old_pin[
                        "attacker"
                    ].piece_type

                    new_attacker_type = pin_info[
                        "attacker"
                    ].piece_type

                    # Та же самая связка — не новая.
                    if (
                        old_attacker_square == new_attacker_square
                        and
                        old_attacker_type == new_attacker_type
                    ):
                        continue

                    # Другой атакующий = новая дополнительная
                    # связка.
                    is_new_pin = True

                if not is_new_pin:
                    continue

                # -------------------------------------------------
                # Проверяем, совпадает ли этот ход с первым ходом
                # Stockfish.
                # -------------------------------------------------

                is_preferred = False

                if preferred_move is not None:

                    try:
                        is_preferred = (
                            opponent_move == preferred_move
                        )
                    except Exception:
                        is_preferred = False

                pinned_piece = pin_info["pinned_piece"]

                candidates.append({
                    "move": opponent_move,
                    "pin_move": opponent_move,
                    "pawn_square": pawn_square,
                    "attacker_square": pin_info[
                        "attacker_square"
                    ],
                    "attacker": pin_info["attacker"],
                    "pinned_square": pin_info[
                        "pinned_square"
                    ],
                    "pinned_piece": pinned_piece,

                    # Служебные поля.
                    "_is_preferred": is_preferred,
                    "_captures_played_piece": (
                        captures_played_piece
                    ),
                    "_attacker_priority": attacker_priority.get(
                        pin_info["attacker"].piece_type,
                        0
                    ),
                })

        # ---------------------------------------------------------
        # 3. Если ничего не нашли — возвращаем None.
        # ---------------------------------------------------------

        if not candidates:
            return None

        # ---------------------------------------------------------
        # 4. Сначала убираем из выбора ходы, которые просто
        #    забирают только что передвинутую фигуру.
        #
        #    Но только если существуют другие нормальные кандидаты.
        # ---------------------------------------------------------

        normal_candidates = [
            candidate
            for candidate in candidates
            if not candidate["_captures_played_piece"]
        ]

        if normal_candidates:
            candidates = normal_candidates

        # ---------------------------------------------------------
        # 5. Если первый ход Stockfish создаёт одну из найденных
        #    связок — выбираем именно его.
        #
        #    Это позволит в твоём примере выбрать Qd6 среди:
        #
        #    Qd7
        #    Qd6
        #    Qd5
        #    Rd7
        #    Rd6
        #    Rd5
        #
        #    и т.д.
        # ---------------------------------------------------------

        preferred_candidates = [
            candidate
            for candidate in candidates
            if candidate["_is_preferred"]
        ]

        if preferred_candidates:

            selected = preferred_candidates[0]

        else:

            # -----------------------------------------------------
            # Если preferred_move не передан или он не создаёт
            # найденную связку, используем обычную сортировку:
            #
            # 1. более сильный атакующий;
            # 2. более ценная связанная фигура.
            # -----------------------------------------------------

            def candidate_score(candidate):

                pinned_piece = candidate["pinned_piece"]

                return (
                    candidate["_attacker_priority"],
                    piece_values.get(
                        pinned_piece.piece_type,
                        0
                    )
                )

            selected = max(
                candidates,
                key=candidate_score
            )

        # ---------------------------------------------------------
        # 6. Получаем SAN хода связки.
        # ---------------------------------------------------------

        try:
            temp_board = board_after.copy()
            san = temp_board.san(selected["pin_move"])
        except Exception:
            san = selected["pin_move"].uci()

        # ---------------------------------------------------------
        # 7. Формируем объяснение.
        # ---------------------------------------------------------

        pawn_name = piece_names[chess.PAWN]

        pinned_piece_type = selected[
            "pinned_piece"
        ].piece_type

        pinned_piece_name = piece_names.get(
            pinned_piece_type,
            "фигуру"
        )

        instrumental_name = piece_instrumental.get(
            pinned_piece_type,
            "фигурой"
        )

        # Корректное управление "с / со":
        if pinned_piece_type == chess.BISHOP:
            preposition = "со"
        else:
            preposition = "с"

        text = (
            f"После вашего хода соперник может сыграть "
            f"{san} и связать вашу {pawn_name} на "
            f"{chess.square_name(selected['pawn_square'])} "
            f"{preposition} {instrumental_name} на "
            f"{chess.square_name(selected['pinned_square'])}."
        )

        # ---------------------------------------------------------
        # 8. Убираем служебные поля перед возвратом.
        # ---------------------------------------------------------

        selected.pop("_is_preferred", None)
        selected.pop("_captures_played_piece", None)
        selected.pop("_attacker_priority", None)

        selected["san"] = san
        selected["text"] = text

        return selected

    except Exception as e:

        print(
            f"[detect_newly_pinned_pawn] ERROR: {e}"
        )

        return None

def detect_queen_activity(
    position_before,
    board_after_played,
    played_move,
    played_results
):
    """
    Определяет ситуацию, когда после хода пользователя
    соперник получает возможность существенно активизировать
    ферзя.

    Важно:
    - не реагирует на любой ход ферзём;
    - не реагирует на взятия;
    - не реагирует на шахи;
    - сравнивает активность ферзя ДО и ПОСЛЕ хода пользователя;
    - особенно сильный сигнал — ход ферзём, который раньше
      был невозможен;
    - использует верхние ответы из played_results.
    """

    if (
        position_before is None
        or board_after_played is None
        or played_move is None
        or not played_results
    ):
        return None

    try:

        opponent_color = board_after_played.turn

        # --------------------------------------------------
        # Оценка активности ферзя на конкретном поле.
        #
        # Это не шахматная оценка Stockfish.
        # Это только вспомогательный показатель:
        #
        #   + атаки на фигуры
        #   + атаки рядом с королём
        #   + мобильность
        #   + контроль центра
        #
        # Чем выше значение, тем активнее ферзь.
        # --------------------------------------------------

        def queen_activity_score(
            board,
            queen_square,
            queen_color
        ):

            if board is None:
                return 0

            piece = board.piece_at(
                queen_square
            )

            if (
                piece is None
                or piece.piece_type != chess.QUEEN
                or piece.color != queen_color
            ):
                return 0

            score = 0

            try:

                attacks = board.attacks(
                    queen_square
                )

            except Exception:

                attacks = []

            # --------------------------------------------------
            # Мобильность ферзя.
            # --------------------------------------------------

            mobility = 0

            try:

                for move in board.legal_moves:

                    if (
                        move.from_square
                        == queen_square
                    ):
                        mobility += 1

            except Exception:
                mobility = 0

            score += min(
                mobility,
                12
            )

            # --------------------------------------------------
            # Атаки на фигуры соперника.
            # Чем ценнее фигура — тем сильнее
            # активизация ферзя.
            # --------------------------------------------------

            attacked_values = {
                chess.PAWN: 1,
                chess.KNIGHT: 3,
                chess.BISHOP: 3,
                chess.ROOK: 5,
                chess.QUEEN: 9,
                chess.KING: 0,
            }

            for square in attacks:

                target = board.piece_at(
                    square
                )

                if not target:
                    continue

                if target.color == queen_color:
                    continue

                score += attacked_values.get(
                    target.piece_type,
                    0
                ) * 4

            # --------------------------------------------------
            # Контроль центральных полей.
            # --------------------------------------------------

            center_squares = {
                chess.D4,
                chess.E4,
                chess.D5,
                chess.E5,
            }

            for square in attacks:

                if square in center_squares:
                    score += 2

            # --------------------------------------------------
            # Активность рядом с королём соперника.
            # --------------------------------------------------

            enemy_king = board.king(
                not queen_color
            )

            if enemy_king is not None:

                queen_file = (
                    chess.square_file(
                        queen_square
                    )
                )

                queen_rank = (
                    chess.square_rank(
                        queen_square
                    )
                )

                king_file = (
                    chess.square_file(
                        enemy_king
                    )
                )

                king_rank = (
                    chess.square_rank(
                        enemy_king
                    )
                )

                king_distance = (
                    abs(
                        queen_file
                        - king_file
                    )
                    +
                    abs(
                        queen_rank
                        - king_rank
                    )
                )

                if king_distance <= 2:
                    score += 5

                elif king_distance <= 3:
                    score += 2

            return score

        # --------------------------------------------------
        # Берём несколько лучших ответов.
        #
        # Обычно played_results уже отсортирован по силе.
        # Не ограничиваемся только первым элементом:
        # Chess.com может объяснять позицию через один из
        # нескольких практически лучших ответов.
        # --------------------------------------------------

        candidates = []

        for index, result in enumerate(
            played_results[:8]
        ):

            if not isinstance(
                result,
                dict
            ):
                continue

            move_value = (
                result.get("move")
                or result.get("uci")
            )

            san_value = (
                result.get("san")
                or ""
            )

            response_move = None

            # --------------------------------------------------
            # Уже готовый chess.Move
            # --------------------------------------------------

            if isinstance(
                move_value,
                chess.Move
            ):

                response_move = move_value

            # --------------------------------------------------
            # UCI
            # --------------------------------------------------

            elif isinstance(
                move_value,
                str
            ):

                try:

                    response_move = (
                        chess.Move.from_uci(
                            move_value
                        )
                    )

                except Exception:
                    response_move = None

            # --------------------------------------------------
            # SAN
            # --------------------------------------------------

            if (
                response_move is None
                and san_value
            ):

                try:

                    response_move = (
                        board_after_played.parse_san(
                            san_value
                        )
                    )

                except Exception:
                    response_move = None

            if response_move is None:
                continue

            if (
                response_move
                not in board_after_played.legal_moves
            ):
                continue

            piece = (
                board_after_played.piece_at(
                    response_move.from_square
                )
            )

            if not piece:
                continue

            if piece.color != opponent_color:
                continue

            if (
                piece.piece_type
                != chess.QUEEN
            ):
                continue

            # --------------------------------------------------
            # Взятие объясняется материальными детекторами.
            # --------------------------------------------------

            try:

                if board_after_played.is_capture(
                    response_move
                ):
                    continue

            except Exception:
                continue

            # --------------------------------------------------
            # Шах объясняется через check.
            # --------------------------------------------------

            try:

                if board_after_played.gives_check(
                    response_move
                ):
                    continue

            except Exception:
                continue

            candidates.append(
                (
                    index,
                    result,
                    response_move,
                    piece
                )
            )

        if not candidates:
            return None

        # --------------------------------------------------
        # Проверяем каждый кандидат.
        # --------------------------------------------------

        best_candidate = None

        for (
            index,
            result,
            response_move,
            queen_piece
        ) in candidates:

            queen_from = (
                response_move.from_square
            )

            queen_to = (
                response_move.to_square
            )

            # --------------------------------------------------
            # Ферзь должен существовать и до, и после
            # хода пользователя.
            # --------------------------------------------------

            before_queen = (
                position_before.piece_at(
                    queen_from
                )
            )

            after_queen = (
                board_after_played.piece_at(
                    queen_from
                )
            )

            if (
                not before_queen
                or before_queen.piece_type
                != chess.QUEEN
                or before_queen.color
                != opponent_color
            ):
                continue

            if (
                not after_queen
                or after_queen.piece_type
                != chess.QUEEN
                or after_queen.color
                != opponent_color
            ):
                continue

            # --------------------------------------------------
            # Был ли этот ход возможен ДО нашего хода?
            # --------------------------------------------------

            was_legal_before = False

            try:

                was_legal_before = (
                    response_move
                    in position_before.legal_moves
                )

            except Exception:
                pass

            # --------------------------------------------------
            # Активность ферзя ДО нашего хода.
            #
            # Если ход уже был легален, оцениваем положение
            # ферзя на исходном поле.
            # --------------------------------------------------

            before_activity = (
                queen_activity_score(
                    position_before,
                    queen_from,
                    opponent_color
                )
            )

            # --------------------------------------------------
            # Делаем ответ ферзём.
            # --------------------------------------------------

            queen_board = (
                board_after_played.copy()
            )

            try:

                queen_board.push(
                    response_move
                )

            except Exception:

                continue

            # --------------------------------------------------
            # Активность ферзя ПОСЛЕ ответа.
            # --------------------------------------------------

            after_activity = (
                queen_activity_score(
                    queen_board,
                    queen_to,
                    opponent_color
                )
            )

            activity_gain = (
                after_activity
                - before_activity
            )

            # --------------------------------------------------
            # Сильный сигнал №1:
            #
            # ход ферзём стал возможен только после нашего
            # хода.
            # --------------------------------------------------

            newly_enabled = (
                not was_legal_before
            )

            # --------------------------------------------------
            # Сильный сигнал №2:
            #
            # ферзь получает заметный прирост активности.
            # --------------------------------------------------

            significantly_more_active = (
                activity_gain >= 5
            )

            # --------------------------------------------------
            # Сильный сигнал №3:
            #
            # ферзь получает атаку на ценную фигуру.
            # --------------------------------------------------

            attacks_valuable_piece = False

            try:

                queen_attacks = queen_board.attacks(
                    queen_to
                )

                for square in queen_attacks:

                    target = (
                        queen_board.piece_at(
                            square
                        )
                    )

                    if not target:
                        continue

                    if target.color == opponent_color:
                        continue

                    if target.piece_type in {
                        chess.KNIGHT,
                        chess.BISHOP,
                        chess.ROOK,
                        chess.QUEEN,
                    }:

                        attacks_valuable_piece = True
                        break

            except Exception:
                attacks_valuable_piece = False

            # --------------------------------------------------
            # Не считаем активизацию только по мобильности.
            #
            # Для обычного хода уже существовавшего маршрута
            # требуется либо заметный рост активности,
            # либо новая атака на ценную фигуру.
            # --------------------------------------------------

            if (
                not newly_enabled
                and not significantly_more_active
                and not attacks_valuable_piece
            ):
                continue

            # --------------------------------------------------
            # Формируем итоговую силу кандидата.
            #
            # Чем ближе ответ к началу played_results,
            # тем он сильнее.
            # --------------------------------------------------

            candidate_score = 0

            if newly_enabled:
                candidate_score += 10

            if significantly_more_active:
                candidate_score += (
                    min(
                        activity_gain,
                        15
                    )
                )

            if attacks_valuable_piece:
                candidate_score += 6

            candidate_score += max(
                0,
                8 - index
            )

            candidate = {
                "move": response_move,
                "san": (
                    san_value
                    or board_after_played.san(
                        response_move
                    )
                ),
                "from_square": queen_from,
                "to_square": queen_to,
                "from_name": (
                    board_after_played.square_name(
                        queen_from
                    )
                ),
                "to_name": (
                    board_after_played.square_name(
                        queen_to
                    )
                ),
                "was_legal_before": was_legal_before,
                "newly_enabled": newly_enabled,
                "before_activity": before_activity,
                "after_activity": after_activity,
                "activity_gain": activity_gain,
                "attacks_valuable_piece":
                    attacks_valuable_piece,
                "result": result,
                "candidate_score": candidate_score,
            }

            if (
                best_candidate is None
                or candidate_score
                > best_candidate.get(
                    "candidate_score",
                    -999
                )
            ):

                best_candidate = candidate

        if best_candidate is None:
            return None

        # --------------------------------------------------
        # Финальная защита от слишком слабых срабатываний.
        #
        # Если ход не был новым и прирост активности
        # небольшой — не говорим пользователю про
        # "активизацию ферзя".
        # --------------------------------------------------

        if (
            not best_candidate["newly_enabled"]
            and best_candidate["activity_gain"] < 5
            and not best_candidate[
                "attacks_valuable_piece"
            ]
        ):
            return None

        return best_candidate

    except Exception as e:

        print(
            "DETECT QUEEN ACTIVITY ERROR:",
            repr(e)
        )

        return None

def detect_open_file_rook_idea(
    board_before,
    best_move,
    played_move
):
    """
    Определяет позиционную идею:
    лучший ход — поставить ладью на открытую вертикаль.

    Например:
        Ra8-c8

    если на вертикали c нет пешек ни одного цвета.

    Возвращает информацию для explanation engine
    или None, если идея не обнаружена.
    """

    if board_before is None:
        return None

    if best_move is None:
        return None

    if played_move is None:
        return None

    try:

        # ==================================================
        # 1. Проверяем, что лучший ход действительно
        #    выполняется ладьёй
        # ==================================================

        best_piece = board_before.piece_at(
            best_move.from_square
        )

        if best_piece is None:
            return None

        if best_piece.piece_type != chess.ROOK:
            return None


        # ==================================================
        # 2. Проверяем, что ладья действительно перемещается
        # ==================================================

        if (
            best_move.from_square
            == best_move.to_square
        ):
            return None


        # ==================================================
        # 3. Определяем вертикаль, на которую
        #    приходит ладья
        # ==================================================

        destination_file = chess.square_file(
            best_move.to_square
        )


        # ==================================================
        # 4. Проверяем вертикаль:
        #
        #    если на ней нет пешек вообще,
        #    это открытая вертикаль.
        # ==================================================

        for rank in range(8):

            square = chess.square(
                destination_file,
                rank
            )

            piece = board_before.piece_at(
                square
            )

            if piece is None:
                continue

            if piece.piece_type == chess.PAWN:
                return None


        # ==================================================
        # 5. Если пользователь уже сыграл именно
        #    лучший ход — это не ошибка.
        # ==================================================

        if played_move == best_move:
            return None


        # ==================================================
        # 6. Получаем название вертикали
        #
        #    0 = a
        #    1 = b
        #    2 = c
        #    ...
        # ==================================================

        file_name = chr(
            ord("a") + destination_file
        )


        # ==================================================
        # 7. Получаем SAN лучшего хода
        #
        #    Например:
        #    a8c8 → Rc8
        # ==================================================

        try:

            best_move_san = board_before.san(
                best_move
            )

        except Exception:

            best_move_san = str(
                best_move
            )


        # ==================================================
        # 8. Формируем объяснение
        # ==================================================

        text = (
            "Вы упустили возможность занять "
            "открытую вертикаль ладьёй. "
            f"Ход {best_move_san} активнее использует "
            "ладью и усиливает давление по открытой линии."
        )


        # ==================================================
        # 9. Возвращаем результат
        # ==================================================

        return {
            "type": "open_file_rook",

            "file": file_name,

            "move": best_move,

            "move_san": best_move_san,

            "text": text,
        }


    except Exception as e:

        print(
            "Ошибка detect_open_file_rook_idea:",
            e
        )

        return None

def detect_neutralized_opponent_plan(mistake):

    print("\n========== ПРОВЕРКА НЕЙТРАЛИЗАЦИИ ПЛАНА ==========")

    played_results = mistake.get("played_results") or []
    best_pv = mistake.get("pv") or []
    position_after = mistake.get("position_after")

    print("PLAYED RESULTS =", played_results)
    print("BEST PV =", best_pv)
    print("POSITION AFTER =", position_after)

    # ------------------------------------------------------
    # ПРОВЕРКА ДАННЫХ
    # ------------------------------------------------------

    if not played_results:
        print("!!! НЕТ PLAYED RESULTS !!!")
        return None

    if not best_pv:
        print("!!! НЕТ BEST PV !!!")
        return None

    if position_after is None:
        print("!!! НЕТ POSITION AFTER !!!")
        return None

    try:

        # --------------------------------------------------
        # ЛУЧШИЙ ОТВЕТ СОПЕРНИКА ПОСЛЕ СЫГРАННОГО ХОДА
        # --------------------------------------------------

        first_result = played_results[0]

        print("FIRST RESULT =", first_result)

        played_pv = first_result.get("pv") or []

        print("PLAYED PV =", played_pv)

        if not played_pv:
            print("!!! PLAYED PV ПУСТОЙ !!!")
            return None

        plan_move = played_pv[0]

        print("PLAN MOVE =", plan_move)

        if not isinstance(plan_move, chess.Move):
            print("!!! PLAN MOVE НЕ chess.Move !!!")
            return None

        # --------------------------------------------------
        # ОТВЕТ СОПЕРНИКА ПОСЛЕ ЛУЧШЕГО ХОДА
        # --------------------------------------------------

        if len(best_pv) < 2:
            print("!!! BEST PV СЛИШКОМ КОРОТКИЙ !!!")
            return None

        best_reply = best_pv[1]

        print("BEST REPLY =", best_reply)

        if not isinstance(best_reply, chess.Move):
            print("!!! BEST REPLY НЕ chess.Move !!!")
            return None

        # --------------------------------------------------
        # СРАВНИВАЕМ ПЕРВЫЕ ОТВЕТЫ
        # --------------------------------------------------

        if plan_move == best_reply:
            print(
                "!!! ПЛАН СОПЕРНИКА И ПОСЛЕ ЛУЧШЕГО ХОДА "
                "ОСТАЁТСЯ ПЕРВЫМ ОТВЕТОМ !!!"
            )
            return None

        print(
            "ПЛАН ПОСЛЕ СЫГРАННОГО ХОДА =",
            plan_move
        )

        print(
            "ОТВЕТ ПОСЛЕ ЛУЧШЕГО ХОДА =",
            best_reply
        )

        # --------------------------------------------------
        # ПРОВЕРЯЕМ ФИГУРУ НА ПОЛЕ ОТКУДА ИДЁТ ПЛАН
        # --------------------------------------------------

        piece = position_after.piece_at(
            plan_move.from_square
        )

        print("PLAN PIECE =", piece)

        if piece is None:
            print(
                "!!! НА ИСХОДНОМ ПОЛЕ PLAN MOVE НЕТ ФИГУРЫ !!!"
            )
            return None

        # --------------------------------------------------
        # НАС ИНТЕРЕСУЮТ ПЕШЕЧНЫЕ ПЛАНЫ
        # --------------------------------------------------

        if piece.piece_type != chess.PAWN:
            print(
                "!!! ПЛАН НЕ ПЕШЕЧНЫЙ !!!"
            )
            return None

        print("ПЛАН ЯВЛЯЕТСЯ ХОДОМ ПЕШКИ")

        # --------------------------------------------------
        # НЕ ДОЛЖНО БЫТЬ ВЗЯТИЯ
        # --------------------------------------------------

        if position_after.is_capture(plan_move):
            print(
                "!!! ПЕШЕЧНЫЙ ХОД ЯВЛЯЕТСЯ ВЗЯТИЕМ !!!"
            )
            return None

        print("ПЕШКА ДВИЖЕТСЯ БЕЗ ВЗЯТИЯ")

        # --------------------------------------------------
        # ПРОВЕРЯЕМ, ЧТО ПЕШКА ДВИГАЕТСЯ ПРЯМО
        # --------------------------------------------------

        from_file = chess.square_file(
            plan_move.from_square
        )

        to_file = chess.square_file(
            plan_move.to_square
        )

        from_rank = chess.square_rank(
            plan_move.from_square
        )

        to_rank = chess.square_rank(
            plan_move.to_square
        )

        print("FROM FILE =", from_file)
        print("TO FILE =", to_file)
        print("FROM RANK =", from_rank)
        print("TO RANK =", to_rank)

        if from_file != to_file:
            print(
                "!!! ПЕШКА ИДЁТ ПО ДИАГОНАЛИ !!!"
            )
            return None

        # --------------------------------------------------
        # НАПРАВЛЕНИЕ ПЕШКИ
        # --------------------------------------------------

        direction = (
            1
            if piece.color == chess.WHITE
            else -1
        )

        rank_difference = to_rank - from_rank

        print("DIRECTION =", direction)
        print("RANK DIFFERENCE =", rank_difference)

        if (
            rank_difference != direction
            and
            rank_difference != 2 * direction
        ):
            print(
                "!!! ЭТО НЕ ОБЫЧНОЕ ПРОДВИЖЕНИЕ ПЕШКИ !!!"
            )
            return None

        print("ПРОДВИЖЕНИЕ ПЕШКИ ПОДХОДИТ")

        # --------------------------------------------------
        # ПОЛУЧАЕМ SAN
        # --------------------------------------------------

        try:

            plan_san = position_after.san(
                plan_move
            )

        except Exception as e:

            print(
                "!!! ОШИБКА ПОЛУЧЕНИЯ SAN !!!",
                e
            )

            return None

        print("PLAN SAN =", plan_san)

        # --------------------------------------------------
        # ИЩЕМ ТОТ ЖЕ ПЛАН В BEST PV
        #
        # Например:
        #
        # h4
        # Ne4
        # Rac8
        # c4
        # ...
        # g5
        #
        # Если g5 появляется значительно позже,
        # это означает, что h4 мог отложить этот план.
        # --------------------------------------------------

        best_plan_index = None

        print(
            "\n--- ПОИСК ПЛАНА В BEST PV ---"
        )

        for index, move in enumerate(
            best_pv[1:10],
            start=1
        ):

            print(
                f"BEST PV MOVE {index} = {move}"
            )

            if (
                isinstance(move, chess.Move)
                and
                move == plan_move
            ):

                best_plan_index = index

                print(
                    "!!! НАШЛИ ТОТ ЖЕ ПЛАН НА ПОЗИЦИИ =",
                    index
                )

                break

        print(
            "BEST PLAN INDEX =",
            best_plan_index
        )

        # --------------------------------------------------
        # ЕСЛИ ПОСЛЕ ЛУЧШЕГО ХОДА ПЛАН ТОЖЕ ЯВЛЯЕТСЯ
        # ПЕРВЫМ ОТВЕТОМ — НЕЙТРАЛИЗАЦИИ НЕТ
        # --------------------------------------------------

        if best_plan_index == 1:

            print(
                "!!! ПЛАН НЕ НЕЙТРАЛИЗОВАН: "
                "ОН ОСТАЁТСЯ ПЕРВЫМ ОТВЕТОМ !!!"
            )

            return None

        # --------------------------------------------------
        # ОПРЕДЕЛЯЕМ ФЛАНГ
        # --------------------------------------------------

        file_name = chess.square_file(
            plan_move.to_square
        )

        if file_name >= chess.FILE_NAMES.index("f"):

            wing = "королевском фланге"

        elif file_name <= chess.FILE_NAMES.index("c"):

            wing = "ферзевом фланге"

        else:

            wing = "в центре"

        print("WING =", wing)

        # --------------------------------------------------
        # ПРОВЕРЯЕМ, ЧТО ЭТО ДЕЙСТВИТЕЛЬНО ГЛАВНЫЙ
        # ОТВЕТ ПОСЛЕ СЫГРАННОГО ХОДА
        # --------------------------------------------------

        multipv_number = first_result.get(
            "multipv"
        )

        print(
            "MULTIPV NUMBER =",
            multipv_number
        )

        if multipv_number != 1:

            print(
                "!!! ЭТО НЕ ПЕРВАЯ ЛИНИЯ MULTIPV !!!"
            )

            return None

        # --------------------------------------------------
        # ФОРМИРУЕМ НАЗВАНИЕ ПЛАНА
        # --------------------------------------------------

        opponent_prefix = (
            "..."
            if piece.color == chess.BLACK
            else ""
        )

        plan_text = (
            f"{opponent_prefix}{plan_san}"
        )

        print(
            "PLAN TEXT =",
            plan_text
        )

        # --------------------------------------------------
        # ФОРМИРУЕМ ОБЪЯСНЕНИЕ
        # --------------------------------------------------

        best_move_text = mistake.get(
            "best",
            ""
        )

        text = (
            f"Лучше было {best_move_text}: "
            f"этот ход заранее ограничивает план соперника "
            f"{plan_text}, поэтому ему приходится сначала "
            f"решать другие задачи, прежде чем проводить это продвижение."
        )

        print(
            "\n!!! НЕЙТРАЛИЗОВАННЫЙ ПЛАН НАЙДЕН !!!"
        )

        print(
            "BEST MOVE =",
            best_move_text
        )

        print(
            "PLAN =",
            plan_text
        )

        print(
            "WING =",
            wing
        )

        print(
            "TEXT =",
            text
        )

        print(
            "=================================================="
        )

        return {
            "plan_move": plan_move,
            "plan_san": plan_san,
            "text": text,
            "wing": wing,
        }

    except Exception as e:

        print(
            "!!! ОШИБКА В detect_neutralized_opponent_plan !!!"
        )

        print(
            "ERROR =",
            repr(e)
        )

        return None

def find_attacked_piece_after_move(
    board_before,
    board_after,
    our_color
):

    if not board_before or not board_after:
        return None

    info = find_newly_attacked_piece_info(
        board_before,
        board_after,
        our_color
    )

    if info:
        return info

    pawn_threat = find_pawn_attack_threat(
        board_before,
        board_after,
        our_color
    )

    if pawn_threat:
        return {
            "piece_name": pawn_threat.get(
                "piece_name"
            ),
            "piece_type": pawn_threat.get(
                "piece_type"
            ),
            "square": pawn_threat.get(
                "target_square"
            ),
            "attacker_type": chess.PAWN,
            "attacker_square": pawn_threat.get(
                "attacker_square"
            ),
            "pawn_move": pawn_threat.get(
                "pawn_move"
            ),
            "is_pawn_threat": True,
        }

    return None


# ==========================================================
# СТАРАЯ ФУНКЦИЯ
# ==========================================================

def find_attacked_piece(
    board_after,
    our_color
):

    if not board_after:
        return None

    try:

        piece_order = [
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ]

        for piece_type in piece_order:

            for square in board_after.pieces(
                piece_type,
                our_color
            ):

                attackers = (
                    board_after.attackers(
                        not our_color,
                        square
                    )
                )

                if attackers:

                    return (
                        piece_name(
                            board_after.piece_at(
                                square
                            )
                        ),
                        square
                    )

        return None

    except Exception:

        return None

def get_apparent_piece_loss_text(
    info,
    best
):

    if not info:
        return ""

    captured_piece_name = (
        info.get(
            "captured_piece_name"
        )
    )

    opponent_san = (
        info.get(
            "opponent_san"
        )
    )

    recapture_san = (
        info.get(
            "recapture_san"
        )
    )

    attacker_piece_name = (
        info.get(
            "attacker_piece_name"
        )
    )

    if (
        not captured_piece_name
        or not opponent_san
        or not recapture_san
    ):
        return ""

    if attacker_piece_name:

        return (
            f"Соперник может сыграть {opponent_san} "
            f"и забрать вашего {captured_piece_name}, "
            f"но после {recapture_san} вы забираете "
            f"{attacker_piece_name}. Поэтому это "
            f"не чистая потеря {captured_piece_name}, "
            f"а размен. Проблема в том, что такой "
            f"размен всё равно оставляет позицию "
            f"значительно хуже, чем после {best}."
        )

    return (
        f"Соперник может забрать вашего "
        f"{captured_piece_name}, но после "
        f"{recapture_san} вы можете ответить "
        f"взятием. Поэтому это не чистая потеря "
        f"фигуры, а размен. При этом позиция "
        f"остаётся значительно хуже, чем после "
        f"{best}."
    )

# ==========================================================
# НОВАЯ АТАКА НА ФИГУРУ
# ==========================================================


def detect_forced_piece_loss_after_pawn_tempo(mistake):
    """
    Ищет конкретную потерю фигуры после пешечного темпового удара.

    Пример:

        Ng4 h5
        Nh6+ gxh6

    Где:
        pv[0] = h5
        pv[1] = Nh6+
        pv[2] = gxh6

    То есть соперник сначала атакует нашу фигуру пешкой,
    после чего фигура уходит и затем теряется.
    """

    if not mistake:
        return None

    played_results = (
        mistake.get("played_results")
        or []
    )

    if not played_results:
        print("FORCED PIECE LOSS: played_results отсутствует")
        return None

    position_before = mistake.get(
        "position_before"
    )

    if not position_before:
        return None

    try:

        # ==================================================
        # Получаем сыгранный ход
        # ==================================================

        played_san = (
            mistake.get("played_san")
            or ""
        )

        if not played_san:
            return None

        board_after_played = (
            position_before.copy()
        )

        played_move = (
            board_after_played.parse_san(
                played_san
            )
        )

        board_after_played.push(
            played_move
        )

        our_color = (
            position_before.turn
        )

        # ==================================================
        # Берём главный PV ответа соперника
        # ==================================================

        first_result = (
            played_results[0]
        )

        pv = (
            first_result.get("pv")
            or []
        )

        if len(pv) < 3:
            print(
                "FORCED PIECE LOSS: PV слишком короткий:",
                pv
            )
            return None

        opponent_move = pv[0]
        our_reply = pv[1]
        opponent_capture = pv[2]

        if not isinstance(
            opponent_move,
            chess.Move
        ):
            return None

        if not isinstance(
            our_reply,
            chess.Move
        ):
            return None

        if not isinstance(
            opponent_capture,
            chess.Move
        ):
            return None

        # ==================================================
        # Ход соперника должен быть легальным
        # ==================================================

        if (
            opponent_move
            not in board_after_played.legal_moves
        ):
            print(
                "FORCED PIECE LOSS: ход соперника нелегален:",
                opponent_move
            )
            return None

        # ==================================================
        # Первый ход должен быть пешечным
        # ==================================================

        pawn = (
            board_after_played.piece_at(
                opponent_move.from_square
            )
        )

        if not pawn:
            return None

        if pawn.piece_type != chess.PAWN:
            return None

        if pawn.color == our_color:
            return None

        # ==================================================
        # SAN пешечного хода
        # ==================================================

        try:

            pawn_san = (
                board_after_played.san(
                    opponent_move
                )
            )

        except Exception:

            pawn_san = ""

        # ==================================================
        # Позиция после пешечного удара
        # ==================================================

        board_after_opponent = (
            board_after_played.copy()
        )

        board_after_opponent.push(
            opponent_move
        )

        # ==================================================
        # Наша фигура, которая должна попасть под удар
        # ==================================================

        moving_piece = (
            board_after_opponent.piece_at(
                our_reply.from_square
            )
        )

        if not moving_piece:
            print(
                "FORCED PIECE LOSS: на исходной клетке "
                "ответного хода нет фигуры"
            )
            return None

        if moving_piece.color != our_color:
            return None

        # Нас интересуют именно фигуры
        if moving_piece.piece_type in (
            chess.PAWN,
            chess.KING,
        ):
            return None

        # ==================================================
        # Пешка должна атаковать эту фигуру
        # ==================================================

        pawn_square = (
            opponent_move.to_square
        )

        pawn_attacks = (
            board_after_opponent.attacks(
                pawn_square
            )
        )

        if (
            our_reply.from_square
            not in pawn_attacks
        ):
            print(
                "FORCED PIECE LOSS: пешка не атакует фигуру"
            )
            return None

        # ==================================================
        # Наш ответ должен быть легальным
        # ==================================================

        if (
            our_reply
            not in board_after_opponent.legal_moves
        ):
            print(
                "FORCED PIECE LOSS: наш ответ нелегален:",
                our_reply
            )
            return None

        # Фигура должна действительно уйти
        if (
            our_reply.from_square
            == our_reply.to_square
        ):
            return None

        # ==================================================
        # SAN нашего ответа
        # ==================================================

        try:

            reply_san = (
                board_after_opponent.san(
                    our_reply
                )
            )

        except Exception:

            reply_san = ""

        # ==================================================
        # Позиция после нашего отхода
        # ==================================================

        board_after_reply = (
            board_after_opponent.copy()
        )

        board_after_reply.push(
            our_reply
        )

        # ==================================================
        # ВАЖНО:
        # Теперь проверяем третий ход именно в этой позиции.
        # ==================================================

        if (
            opponent_capture
            not in board_after_reply.legal_moves
        ):
            print(
                "FORCED PIECE LOSS: взятие нелегально "
                "ПОСЛЕ нашего ответа:",
                opponent_capture
            )
            return None

        # ==================================================
        # Третий ход должен быть взятием
        # ==================================================

        if not board_after_reply.is_capture(
            opponent_capture
        ):
            print(
                "FORCED PIECE LOSS: третий ход не является взятием"
            )
            return None

        # ==================================================
        # Он должен забирать именно нашу фигуру
        # ==================================================

        if (
            opponent_capture.to_square
            != our_reply.to_square
        ):
            print(
                "FORCED PIECE LOSS: взятие происходит "
                "не на клетке нашей фигуры"
            )
            return None

        captured_piece = (
            board_after_reply.piece_at(
                opponent_capture.to_square
            )
        )

        if not captured_piece:
            print(
                "FORCED PIECE LOSS: на клетке взятия "
                "нет фигуры"
            )
            return None

        if (
            captured_piece.color
            != our_color
        ):
            return None

        if (
            captured_piece.piece_type
            != moving_piece.piece_type
        ):
            return None

        # ==================================================
        # SAN взятия
        # ==================================================

        try:

            capture_san = (
                board_after_reply.san(
                    opponent_capture
                )
            )

        except Exception:

            capture_san = ""

        # ==================================================
        # Название фигуры
        # ==================================================

        piece_name = (
            PIECE_NAMES.get(
                moving_piece.piece_type,
                "фигуру"
            )
        )

        destination_square = (
            chess.square_name(
                our_reply.to_square
            )
        )

        # ==================================================
        # Формируем объяснение
        # ==================================================

        if (
            pawn_san
            and reply_san
            and capture_san
        ):

            text = (
                f"Вы позволили сопернику выиграть "
                f"{piece_name}: после {pawn_san} "
                f"фигура оказывается под ударом, "
                f"а в варианте {reply_san} "
                f"{capture_san} она теряется."
            )

        else:

            text = (
                f"Вы позволили сопернику выиграть "
                f"{piece_name}: после пешечного удара "
                f"фигура оказывается под ударом и "
                f"затем теряется."
            )

        print(
            "!!! FORCED PIECE LOSS НАЙДЕН !!!"
        )
        print(
            "PAWN MOVE =",
            pawn_san
        )
        print(
            "OUR REPLY =",
            reply_san
        )
        print(
            "CAPTURE =",
            capture_san
        )
        print(
            "PIECE =",
            piece_name
        )
        print(
            "TEXT =",
            text
        )

        return {
            "text": text,
            "piece": moving_piece,
            "piece_type": moving_piece.piece_type,
            "piece_square": our_reply.to_square,
            "pawn_move": opponent_move,
            "pawn_san": pawn_san,
            "reply_move": our_reply,
            "reply_san": reply_san,
            "capture_move": opponent_capture,
            "capture_san": capture_san,
        }

    except Exception as e:

        print(
            "FORCED PIECE LOSS DETECTOR ERROR:",
            repr(e)
        )

        return None

def king_is_in_check(
    board,
    color
):

    if not board:
        return False

    try:

        king_square = board.king(
            color
        )

        if king_square is None:
            return False

        return bool(
            board.attackers(
                not color,
                king_square
            )
        )

    except Exception:

        return False


# ==========================================================
# АКТИВНОСТЬ ФЕРЗЯ
# ==========================================================

def detect_active_queen_move(
    board,
    best_move
):

    if not board or not best_move:
        return False

    try:

        piece = board.piece_at(
            best_move.from_square
        )

        if not piece:
            return False

        if piece.piece_type != chess.QUEEN:
            return False

        if board.is_capture(best_move):
            return False

        if board.is_castling(best_move):
            return False

        board_after = make_position_after(
            board,
            best_move
        )

        if not board_after:
            return False

        before_attacks = set(
            board.attacks(
                best_move.from_square
            )
        )

        after_attacks = set(
            board_after.attacks(
                best_move.to_square
            )
        )

        before_activity = len(
            before_attacks
        )

        after_activity = len(
            after_attacks
        )

        before_file = chess.square_file(
            best_move.from_square
        )

        before_rank = chess.square_rank(
            best_move.from_square
        )

        after_file = chess.square_file(
            best_move.to_square
        )

        after_rank = chess.square_rank(
            best_move.to_square
        )

        before_center_distance = (
            abs(before_file - 3.5)
            + abs(before_rank - 3.5)
        )

        after_center_distance = (
            abs(after_file - 3.5)
            + abs(after_rank - 3.5)
        )

        before_center_control = len(
            before_attacks
            & CENTER_SQUARES
        )

        after_center_control = len(
            after_attacks
            & CENTER_SQUARES
        )

        if after_activity > before_activity:

            return True

        if (
            after_center_distance
            < before_center_distance
        ):

            return True

        if (
            after_center_control
            > before_center_control
        ):

            return True

        return False

    except Exception as e:

        print(
            "Ошибка detect_active_queen_move:",
            e
        )

        return False

def square_lies_between(
    from_square,
    to_square,
    target_square
):

    from_file = chess.square_file(
        from_square
    )

    from_rank = chess.square_rank(
        from_square
    )

    to_file = chess.square_file(
        to_square
    )

    to_rank = chess.square_rank(
        to_square
    )

    target_file = chess.square_file(
        target_square
    )

    target_rank = chess.square_rank(
        target_square
    )

    dx = to_file - from_file
    dy = to_rank - from_rank

    if not (
        dx == 0
        or dy == 0
        or abs(dx) == abs(dy)
    ):
        return False

    if dx == 0:

        if target_file != from_file:
            return False

        return (
            min(
                from_rank,
                to_rank
            )
            <
            target_rank
            <
            max(
                from_rank,
                to_rank
            )
        )

    if dy == 0:

        if target_rank != from_rank:
            return False

        return (
            min(
                from_file,
                to_file
            )
            <
            target_file
            <
            max(
                from_file,
                to_file
            )
        )

    if (
        abs(
            target_file - from_file
        )
        !=
        abs(
            target_rank - from_rank
        )
    ):
        return False

    return (
        min(
            from_file,
            to_file
        )
        <
        target_file
        <
        max(
            from_file,
            to_file
        )
        and
        min(
            from_rank,
            to_rank
        )
        <
        target_rank
        <
        max(
            from_rank,
            to_rank
        )
    )


def detect_clearance_followup_idea(
    board,
    best_move
):

    if not board or not best_move:
        return None

    try:

        moving_piece = board.piece_at(
            best_move.from_square
        )

        if not moving_piece:
            return None

        if moving_piece.piece_type in (
            chess.PAWN,
            chess.KING,
        ):
            return None

        board_after = board.copy()

        board_after.push(
            best_move
        )

        freed_square = best_move.from_square

        if board_after.piece_at(
            freed_square
        ):
            return None

        our_color = moving_piece.color

        for queen_square, queen in board_after.piece_map().items():

            if queen.color != our_color:
                continue

            if queen.piece_type != chess.QUEEN:
                continue

            for followup_move in board_after.legal_moves:

                if followup_move.from_square != queen_square:
                    continue

                from_file = chess.square_file(
                    followup_move.from_square
                )

                from_rank = chess.square_rank(
                    followup_move.from_square
                )

                to_file = chess.square_file(
                    followup_move.to_square
                )

                to_rank = chess.square_rank(
                    followup_move.to_square
                )

                same_file = (
                    from_file == to_file
                )

                same_rank = (
                    from_rank == to_rank
                )

                same_diagonal = (
                    abs(from_file - to_file)
                    ==
                    abs(from_rank - to_rank)
                )

                if not (
                    same_file
                    or same_rank
                    or same_diagonal
                ):
                    continue

                if to_file > from_file:
                    file_step = 1
                elif to_file < from_file:
                    file_step = -1
                else:
                    file_step = 0

                if to_rank > from_rank:
                    rank_step = 1
                elif to_rank < from_rank:
                    rank_step = -1
                else:
                    rank_step = 0

                current_file = (
                    from_file + file_step
                )

                current_rank = (
                    from_rank + rank_step
                )

                path_squares = []

                while (
                    current_file != to_file
                    or current_rank != to_rank
                ):

                    path_square = chess.square(
                        current_file,
                        current_rank
                    )

                    path_squares.append(
                        path_square
                    )

                    current_file += file_step
                    current_rank += rank_step

                if freed_square not in path_squares:
                    continue

                try:

                    if followup_move in board.legal_moves:
                        continue

                except Exception:

                    continue

                try:

                    followup_san = (
                        board_after.san(
                            followup_move
                        )
                    )

                except Exception:

                    continue

                if not followup_san:
                    continue

                followup_after = (
                    board_after.copy()
                )

                followup_after.push(
                    followup_move
                )

                activity = False

                if followup_after.is_check():

                    activity = True

                captured_piece = (
                    board_after.piece_at(
                        followup_move.to_square
                    )
                )

                if (
                    captured_piece
                    and captured_piece.color
                    != our_color
                ):

                    activity = True

                for target_square in (
                    followup_after.attacks(
                        followup_move.to_square
                    )
                ):

                    target_piece = (
                        followup_after.piece_at(
                            target_square
                        )
                    )

                    if not target_piece:
                        continue

                    if target_piece.color == our_color:
                        continue

                    if target_piece.piece_type == chess.KING:
                        continue

                    activity = True
                    break

                target_file = chess.square_file(
                    followup_move.to_square
                )

                target_rank = chess.square_rank(
                    followup_move.to_square
                )

                center_distance = (
                    abs(target_file - 3.5)
                    +
                    abs(target_rank - 3.5)
                )

                if center_distance <= 3:
                    activity = True

                if not activity:
                    continue

                print(
                    "CLEARANCE FOUND:",
                    "BEST MOVE =",
                    board.san(best_move),
                    "| FREED =",
                    chess.square_name(
                        freed_square
                    ),
                    "| FOLLOWUP =",
                    followup_san
                )

                return {
                    "freed_square": freed_square,

                    "freed_square_name":
                        chess.square_name(
                            freed_square
                        ),

                    "followup_move":
                        followup_move,

                    "followup_san":
                        followup_san,

                    "followup_piece":
                        queen,
                }

        return None

    except Exception as e:

        print(
            "Ошибка detect_clearance_followup_idea:",
            e
        )

        return None

def detect_newly_undefended_pawn(
    position_before,
    board_after_played,
    played_move
):
    """
    Ищет пешку нашей стороны, которая:

    1. была защищена до нашего хода;
    2. после нашего хода больше не имеет защитников;
    3. после нашего хода соперник реально может
       атаковать/взять эту пешку.

    Возвращает информацию о пешке или None.
    """

    if (
        not position_before
        or not board_after_played
        or not played_move
    ):
        return None

    try:

        our_color = board_after_played.turn != position_before.turn

        candidate_pawns = []

        for square in chess.SQUARES:

            piece_after = board_after_played.piece_at(square)

            if not piece_after:
                continue

            if piece_after.color != our_color:
                continue

            if piece_after.piece_type != chess.PAWN:
                continue

            # --------------------------------------------------
            # Была ли пешка защищена ДО нашего хода?
            # --------------------------------------------------

            defenders_before = []

            for attacker_square in position_before.attackers(
                our_color,
                square
            ):

                attacker = position_before.piece_at(
                    attacker_square
                )

                if not attacker:
                    continue

                # Саму пешку не считаем защитником
                if attacker_square == square:
                    continue

                defenders_before.append(
                    attacker_square
                )

            if not defenders_before:
                continue

            # --------------------------------------------------
            # Есть ли защитники ПОСЛЕ нашего хода?
            # --------------------------------------------------

            defenders_after = []

            for attacker_square in board_after_played.attackers(
                our_color,
                square
            ):

                attacker = board_after_played.piece_at(
                    attacker_square
                )

                if not attacker:
                    continue

                if attacker_square == square:
                    continue

                defenders_after.append(
                    attacker_square
                )

            # Если защита сохранилась — это не наш случай
            if defenders_after:
                continue

            # --------------------------------------------------
            # Может ли соперник реально взять эту пешку?
            # --------------------------------------------------

            opponent_can_capture = False
            capture_san = ""

            for opponent_move in board_after_played.legal_moves:

                if opponent_move.to_square != square:
                    continue

                target = board_after_played.piece_at(
                    square
                )

                if not target:
                    continue

                if target.color == board_after_played.turn:
                    continue

                try:
                    capture_san = board_after_played.san(
                        opponent_move
                    )
                except Exception:
                    capture_san = ""

                opponent_can_capture = True
                break

            if not opponent_can_capture:
                continue

            candidate_pawns.append({
                "square": square,
                "piece": piece_after,
                "capture_san": capture_san,
            })

        if not candidate_pawns:
            return None

        # Если таких пешек несколько, берём первую.
        return candidate_pawns[0]

    except Exception as e:

        print(
            "NEWLY UNDEFENDED PAWN ERROR:",
            e
        )

        return None

def get_clearance_followup_text(
    clearance_info
):

    if not clearance_info:
        return ""

    freed_square_name = (
        clearance_info.get(
            "freed_square_name"
        )
    )

    followup_san = (
        clearance_info.get(
            "followup_san"
        )
    )

    followup_piece = (
        clearance_info.get(
            "followup_piece"
        )
    )

    if (
        not freed_square_name
        or not followup_san
        or not followup_piece
    ):
        return ""

    if followup_piece.piece_type == chess.QUEEN:

        return (
            f"ход освобождает поле "
            f"{freed_square_name} для ферзя "
            f"и создаёт возможность "
            f"активного {followup_san}."
        )

    return (
        f"ход освобождает поле "
        f"{freed_square_name} и создаёт "
        f"возможность активного "
        f"{followup_san}."
    )


def generate_best_move_idea(
    position_before,
    best_move_obj,
    best
):

    if (
        not position_before
        or not best_move_obj
        or not best
    ):
        return ""

    try:

        board = position_before

        if detect_mate(
            board,
            best_move_obj
        ):

            return (
                "этот ход сразу ставит мат."
            )

        if detect_check(
            board,
            best_move_obj
        ):

            return (
                "этот ход создаёт шах и заставляет "
                "соперника немедленно реагировать."
            )

        trade_info = (
            detect_equal_trade_info(
                board,
                best_move_obj
            )
        )

        if trade_info:

            trade_text = (
                get_equal_trade_text(
                    trade_info
                )
            )

            if trade_text:

                return (
                    f"этот ход позволяет {trade_text}"
                )

        clearance_info = (
            detect_clearance_followup_idea(
                board,
                best_move_obj
            )
        )

        if clearance_info:

            clearance_text = (
                get_clearance_followup_text(
                    clearance_info
                )
            )

            if clearance_text:

                return clearance_text

        if detect_center_pawn_move(
            board,
            best_move_obj
        ):

            return (
                "это пешечный удар по центру, "
                "который позволяет оспорить "
                "пространство соперника."
            )

        if detect_castling(
            board,
            best_move_obj
        ):

            return (
                "рокировка улучшает безопасность "
                "короля и помогает подключить ладью."
            )

        captured_name = detect_material_gain(
            board,
            best_move_obj
        )

        if captured_name:

            return (
                f"этот ход позволяет взять "
                f"{captured_name}."
            )

        if best_move_obj.promotion:

            return (
                "пешка превращается в новую фигуру."
            )

        if detect_active_queen_move(
            board,
            best_move_obj
        ):

            return (
                "этот ход позволяет переместить "
                "ферзя на более активную позицию."
            )

        return ""

    except Exception as e:

        print(
            "Ошибка generate_best_move_idea:",
            e
        )

        return ""


# ==========================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ==========================================================

# ==========================================================
# АНАЛИЗ ПОСЛЕДСТВИЙ ХОДА
#
# Эта функция НИЧЕГО НЕ РЕШАЕТ за пользователя.
#
# Она только собирает все обнаруженные последствия
# сыгранного хода в единый список events.
#
# Далее отдельная функция сможет выбрать главное
# событие и второстепенные события.
# ==========================================================

def analyze_move_consequences(mistake):

    if not mistake:
        return []

    events = []

    # ======================================================
    # ИСХОДНЫЕ ДАННЫЕ
    # ======================================================

    position_before = mistake.get(
        "position_before"
    )

    played = mistake.get(
        "played_san",
        ""
    )

    best = mistake.get(
        "best",
        ""
    )

    loss = mistake.get(
        "loss",
        0
    )

    features = (
        mistake.get(
            "features"
        )
        or {}
    )

    if not position_before:
        return events

    try:
        loss = float(loss)
    except Exception:
        loss = 0

    # ======================================================
    # ХОДЫ
    # ======================================================

    played_move = None

    if played:

        try:

            played_move = (
                position_before.parse_san(
                    played
                )
            )

        except Exception:

            played_move = None

    best_move = get_best_move(
        mistake,
        position_before
    )

    board_after_played = None

    if played_move:

        board_after_played = (
            make_position_after(
                position_before,
                played_move
            )
        )

    # ======================================================
    # ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
    #
    # Чтобы все события имели одинаковую структуру.
    # ======================================================

    def add_event(
        event_type,
        severity,
        text="",
        **data
    ):

        event = {
            "type": event_type,
            "severity": severity,
            "text": text,
        }

        if data:
            event.update(data)

        events.append(
            event
        )

    # ======================================================
    # 1. МАТ
    #
    # Это самое сильное тактическое событие.
    # ======================================================

    if (
        best_move
        and detect_mate(
            position_before,
            best_move
        )
    ):

        add_event(
            "mate",
            100,
            (
                f"лучший ход {best} "
                "сразу ставит мат"
            ),
            best_move=best_move,
            best=best,
        )

    # ======================================================
    # 2. ШАХ ЛУЧШИМ ХОДОМ
    # ======================================================

    if (
        best_move
        and detect_check(
            position_before,
            best_move
        )
    ):

        add_event(
            "check",
            95,
            (
                f"лучший ход {best} "
                "создаёт шах"
            ),
            best_move=best_move,
            best=best,
        )

    # ======================================================
    # 3. ВЫИГРЫШ МАТЕРИАЛА ЛУЧШИМ ХОДОМ
    # ======================================================

    if best_move:

        captured_name = (
            detect_material_gain(
                position_before,
                best_move
            )
        )

        if captured_name:

            add_event(
                "material_gain",
                90,
                (
                    f"ход {best} "
                    f"позволяет взять {captured_name}"
                ),
                best_move=best_move,
                best=best,
                captured_piece_name=captured_name,
            )

    # ======================================================
    # 4. СВЯЗКА → ВЫИГРЫШ МАТЕРИАЛА
    # ======================================================

    pin_material_info = None

    if (
        played_move
        and board_after_played
    ):

        try:

            pin_material_info = (
                detect_pin_material_loss(
                    position_before,
                    board_after_played,
                    played_move,
                    loss
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES PIN ERROR:",
                e
            )

    if pin_material_info:

        pin_text = ""

        try:

            pin_text = (
                get_pin_material_loss_text(
                    pin_material_info,
                    played
                )
            )

        except Exception:

            pin_text = ""

        add_event(
            "pin_material_loss",
            88,
            pin_text,
            info=pin_material_info,
        )

    # ======================================================
    # 5. КАЖУЩАЯСЯ ПОТЕРЯ ФИГУРЫ → РАЗМЕН
    # ======================================================

    apparent_piece_loss_info = None

    if (
        played_move
        and best_move
    ):

        try:

            apparent_piece_loss_info = (
                detect_apparent_piece_loss_but_recapturable(
                    position_before,
                    played_move,
                    best_move,
                    loss
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES APPARENT LOSS ERROR:",
                e
            )

    if apparent_piece_loss_info:

        apparent_text = ""

        try:

            apparent_text = (
                get_apparent_piece_loss_text(
                    apparent_piece_loss_info,
                    best
                )
            )

        except Exception:

            apparent_text = ""

        add_event(
            "apparent_piece_loss",
            82,
            apparent_text,
            info=apparent_piece_loss_info,
        )

    # ======================================================
    # 6. НОВАЯ НЕЗАЩИЩЁННАЯ ПЕШКА
    # ======================================================

    newly_undefended_pawn = None

    if (
        played_move
        and board_after_played
    ):

        try:

            newly_undefended_pawn = (
                detect_newly_undefended_pawn(
                    position_before,
                    board_after_played,
                    played_move
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES UNDEFENDED PAWN ERROR:",
                e
            )

    if newly_undefended_pawn:

        pawn_square = (
            newly_undefended_pawn.get(
                "square"
            )
        )

        capture_san = (
            newly_undefended_pawn.get(
                "capture_san"
            )
            or ""
        )

        square_name = ""

        if pawn_square is not None:

            square_name = chess.square_name(
                pawn_square
            )

        if capture_san:

            text = (
                f"после {played} пешка "
                f"на {square_name} осталась "
                f"без защиты, и соперник может "
                f"взять её ходом {capture_san}"
            )

        else:

            text = (
                f"после {played} пешка "
                f"на {square_name} осталась "
                "без защиты"
            )

        add_event(
            "undefended_pawn",
            78,
            text,
            info=newly_undefended_pawn,
        )

    # ======================================================
    # 7. НОВАЯ АТАКА НА ФИГУРУ
    # ======================================================

    newly_attacked_info = None

    if board_after_played:

        our_color = (
            not board_after_played.turn
        )

        try:

            newly_attacked_info = (
                find_newly_attacked_piece_info(
                    position_before,
                    board_after_played,
                    our_color
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES NEW ATTACK ERROR:",
                e
            )

    if newly_attacked_info:

        attacked_piece_name = (
            newly_attacked_info.get(
                "piece_name"
            )
        )

        attacked_square = (
            newly_attacked_info.get(
                "square"
            )
        )

        attacker_type = (
            newly_attacked_info.get(
                "attacker_type"
            )
        )

        square_name = ""

        if attacked_square is not None:

            square_name = chess.square_name(
                attacked_square
            )

        if attacker_type == chess.PAWN:

            text = (
                f"соперник получает новую "
                f"атаку на {attacked_piece_name} "
                "пешкой"
            )

            event_type = "pawn_piece_attack"
            severity = 65

        else:

            text = (
                f"соперник получает новую "
                f"атаку на {attacked_piece_name} "
                f"на поле {square_name}"
            )

            event_type = "piece_attack"
            severity = 55

        add_event(
            event_type,
            severity,
            text,
            info=newly_attacked_info,
        )

    # ======================================================
    # 8. ПЕШЕЧНАЯ УГРОЗА
    #
    # Отдельно проверяем угрозу следующего хода,
    # потому что пешка может ещё НЕ атаковать фигуру
    # прямо сейчас.
    # ======================================================

    pawn_attack_threat = None

    if board_after_played:

        our_color = (
            not board_after_played.turn
        )

        try:

            pawn_attack_threat = (
                find_pawn_attack_threat(
                    position_before,
                    board_after_played,
                    our_color
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES PAWN THREAT ERROR:",
                e
            )

    if pawn_attack_threat:

        attacked_piece_name = (
            pawn_attack_threat.get(
                "piece_name"
            )
        )

        target_square = (
            pawn_attack_threat.get(
                "target_square"
            )
        )

        pawn_move = (
            pawn_attack_threat.get(
                "pawn_move"
            )
        )

        pawn_move_san = ""

        if pawn_move:

            try:

                pawn_move_san = (
                    board_after_played.san(
                        pawn_move
                    )
                )

            except Exception:

                pawn_move_san = ""

        square_name = ""

        if target_square is not None:

            square_name = chess.square_name(
                target_square
            )

        if pawn_move_san:

            text = (
                f"соперник может следующим "
                f"ходом {pawn_move_san} "
                f"атаковать {attacked_piece_name} "
                f"на {square_name} пешкой"
            )

        else:

            text = (
                f"соперник получает пешечную "
                f"угрозу против {attacked_piece_name}"
            )

        add_event(
            "pawn_tempo",
            72,
            text,
            info=pawn_attack_threat,
        )

    # ======================================================
    # 9. ТЕМП НА ФЕРЗЯ
    # ======================================================

    queen_tempo = None

    if board_after_played:

        try:

            queen_tempo = find_queen_tempo(
                position_before,
                board_after_played,
                played_move
            )

        except Exception as e:

            print(
                "CONSEQUENCES QUEEN TEMPO ERROR:",
                e
            )

    if queen_tempo:

        queen_square = (
            queen_tempo.get(
                "queen_square"
            )
        )

        opponent_san = (
            queen_tempo.get(
                "san"
            )
            or ""
        )

        queen_square_name = ""

        if queen_square is not None:

            queen_square_name = (
                chess.square_name(
                    queen_square
                )
            )

        if opponent_san:

            text = (
                f"соперник может сыграть "
                f"{opponent_san} и атаковать "
                f"ферзя с темпом"
            )

        else:

            text = (
                "соперник получает возможность "
                "атаковать ферзя с темпом"
            )

        add_event(
            "queen_tempo",
            80,
            text,
            info=queen_tempo,
            queen_square=queen_square_name,
        )

    # ======================================================
    # 10. НОВЫЙ ШАХ СОПЕРНИКА
    # ======================================================

    new_check_threat = None

    if board_after_played:

        try:

            opponent_color = (
                board_after_played.turn
            )

            candidate_checks = []

            for opponent_move in (
                board_after_played.legal_moves
            ):

                try:

                    attacker = (
                        board_after_played.piece_at(
                            opponent_move.from_square
                        )
                    )

                    if not attacker:
                        continue

                    if attacker.color != opponent_color:
                        continue

                    if not board_after_played.gives_check(
                        opponent_move
                    ):
                        continue

                    check_board = (
                        board_after_played.copy()
                    )

                    check_board.push(
                        opponent_move
                    )

                    if not check_board.is_check():
                        continue

                    try:

                        check_san = (
                            board_after_played.san(
                                opponent_move
                            )
                        )

                    except Exception:

                        check_san = ""

                    candidate_checks.append(
                        (
                            opponent_move,
                            attacker,
                            check_san
                        )
                    )

                except Exception:

                    continue

            piece_priority = {
                chess.QUEEN: 5,
                chess.ROOK: 4,
                chess.BISHOP: 3,
                chess.KNIGHT: 2,
                chess.PAWN: 1,
            }

            candidate_checks.sort(
                key=lambda item:
                piece_priority.get(
                    item[1].piece_type,
                    0
                ),
                reverse=True
            )

            if candidate_checks:

                selected_move = (
                    candidate_checks[0][0]
                )

                selected_piece = (
                    candidate_checks[0][1]
                )

                selected_san = (
                    candidate_checks[0][2]
                )

                new_check_threat = {
                    "move": selected_move,
                    "piece": selected_piece,
                    "san": selected_san,
                }

        except Exception as e:

            print(
                "CONSEQUENCES NEW CHECK ERROR:",
                e
            )

    if new_check_threat:

        check_san = (
            new_check_threat.get(
                "san"
            )
            or ""
        )

        if check_san:

            text = (
                f"соперник получает новый "
                f"шах {check_san}"
            )

        else:

            text = (
                "соперник получает новый шах"
            )

        add_event(
            "new_check",
            85,
            text,
            info=new_check_threat,
        )

    # ======================================================
    # 11. РАВНОЦЕННЫЙ РАЗМЕН ЛУЧШИМ ХОДОМ
    # ======================================================

    equal_trade_info = None

    if best_move:

        try:

            equal_trade_info = (
                detect_equal_trade_info(
                    position_before,
                    best_move
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES EQUAL TRADE ERROR:",
                e
            )

    if equal_trade_info:

        trade_text = ""

        try:

            trade_text = (
                get_equal_trade_text(
                    equal_trade_info
                )
            )

        except Exception:

            trade_text = ""

        if trade_text:

            text = (
                f"лучший ход {best} "
                f"позволяет {trade_text}"
            )

        else:

            text = (
                f"лучший ход {best} "
                "позволяет предложить "
                "равноценный размен"
            )

        add_event(
            "equal_trade",
            45,
            text,
            info=equal_trade_info,
        )

    # ======================================================
    # 12. ПЕШЕЧНАЯ СТРУКТУРА
    # ======================================================

    pawn_structure_info = None

    if best_move:

        try:

            pawn_structure_info = (
                detect_pawn_structure_damage(
                    position_before,
                    best_move
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES PAWN STRUCTURE ERROR:",
                e
            )

    if pawn_structure_info:

        pawn_structure_text = ""

        try:

            pawn_structure_text = (
                get_pawn_structure_text(
                    pawn_structure_info,
                    best
                )
            )

        except Exception:

            pawn_structure_text = ""

        add_event(
            "pawn_structure",
            35,
            pawn_structure_text,
            info=pawn_structure_info,
        )

    # ======================================================
    # 13. ВЗЯТИЕ МАТЕРИАЛА С ПОТЕРЕЙ ТЕМПА
    # ======================================================

    tempo_material_loss = None

    if (
        played_move
        and best_move
        and best
    ):

        try:

            tempo_material_loss = (
                detect_tempo_material_loss(
                    position_before,
                    played_move,
                    best_move,
                    best
                )
            )

        except Exception as e:

            print(
                "CONSEQUENCES TEMPO MATERIAL ERROR:",
                e
            )

    if tempo_material_loss:

        add_event(
            "tempo_material_loss",
            83,
            str(
                tempo_material_loss
            ),
            info=tempo_material_loss,
        )

    # ======================================================
    # 14. ИДЕЯ ЛУЧШЕГО ХОДА
    #
    # Это не обязательно причина ошибки.
    # Поэтому severity ниже конкретных тактических
    # последствий.
    # ======================================================

    best_idea = ""

    if best_move and best:

        try:

            best_idea = (
                generate_best_move_idea(
                    position_before,
                    best_move,
                    best
                )
                or ""
            )

        except Exception as e:

            print(
                "CONSEQUENCES BEST IDEA ERROR:",
                e
            )

    if best_idea:

        add_event(
            "best_move_idea",
            30,
            best_idea,
            best_move=best_move,
            best=best,
        )

    # ======================================================
    # 15. ЦЕНТР
    # ======================================================

    if (
        best_move
        and detect_center_pawn_move(
            position_before,
            best_move
        )
    ):

        add_event(
            "center",
            32,
            (
                f"лучший ход {best} "
                "позволяет ударить по центру"
            ),
            best_move=best_move,
            best=best,
        )

    # ======================================================
    # 16. РОКИРОВКА
    # ======================================================

    if (
        best_move
        and detect_castling(
            position_before,
            best_move
        )
    ):

        add_event(
            "king_safety",
            40,
            (
                f"лучший ход {best} "
                "улучшает безопасность короля"
            ),
            best_move=best_move,
            best=best,
        )

    # ======================================================
    # 17. FREE PAWN ИЗ FEATURES
    # ======================================================

    free_pawn = (
        mistake.get(
            "free_pawn_explanation"
        )
        or features.get(
            "free_pawn_explanation"
        )
    )

    if free_pawn:

        add_event(
            "free_pawn",
            60,
            str(
                free_pawn
            ),
        )

    # ======================================================
    # 18. ПЛОХОЙ РАЗМЕН ИЗ FEATURES
    # ======================================================

    bad_recapture = (
        mistake.get(
            "bad_recapture_explanation"
        )
        or features.get(
            "bad_recapture_explanation"
        )
    )

    if bad_recapture:

        add_event(
            "bad_recapture",
            60,
            str(
                bad_recapture
            ),
        )

    # ======================================================
    # 19. ПЕШЕЧНАЯ УГРОЗА ИЗ FEATURES
    # ======================================================

    pawn_threat_explanation = (
        mistake.get(
            "pawn_threat_explanation"
        )
        or features.get(
            "pawn_threat_explanation"
        )
    )

    if pawn_threat_explanation:

        add_event(
            "pawn_attack",
            55,
            str(
                pawn_threat_explanation
            ),
        )

    # ======================================================
    # 20. СТАРАЯ ИНФОРМАЦИЯ О ВИЛКЕ
    #
    # Здесь пока только обнаруживаем её.
    # Выбор главной причины будет позже.
    # ======================================================

    if best_move:

        try:

            best_piece = (
                position_before.piece_at(
                    best_move.from_square
                )
            )

            if (
                best_piece
                and best_piece.piece_type
                == chess.KNIGHT
            ):

                board_after_best = (
                    position_before.copy()
                )

                board_after_best.push(
                    best_move
                )

                fork_targets = []

                for square in board_after_best.attacks(
                    best_move.to_square
                ):

                    target_piece = (
                        board_after_best.piece_at(
                            square
                        )
                    )

                    if (
                        target_piece
                        and target_piece.color
                        != best_piece.color
                        and target_piece.piece_type
                        not in (
                            chess.PAWN,
                            chess.KING,
                        )
                    ):

                        fork_targets.append(
                            (
                                target_piece,
                                square
                            )
                        )

                if len(fork_targets) >= 2:

                    piece_values = {
                        chess.QUEEN: 9,
                        chess.ROOK: 5,
                        chess.BISHOP: 3,
                        chess.KNIGHT: 3,
                    }

                    fork_targets.sort(
                        key=lambda item:
                        piece_values.get(
                            item[0].piece_type,
                            0
                        ),
                        reverse=True
                    )

                    first_piece, first_square = (
                        fork_targets[0]
                    )

                    second_piece, second_square = (
                        fork_targets[1]
                    )

                    first_name = PIECE_NAMES.get(
                        first_piece.piece_type,
                        "фигуру"
                    )

                    second_name = PIECE_NAMES.get(
                        second_piece.piece_type,
                        "фигуру"
                    )

                    first_square_name = (
                        chess.square_name(
                            first_square
                        )
                    )

                    second_square_name = (
                        chess.square_name(
                            second_square
                        )
                    )

                    fork_text = (
                        f"лучший ход {best} "
                        f"создаёт вилку: конь "
                        f"атакует {first_name} "
                        f"на {first_square_name} "
                        f"и {second_name} "
                        f"на {second_square_name}"
                    )

                    add_event(
                        "fork",
                        75,
                        fork_text,
                        best_move=best_move,
                        best=best,
                        targets=fork_targets,
                    )

        except Exception as e:

            print(
                "CONSEQUENCES FORK ERROR:",
                e
            )

    # ======================================================
    # 21. СОРТИРОВКА
    #
    # Пока мы ничего не выбираем.
    #
    # Просто возвращаем события от более серьёзных
    # к менее серьёзным.
    # ======================================================

    events.sort(
        key=lambda event:
        event.get(
            "severity",
            0
        ),
        reverse=True
    )

    return events

def find_piece_tempo_attack(
    board_after,
    played_move,
    played_results,
    our_color
):
    """
    Проверяет, атакует ли первый ответ соперника
    фигуру, которую мы только что передвинули.

    Пример:

        Qe3 Nd5

    После Qe3:
        - ферзь находится на e3
        - лучший ответ соперника Nd5
        - Nd5 атакует ферзя на e3

    Возвращает информацию о такой атаке.
    """

    if (
        board_after is None
        or played_move is None
        or not played_results
    ):
        return None

    try:

        # --------------------------------------------------
        # Фигура, которую мы только что передвинули
        # --------------------------------------------------

        attacked_square = played_move.to_square

        our_piece = board_after.piece_at(
            attacked_square
        )

        if not our_piece:
            return None

        # Короля здесь не рассматриваем.
        # Шах имеет собственную систему объяснений.
        if our_piece.piece_type == chess.KING:
            return None

        if our_piece.color != our_color:
            return None

        # --------------------------------------------------
        # Первый ответ соперника из PV
        # --------------------------------------------------

        first_result = played_results[0]

        pv = first_result.get("pv")

        if not pv:
            return None

        opponent_move = pv[0]

        if opponent_move not in board_after.legal_moves:
            return None

        # --------------------------------------------------
        # Проверяем, действительно ли ход соперника
        # атакует нашу фигуру
        # --------------------------------------------------

        attacker_piece = board_after.piece_at(
            opponent_move.from_square
        )

        if not attacker_piece:
            return None

        if attacker_piece.color == our_color:
            return None

        # Позиция после ответа соперника
        board_reply = board_after.copy()

        try:

            board_reply.push(
                opponent_move
            )

        except Exception:

            return None

        # После ответа соперника наша фигура
        # должна находиться под атакой.
        if not board_reply.is_attacked_by(
            not our_color,
            attacked_square
        ):
            return None

        # --------------------------------------------------
        # Важно:
        # убеждаемся, что именно сыгравшая фигура
        # соперника атакует нашу фигуру.
        #
        # Это убирает часть ложных срабатываний,
        # когда наша фигура стала атакована побочно.
        # --------------------------------------------------

        direct_attack = False

        try:

            attacker_attacks = board_reply.attacks(
                opponent_move.to_square
            )

            if attacked_square in attacker_attacks:
                direct_attack = True

        except Exception:
            direct_attack = False

        if not direct_attack:
            return None

        # --------------------------------------------------
        # SAN ответа соперника
        # --------------------------------------------------

        try:

            opponent_move_san = (
                board_after.san(
                    opponent_move
                )
            )

        except Exception:

            opponent_move_san = (
                opponent_move.uci()
            )

        # --------------------------------------------------
        # Название фигуры
        # --------------------------------------------------

        piece_name = PIECE_NAMES.get(
            our_piece.piece_type,
            "фигуру"
        )

        piece_square_name = (
            chess.square_name(
                attacked_square
            )
        )

        attacker_name = PIECE_NAMES.get(
            attacker_piece.piece_type,
            "фигурой"
        )

        return {
            "piece_tempo_attack": True,

            "queen_tempo": (
                our_piece.piece_type
                == chess.QUEEN
            ),

            "attacked_piece": piece_name,

            "attacked_piece_type":
                our_piece.piece_type,

            "attacked_square":
                attacked_square,

            "attacked_square_name":
                piece_square_name,

            "attacker_piece":
                attacker_name,

            "attacker_piece_type":
                attacker_piece.piece_type,

            "attacker_square":
                opponent_move.to_square,

            "opponent_move":
                opponent_move_san,

            "opponent_move_uci":
                opponent_move.uci(),

            "text": (
                f"После вашего хода соперник может "
                f"сыграть {opponent_move_san} с темпом, "
                f"атакуя вашего {piece_name} "
                f"на {piece_square_name}."
            ),
        }

    except Exception as e:

        print(
            "PIECE TEMPO ATTACK ERROR:",
            e
        )

        return None

# ==========================================================
# СОЗДАНИЕ НОВОЙ ИЗОЛИРОВАННОЙ ПЕШКИ
# ==========================================================


def detect_isolated_pawn_after_move(
    board_before,
    board_after,
    played_move,
    best_move=None,
):
    """
    Определяет, создаёт ли сыгранный ход НОВУЮ изолированную
    пешку и позволяет ли лучший ход избежать этой структуры.

    Изолированная пешка — пешка, у которой нет своих пешек
    на соседних вертикалях.

    Важно:
    - проверяется именно изменение структуры после хода;
    - уже существующая изолированная пешка не считается ошибкой;
    - для главного объяснения особенно полезен случай, когда
      пользователь забирает пешку пешкой, а лучший ход забирает
      ту же пешку фигурой.
    """

    if (
        board_before is None
        or board_after is None
        or played_move is None
    ):
        return None

    try:

        # --------------------------------------------------
        # Пешка, которая должна стать изолированной
        # --------------------------------------------------

        played_piece = board_after.piece_at(
            played_move.to_square
        )

        if not played_piece:
            return None

        if played_piece.piece_type != chess.PAWN:
            return None

        our_color = played_piece.color
        pawn_square = played_move.to_square
        pawn_file = chess.square_file(pawn_square)
        pawn_rank = chess.square_rank(pawn_square)

        # --------------------------------------------------
        # Есть ли наша пешка на конкретной вертикали?
        # --------------------------------------------------

        def has_pawn_on_file(
            board,
            file_index,
            color
        ):

            if file_index < 0 or file_index > 7:
                return False

            for rank in range(8):

                square = chess.square(
                    file_index,
                    rank
                )

                piece = board.piece_at(square)

                if (
                    piece
                    and piece.color == color
                    and piece.piece_type == chess.PAWN
                ):
                    return True

            return False

        left_file = pawn_file - 1
        right_file = pawn_file + 1

        # --------------------------------------------------
        # Структура ДО хода
        # --------------------------------------------------

        before_has_left = has_pawn_on_file(
            board_before,
            left_file,
            our_color
        )

        before_has_right = has_pawn_on_file(
            board_before,
            right_file,
            our_color
        )

        was_isolated_before = (
            not before_has_left
            and not before_has_right
        )

        # Нас интересует только НОВАЯ слабость.
        if was_isolated_before:
            return None

        # --------------------------------------------------
        # Структура ПОСЛЕ хода
        # --------------------------------------------------

        after_has_left = has_pawn_on_file(
            board_after,
            left_file,
            our_color
        )

        after_has_right = has_pawn_on_file(
            board_after,
            right_file,
            our_color
        )

        is_isolated_after = (
            not after_has_left
            and not after_has_right
        )

        if not is_isolated_after:
            return None

        # --------------------------------------------------
        # Убеждаемся, что сыгранный ход действительно был
        # ходом нашей пешки.
        # --------------------------------------------------

        before_piece = board_before.piece_at(
            played_move.from_square
        )

        if (
            not before_piece
            or before_piece.piece_type != chess.PAWN
            or before_piece.color != our_color
        ):
            return None

        # --------------------------------------------------
        # SAN сыгранного хода
        # --------------------------------------------------

        try:
            played_move_san = board_before.san(
                played_move
            )
        except Exception:
            played_move_san = played_move.uci()

        # --------------------------------------------------
        # Что было взято
        # --------------------------------------------------

        was_capture = False
        captured_piece = None
        captured_piece_name = None

        try:
            was_capture = board_before.is_capture(
                played_move
            )
        except Exception:
            was_capture = False

        if was_capture:

            captured_piece = board_before.piece_at(
                played_move.to_square
            )

            if (
                captured_piece is None
                and board_before.is_en_passant(played_move)
            ):

                captured_square = (
                    played_move.to_square - 8
                    if our_color == chess.WHITE
                    else played_move.to_square + 8
                )

                captured_piece = board_before.piece_at(
                    captured_square
                )

            if captured_piece:
                captured_piece_name = PIECE_NAMES.get(
                    captured_piece.piece_type,
                    "фигуру"
                )

        # --------------------------------------------------
        # Проверяем лучший ход.
        # Нас особенно интересует случай:
        #   пользователь: bxc4
        #   лучший ход:   Nxc4
        # То есть та же пешка снимается фигурой.
        # --------------------------------------------------

        best_avoids_isolation = False
        best_move_san = None
        best_move_piece = None

        if best_move is not None:

            try:

                if best_move in board_before.legal_moves:

                    best_move_piece = board_before.piece_at(
                        best_move.from_square
                    )

                    if best_move_piece:

                        best_move_san = board_before.san(
                            best_move
                        )

                        # Лучший ход должен забирать именно
                        # ту пешку, которая после нашего хода
                        # стала бы изолированной.
                        if (
                            best_move.to_square
                            == played_move.to_square
                            and board_before.is_capture(
                                best_move
                            )
                            and best_move_piece.piece_type
                            != chess.PAWN
                        ):
                            target = board_before.piece_at(
                                played_move.to_square
                            )

                            if (
                                target
                                and target.piece_type
                                == chess.PAWN
                                and target.color
                                != our_color
                            ):
                                best_avoids_isolation = True

            except Exception:
                best_move_san = None
                best_move_piece = None

        pawn_square_name = chess.square_name(
            pawn_square
        )

        # --------------------------------------------------
        # Формируем объяснение.
        # --------------------------------------------------

        if (
            best_avoids_isolation
            and best_move_san
        ):

            if was_capture:

                text = (
                    f"Ход {played_move_san} создал "
                    f"изолированную пешку на "
                    f"{pawn_square_name}. "
                    f"Лучше было сыграть {best_move_san}: "
                    f"так вы забирали пешку соперника фигурой "
                    f"и сохраняли более здоровую пешечную структуру."
                )

            else:

                text = (
                    f"Ход {played_move_san} создал "
                    f"изолированную пешку на "
                    f"{pawn_square_name}. "
                    f"Лучше было сыграть {best_move_san}, "
                    f"избегая этой пешечной структуры."
                )

        else:

            text = (
                f"Ход {played_move_san} создал "
                f"изолированную пешку на "
                f"{pawn_square_name}."
            )

        return {
            "isolated_pawn": True,
            "pawn_square": pawn_square,
            "pawn_square_name": pawn_square_name,
            "pawn_file": pawn_file,
            "pawn_rank": pawn_rank,
            "played_move": played_move.uci(),
            "played_move_san": played_move_san,
            "was_capture": was_capture,
            "captured_piece": captured_piece_name,
            "captured_piece_type": (
                captured_piece.piece_type
                if captured_piece
                else None
            ),
            "best_move": (
                best_move.uci()
                if best_move
                else None
            ),
            "best_move_san": best_move_san,
            "best_move_piece": (
                PIECE_NAMES.get(
                    best_move_piece.piece_type
                )
                if best_move_piece
                else None
            ),
            "best_avoids_isolation": (
                best_avoids_isolation
            ),
            "text": text,
        }

    except Exception as e:

        print(
            "ISOLATED PAWN DETECTOR ERROR:",
            e
        )

        return None


# ==========================================================
# ВЫНУЖДЕННАЯ ПОТЕРЯ ФИГУРЫ
# ==========================================================


def detect_forced_piece_loss(
    board,
    played_move,
    played_results=None,
):
    """
    Определяет непосредственную потерю фигуры после сыгранного хода.

    Пример:

        Nd4 Rxd4 Bf1

    Здесь:
        - Nd4 — наш ход
        - Rxd4 — лучший ответ соперника
        - Bf1 — лучший ответ нашей стороны

    Поскольку после Rxd4 Stockfish играет Bf1,
    а не взятие ладьи, это не размен, а потеря коня.
    """

    print()
    print("==============================================")
    print("=== ВХОД В detect_forced_piece_loss() ===")
    print("==============================================")

    # ==========================================================
    # 1. ПРОВЕРКИ ВХОДНЫХ ДАННЫХ
    # ==========================================================

    print("BOARD =", board)
    print("PLAYED MOVE =", played_move)
    print("PLAYED RESULTS =", played_results)

    if board is None:
        print("FORCED LOSS EXIT: board is None")
        return None

    if played_move is None:
        print("FORCED LOSS EXIT: played_move is None")
        return None

    if not played_results:
        print("FORCED LOSS EXIT: played_results пустой")
        return None

    # ==========================================================
    # 2. СОЗДАЁМ ПОЗИЦИЮ ПОСЛЕ НАШЕГО ХОДА
    # ==========================================================

    try:

        after_played = board.copy()

        print(
            "PLAYED MOVE LEGAL =",
            played_move in after_played.legal_moves
        )

        if played_move not in after_played.legal_moves:
            print(
                "FORCED LOSS EXIT: сыгранный ход "
                "не является легальным в position_before"
            )
            return None

        played_san = after_played.san(
            played_move
        )

        print(
            "PLAYED SAN =",
            played_san
        )

        after_played.push(
            played_move
        )

    except Exception as e:

        print(
            "FORCED LOSS ERROR AFTER PLAYED:",
            repr(e)
        )

        return None

    # ==========================================================
    # 3. ФИГУРА, КОТОРУЮ МЫ ПОСТАВИЛИ
    # ==========================================================

    played_piece = after_played.piece_at(
        played_move.to_square
    )

    print(
        "PIECE AFTER PLAYED =",
        played_piece
    )

    if played_piece is None:
        print(
            "FORCED LOSS EXIT: на поле назначения "
            "нет нашей фигуры"
        )
        return None

    print(
        "PIECE TYPE =",
        played_piece.piece_type
    )

    print(
        "PIECE COLOR =",
        played_piece.color
    )

    if played_piece.piece_type in (
        chess.PAWN,
        chess.KING,
    ):

        print(
            "FORCED LOSS EXIT: это пешка или король"
        )

        return None

    our_color = played_piece.color

    # ==========================================================
    # 4. ПЕРВЫЙ ХОД PV — ЛУЧШИЙ ОТВЕТ СОПЕРНИКА
    # ==========================================================

    try:

        first_result = played_results[0]

        print(
            "FIRST RESULT =",
            first_result
        )

        pv = first_result.get(
            "pv",
            []
        )

    except Exception as e:

        print(
            "FORCED LOSS ERROR READING PV:",
            repr(e)
        )

        return None

    print(
        "PV =",
        pv
    )

    if not pv:

        print(
            "FORCED LOSS EXIT: PV пустой"
        )

        return None

    opponent_move = pv[0]

    print(
        "OPPONENT MOVE =",
        opponent_move
    )

    # ==========================================================
    # 5. ПРОВЕРЯЕМ ЛЕГАЛЬНОСТЬ ОТВЕТА
    # ==========================================================

    if opponent_move not in after_played.legal_moves:

        print(
            "FORCED LOSS EXIT: opponent_move "
            "не является легальным"
        )

        return None

    # ==========================================================
    # 6. ОТВЕТ ДОЛЖЕН БЫТЬ ВЗЯТИЕМ
    # ==========================================================

    is_capture = after_played.is_capture(
        opponent_move
    )

    print(
        "OPPONENT MOVE IS CAPTURE =",
        is_capture
    )

    if not is_capture:

        print(
            "FORCED LOSS EXIT: лучший ответ "
            "не является взятием"
        )

        return None

    # ==========================================================
    # 7. ОПРЕДЕЛЯЕМ ВЗЯТУЮ ФИГУРУ
    # ==========================================================

    captured_square = (
        opponent_move.to_square
    )

    if after_played.is_en_passant(
        opponent_move
    ):

        captured_square = (
            opponent_move.to_square
            + (
                -8
                if after_played.turn == chess.WHITE
                else 8
            )
        )

    captured_piece = after_played.piece_at(
        captured_square
    )

    print(
        "CAPTURED SQUARE =",
        chess.square_name(
            captured_square
        )
    )

    print(
        "CAPTURED PIECE =",
        captured_piece
    )

    if captured_piece is None:

        print(
            "FORCED LOSS EXIT: на поле взятия "
            "нет фигуры"
        )

        return None

    # ==========================================================
    # 8. ДОЛЖНА БЫТЬ НАША ФИГУРА
    # ==========================================================

    print(
        "CAPTURED PIECE COLOR =",
        captured_piece.color
    )

    print(
        "OUR COLOR =",
        our_color
    )

    if captured_piece.color != our_color:

        print(
            "FORCED LOSS EXIT: взята не наша фигура"
        )

        return None

    if captured_piece.piece_type in (
        chess.PAWN,
        chess.KING,
    ):

        print(
            "FORCED LOSS EXIT: взята пешка или король"
        )

        return None

    # ==========================================================
    # 9. СОПЕРНИК ДОЛЖЕН ЗАБИРАТЬ ИМЕННО ФИГУРУ,
    #    КОТОРУЮ МЫ ТОЛЬКО ЧТО ПОСТАВИЛИ
    # ==========================================================

    print(
        "PLAYED TO SQUARE =",
        chess.square_name(
            played_move.to_square
        )
    )

    print(
        "CAPTURED SQUARE =",
        chess.square_name(
            captured_square
        )
    )

    if captured_square != played_move.to_square:

        print(
            "FORCED LOSS EXIT: соперник взял "
            "не фигуру с destination сыгранного хода"
        )

        return None

    # ==========================================================
    # 10. SAN ОТВЕТА СОПЕРНИКА
    # ==========================================================

    try:

        opponent_san = after_played.san(
            opponent_move
        )

    except Exception as e:

        print(
            "FORCED LOSS ERROR SAN:",
            repr(e)
        )

        return None

    print(
        "OPPONENT SAN =",
        opponent_san
    )

    # ==========================================================
    # 11. ПОЗИЦИЯ ПОСЛЕ ВЗЯТИЯ
    # ==========================================================

    try:

        after_capture = after_played.copy()

        after_capture.push(
            opponent_move
        )

    except Exception as e:

        print(
            "FORCED LOSS ERROR AFTER CAPTURE:",
            repr(e)
        )

        return None

    # ==========================================================
    # 12. ВТОРОЙ ХОД PV — ЛУЧШИЙ ОТВЕТ НАШЕЙ СТОРОНЫ
    # ==========================================================

    best_reply = None

    if len(pv) >= 2:

        candidate_reply = pv[1]

        print(
            "PV SECOND MOVE =",
            candidate_reply
        )

        if candidate_reply in after_capture.legal_moves:

            best_reply = candidate_reply

        else:

            print(
                "PV SECOND MOVE НЕ ЛЕГАЛЕН"
            )

    print(
        "BEST REPLY =",
        best_reply
    )

    # ==========================================================
    # 13. КРИТИЧЕСКАЯ ПРОВЕРКА
    #
    # Если после Rxd4 Stockfish играет Bf1,
    # значит это НЕ размен.
    #
    # Если после Rxd4 Stockfish играет Qxd4,
    # Nxd4 и т.п. — тогда это размен.
    # ==========================================================

    normal_recap = False

    if best_reply is not None:

        print(
            "BEST REPLY TO SQUARE =",
            chess.square_name(
                best_reply.to_square
            )
        )

        print(
            "OPPONENT CAPTURE TO SQUARE =",
            chess.square_name(
                opponent_move.to_square
            )
        )

        if (
            after_capture.is_capture(
                best_reply
            )
            and
            best_reply.to_square
            == opponent_move.to_square
        ):

            normal_recap = True

    print(
        "NORMAL RECAPTURE =",
        normal_recap
    )

    if normal_recap:

        print(
            "FORCED LOSS EXIT: "
            "Stockfish действительно показывает размен"
        )

        return None

    # ==========================================================
    # 14. ЗНАЧИТ ФИГУРА ПОТЕРЯНА
    # ==========================================================

    piece_names = {
        chess.PAWN: "пешку",
        chess.KNIGHT: "коня",
        chess.BISHOP: "слона",
        chess.ROOK: "ладью",
        chess.QUEEN: "ферзя",
        chess.KING: "короля",
    }

    captured_name = piece_names.get(
        captured_piece.piece_type,
        "фигуру"
    )

    text = (
        f"После {played_san} вы оставили "
        f"{captured_name} без достаточной защиты: "
        f"соперник может сразу забрать её ходом "
        f"{opponent_san}."
    )

    print()
    print(
        "=============================================="
    )
    print(
        "!!! FORCED PIECE LOSS НАЙДЕН !!!"
    )
    print(
        "=============================================="
    )
    print(
        "PLAYED =",
        played_san
    )
    print(
        "OPPONENT =",
        opponent_san
    )
    print(
        "LOST PIECE =",
        captured_name
    )
    print(
        "BEST REPLY =",
        best_reply
    )
    print(
        "TEXT =",
        text
    )
    print(
        "=============================================="
    )

    return {
        "type": "forced_piece_loss",
        "piece": captured_name,
        "piece_type": captured_piece.piece_type,
        "square": chess.square_name(
            captured_square
        ),
        "opponent_move": opponent_move,
        "opponent_san": opponent_san,
        "best_reply": best_reply,
        "text": text,
    }

def detect_trapped_piece(
    board,
    played_results,
):
    """
    Определяет действительно запертую фигуру.

    Сценарий:

        наш ход
            ↓
        лучший ход соперника атакует нашу фигуру
            ↓
        у этой фигуры нет безопасного отхода
            ↓
        соперник реально забирает эту фигуру
        в продолжении PV

    Важный момент:

        Nb2 Qc2
        Nc3 Qxb2

    Nc3 может быть ходом ДРУГОЙ нашей фигуры.
    Поэтому нельзя считать, что атакованная фигура
    обязательно должна ходить следующим ходом.
    """

    if board is None or not played_results:
        return None

    try:

        # ==================================================
        # ПОЗИЦИЯ ПОСЛЕ НАШЕГО ОШИБОЧНОГО ХОДА
        # ==================================================

        board_after_our_move = board.copy()

        opponent_color = board_after_our_move.turn
        our_color = not opponent_color

        # ==================================================
        # ЛУЧШИЙ ОТВЕТ СОПЕРНИКА
        # ==================================================

        first_result = played_results[0]

        pv = first_result.get("pv", [])

        if not pv:
            return None

        opponent_move = pv[0]

        if not isinstance(opponent_move, chess.Move):
            return None

        if opponent_move not in board_after_our_move.legal_moves:
            return None

        opponent_san = board_after_our_move.san(
            opponent_move
        )

        # ==================================================
        # ЗАПОМИНАЕМ НАШИ ФИГУРЫ ДО ХОДА СОПЕРНИКА
        # ==================================================

        our_pieces_before = {}

        for square, piece in board_after_our_move.piece_map().items():

            if piece.color != our_color:
                continue

            if piece.piece_type in (
                chess.PAWN,
                chess.KING,
            ):
                continue

            our_pieces_before[square] = piece.piece_type

        # ==================================================
        # КАКИЕ НАШИ ФИГУРЫ АТАКОВАНЫ ДО ХОДА
        # ==================================================

        attacked_before = set()

        for square in our_pieces_before:

            if board_after_our_move.is_attacked_by(
                opponent_color,
                square
            ):
                attacked_before.add(square)

        # ==================================================
        # ДЕЛАЕМ ХОД СОПЕРНИКА
        # ==================================================

        position_after_attack = (
            board_after_our_move.copy()
        )

        position_after_attack.push(
            opponent_move
        )

        # ==================================================
        # ИЩЕМ НОВОАТАКОВАННЫЕ НАШИ ФИГУРЫ
        # ==================================================

        candidates = []

        for square, piece in position_after_attack.piece_map().items():

            if piece.color != our_color:
                continue

            if piece.piece_type in (
                chess.PAWN,
                chess.KING,
            ):
                continue

            # До хода не была атакована.
            if square in attacked_before:
                continue

            # После хода стала атакованной.
            if not position_after_attack.is_attacked_by(
                opponent_color,
                square
            ):
                continue

            candidates.append(
                (
                    square,
                    piece.piece_type
                )
            )

        if not candidates:
            return None

        # ==================================================
        # НАЗВАНИЯ ФИГУР
        # ==================================================

        piece_names = {
            chess.KNIGHT: (
                "коня",
                "коню"
            ),
            chess.BISHOP: (
                "слона",
                "слону"
            ),
            chess.ROOK: (
                "ладью",
                "ладье"
            ),
            chess.QUEEN: (
                "ферзя",
                "ферзю"
            ),
        }

        # ==================================================
        # ПРОВЕРЯЕМ КАНДИДАТОВ
        # ==================================================

        for piece_square, piece_type in candidates:

            if piece_type not in piece_names:
                continue

            piece_name, piece_dative = piece_names[
                piece_type
            ]

            square_name = chess.square_name(
                piece_square
            )

            # ==================================================
            # ИЩЕМ ЛЕГАЛЬНЫЕ ХОДЫ ЭТОЙ ФИГУРЫ
            # ==================================================

            legal_moves = []

            for move in position_after_attack.legal_moves:

                if move.from_square != piece_square:
                    continue

                legal_moves.append(
                    move
                )

            # ==================================================
            # ИЩЕМ БЕЗОПАСНЫЕ ОТХОДЫ
            # ==================================================

            safe_moves = []

            for move in legal_moves:

                test_board = (
                    position_after_attack.copy()
                )

                try:
                    test_board.push(move)
                except Exception:
                    continue

                moved_piece = test_board.piece_at(
                    move.to_square
                )

                if moved_piece is None:
                    continue

                if moved_piece.color != our_color:
                    continue

                # После хода фигура не должна
                # оставаться под атакой.
                if not test_board.is_attacked_by(
                    opponent_color,
                    move.to_square
                ):
                    safe_moves.append(
                        move
                    )

            # ==================================================
            # ЕСЛИ ЕСТЬ ХОТЯ БЫ ОДИН БЕЗОПАСНЫЙ ОТХОД —
            # ФИГУРА НЕ ЗАПЕРТА
            # ==================================================

            if safe_moves:
                continue

            # ==================================================
            # ТЕПЕРЬ ПРОВЕРЯЕМ PV.
            #
            # ВАЖНО:
            #
            # После Qc2:
            #
            #     b2 = наш конь
            #     e2 = наш другой конь
            #
            # Потом:
            #
            #     Nc3      <-- e2-c3
            #     Qxb2     <-- забирается именно b2
            #
            # Поэтому мы просто отслеживаем исходную
            # клетку piece_square, пока она не будет
            # занята/освобождена.
            # ==================================================

            pv_board = (
                board_after_our_move.copy()
            )

            piece_current_square = piece_square

            piece_still_exists = True

            pv_capture_found = False

            # --------------------------------------------------
            # Обрабатываем PV.
            #
            # Первый ход PV = Qc2
            # --------------------------------------------------

            for pv_index, pv_move in enumerate(pv):

                if pv_move not in pv_board.legal_moves:
                    break

                moving_piece = pv_board.piece_at(
                    pv_move.from_square
                )

                captured_piece = pv_board.piece_at(
                    pv_move.to_square
                )

                # ==================================================
                # Соперник забирает именно нашу фигуру
                # ==================================================

                if (
                    pv_board.turn == opponent_color
                    and captured_piece is not None
                    and captured_piece.color == our_color
                    and pv_move.to_square == piece_current_square
                ):

                    pv_capture_found = True

                    break

                # ==================================================
                # Если наша отслеживаемая фигура сама ходит,
                # переносим её текущую клетку.
                # ==================================================

                if (
                    pv_board.turn == our_color
                    and pv_move.from_square == piece_current_square
                ):

                    # Это наша отслеживаемая фигура.
                    piece_current_square = (
                        pv_move.to_square
                    )

                pv_board.push(
                    pv_move
                )

            # ==================================================
            # ЕСЛИ В PV ФИГУРА НЕ ТЕРЯЕТСЯ —
            # НЕ НАЗЫВАЕМ ЕЁ ЗАПЕРТОЙ.
            # ==================================================

            if not pv_capture_found:
                continue

            # ==================================================
            # НАСТОЯЩАЯ ЗАПЕРТАЯ ФИГУРА
            # ==================================================

            return {
                "type": "trapped_piece",

                "piece": piece_name,

                "piece_dative": piece_dative,

                "piece_type": piece_type,

                "square": square_name,

                "opponent_move": opponent_move,

                "opponent_san": opponent_san,

                "legal_moves": legal_moves,

                "safe_moves": safe_moves,

                "pv_capture_found": True,

                "text": (
                    f"Вы позволили сопернику атаковать "
                    f"запертого {piece_name}: после "
                    f"{opponent_san} {piece_dative} на "
                    f"{square_name} некуда отступать."
                ),
            }

        return None

    except Exception as e:

        print(
            "TRAPPED PIECE DETECTOR ERROR:",
            repr(e)
        )

        return None

def detect_pawn_loss(mistake):
    """
    Ищет потерю нашей пешки, которая возникает вследствие
    сыгранного хода.

    Логика:

        BEFORE
          ↓
        наш сыгранный ход
          ↓
        PV Stockfish после сыгранного хода
          ↓
        соперник забирает нашу пешку

    Затем сравниваем с PV лучшего хода:
    если соответствующая пешка в лучшем варианте не теряется,
    считаем, что сыгранный ход приводит к потере пешки.

    Возвращает dict с информацией или None.
    """

    if not mistake:
        return None

    position_before = mistake.get("position_before")

    if not position_before:
        return None

    played_san = (
        mistake.get("played_san")
        or ""
    )

    if not played_san:
        return None

    played_results = (
        mistake.get("played_results")
        or []
    )

    if not played_results:
        print(
            "PAWN LOSS: played_results отсутствует"
        )
        return None

    # --------------------------------------------------
    # Цвет нашей стороны
    # --------------------------------------------------

    our_color = position_before.turn

    # --------------------------------------------------
    # Восстанавливаем позицию после нашего хода
    # --------------------------------------------------

    try:
        board_after_played = (
            position_before.copy()
        )

        played_move = (
            board_after_played.parse_san(
                played_san
            )
        )

        board_after_played.push(
            played_move
        )

    except Exception as e:
        print(
            "PAWN LOSS: ошибка восстановления "
            "позиции после сыгранного хода:",
            repr(e)
        )
        return None

    # --------------------------------------------------
    # Берём PV сыгранного хода
    # --------------------------------------------------

    first_result = played_results[0]

    pv_played = (
        first_result.get("pv")
        or []
    )

    if not pv_played:
        print(
            "PAWN LOSS: PV после сыгранного хода отсутствует"
        )
        return None

    # --------------------------------------------------
    # Проигрываем PV после сыгранного хода
    # --------------------------------------------------

    board = board_after_played.copy()

    lost_pawn_square = None
    lost_pawn_move = None
    lost_pawn_san = None

    try:

        for move in pv_played:

            if move not in board.legal_moves:
                print(
                    "PAWN LOSS: нелегальный ход в PV:",
                    move
                )
                break

            # ------------------------------------------
            # Проверяем, является ли взятие потерей
            # НАШЕЙ пешки
            # ------------------------------------------

            if board.is_capture(move):

                captured_piece = None

                # Обычное взятие
                if not board.is_en_passant(move):
                    captured_piece = (
                        board.piece_at(
                            move.to_square
                        )
                    )

                # Взятие на проходе
                else:
                    captured_piece = (
                        board.piece_at(
                            chess.square(
                                chess.square_file(
                                    move.to_square
                                ),
                                chess.square_rank(
                                    move.from_square
                                )
                            )
                        )
                    )

                if (
                    captured_piece
                    and captured_piece.color == our_color
                    and captured_piece.piece_type == chess.PAWN
                ):
                    lost_pawn_square = (
                        move.to_square
                        if not board.is_en_passant(move)
                        else chess.square(
                            chess.square_file(
                                move.to_square
                            ),
                            chess.square_rank(
                                move.from_square
                            )
                        )
                    )

                    try:
                        lost_pawn_san = board.san(move)
                    except Exception:
                        lost_pawn_san = ""

                    lost_pawn_move = move

                    print(
                        "!!! PAWN LOSS FOUND !!!"
                    )
                    print(
                        "LOST PAWN =",
                        chess.square_name(
                            lost_pawn_square
                        )
                    )
                    print(
                        "CAPTURE MOVE =",
                        lost_pawn_san
                    )

                    break

            board.push(move)

    except Exception as e:
        print(
            "PAWN LOSS: ошибка анализа PV:",
            repr(e)
        )
        return None

    if lost_pawn_square is None:
        print(
            "PAWN LOSS: в PV после сыгранного "
            "хода потеря нашей пешки не найдена"
        )
        return None

    # --------------------------------------------------
    # Проверяем PV лучшего хода
    # --------------------------------------------------

    best_results = (
        mistake.get("best_results")
        or []
    )

    # В некоторых версиях структуры best_results
    # может отсутствовать, поэтому пробуем также
    # best_pv, если он сохранён отдельно.

    pv_best = []

    if best_results:
        try:
            pv_best = (
                best_results[0].get("pv")
                or []
            )
        except Exception:
            pv_best = []

    if not pv_best:
        pv_best = (
            mistake.get("best_pv")
            or []
        )

    # --------------------------------------------------
    # Если PV лучшего хода нет,
    # не делаем ложного вывода.
    # --------------------------------------------------

    if not pv_best:
        print(
            "PAWN LOSS: PV лучшего хода отсутствует"
        )

        # Даже без сравнения можем вернуть найденную
        # конкретную потерю, но с низкой уверенностью.
        return {
            "text": (
                "Ваш ход приводит к потере пешки."
            ),
            "pawn_square": lost_pawn_square,
            "pawn_square_name": chess.square_name(
                lost_pawn_square
            ),
            "capture_move": lost_pawn_move,
            "capture_san": lost_pawn_san,
            "verified_against_best": False,
        }

    # --------------------------------------------------
    # Проигрываем PV лучшего хода
    # --------------------------------------------------

    board_best = position_before.copy()

    pawn_lost_in_best = False
    best_pawn_capture_san = None

    try:

        for move in pv_best:

            if move not in board_best.legal_moves:
                break

            if board_best.is_capture(move):

                captured_piece = None

                if not board_best.is_en_passant(move):
                    captured_piece = (
                        board_best.piece_at(
                            move.to_square
                        )
                    )
                else:
                    captured_piece = (
                        board_best.piece_at(
                            chess.square(
                                chess.square_file(
                                    move.to_square
                                ),
                                chess.square_rank(
                                    move.from_square
                                )
                            )
                        )
                    )

                if (
                    captured_piece
                    and captured_piece.color == our_color
                    and captured_piece.piece_type == chess.PAWN
                ):

                    captured_square = (
                        move.to_square
                        if not board_best.is_en_passant(move)
                        else chess.square(
                            chess.square_file(
                                move.to_square
                            ),
                            chess.square_rank(
                                move.from_square
                            )
                        )
                    )

                    # Нам важно понять,
                    # теряется ли именно та же пешка.
                    if (
                        captured_square
                        == lost_pawn_square
                    ):
                        pawn_lost_in_best = True

                        try:
                            best_pawn_capture_san = (
                                board_best.san(move)
                            )
                        except Exception:
                            best_pawn_capture_san = ""

                        break

            board_best.push(move)

    except Exception as e:
        print(
            "PAWN LOSS: ошибка анализа BEST PV:",
            repr(e)
        )

    # --------------------------------------------------
    # Если та же пешка теряется и при лучшем ходе,
    # значит сыгранный ход не является причиной
    # именно этой потери.
    # --------------------------------------------------

    if pawn_lost_in_best:
        print(
            "PAWN LOSS: та же пешка теряется "
            "и после лучшего хода — НЕ считаем причиной"
        )

        return None

    # --------------------------------------------------
    # Формируем объяснение
    # --------------------------------------------------

    pawn_name = chess.square_name(
        lost_pawn_square
    )

    if lost_pawn_san:
        text = (
            f"Ваш ход приводит к потере пешки "
            f"на {pawn_name}: соперник может "
            f"забрать её ходом {lost_pawn_san}."
        )
    else:
        text = (
            "Ваш ход приводит к потере пешки."
        )

    print(
        "=============================================="
    )
    print(
        "!!! PAWN LOSS НАЙДЕН !!!"
    )
    print(
        "PAWN SQUARE =",
        pawn_name
    )
    print(
        "CAPTURE =",
        lost_pawn_san
    )
    print(
        "TEXT =",
        text
    )
    print(
        "=============================================="
    )

    return {
        "text": text,
        "pawn_square": lost_pawn_square,
        "pawn_square_name": pawn_name,
        "capture_move": lost_pawn_move,
        "capture_san": lost_pawn_san,
        "verified_against_best": True,
    }

def detect_inaccuracy_no_benefit(
    position_before,
    played_move,
    best_move,
    loss,
    equivalent_best_moves=None,
    best_after_score=None,
    before_score=None,
):
    """
    Небольшая позиционная неточность без конкретной
    тактической причины.

    Условия:
    - 30 <= loss < 80
    - сыгранный ход не является взятием
    - сыгранный ход не даёт шах
    - лучший ход не является взятием
    - лучший ход не даёт шах
    - лучший ход не ставит мат
    - после сыгранного хода нет немедленного мата
    - нет очевидной прямой потери фигуры
    - сыгранный ход не равноценен лучшему
    """

    if (
        position_before is None
        or played_move is None
        or best_move is None
    ):
        return None

    # ======================================================
    # 1. LOSS
    # ======================================================

    try:
        loss = float(loss)
    except Exception:
        return None

    if loss < 30 or loss >= 80:
        return None

    # ======================================================
    # 2. ЛЕГАЛЬНОСТЬ ХОДОВ
    # ======================================================

    try:
        if played_move not in position_before.legal_moves:
            return None

        if best_move not in position_before.legal_moves:
            return None

    except Exception:
        return None

    # ======================================================
    # 3. SAN СЫГРАННОГО ХОДА
    # ======================================================

    try:
        played_san = position_before.san(
            played_move
        )
    except Exception:
        played_san = ""

    # ======================================================
    # 4. SAN ЛУЧШЕГО ХОДА
    # ======================================================

    try:
        best_san = position_before.san(
            best_move
        )
    except Exception:
        best_san = ""

    # ======================================================
    # 5. ОДИН И ТОТ ЖЕ ХОД
    # ======================================================

    try:
        if played_move == best_move:
            return None
    except Exception:
        pass

    # ======================================================
    # 6. СЫГРАННЫЙ ХОД НЕ ВЗЯТИЕ
    # ======================================================

    try:
        if position_before.is_capture(
            played_move
        ):
            return None
    except Exception:
        return None

    # ======================================================
    # 7. СЫГРАННЫЙ ХОД НЕ ШАХ
    # ======================================================

    try:
        if position_before.gives_check(
            played_move
        ):
            return None
    except Exception:
        return None

    # ======================================================
    # 8. ЛУЧШИЙ ХОД НЕ ВЗЯТИЕ
    # ======================================================

    try:
        if position_before.is_capture(
            best_move
        ):
            return None
    except Exception:
        return None

    # ======================================================
    # 9. ЛУЧШИЙ ХОД НЕ ШАХ
    # ======================================================

    try:
        if position_before.gives_check(
            best_move
        ):
            return None
    except Exception:
        return None

    # ======================================================
    # 10. ЛУЧШИЙ ХОД НЕ СТАВИТ МАТ
    # ======================================================

    try:

        best_board = position_before.copy()

        best_board.push(best_move)

        if best_board.is_checkmate():
            return None

    except Exception:
        return None

    # ======================================================
    # 11. ПОСЛЕ СЫГРАННОГО ХОДА НЕ ДОЛЖНО БЫТЬ
    #     МАТА В ОДИН
    # ======================================================

    try:

        played_board = position_before.copy()

        played_board.push(played_move)

        for enemy_move in played_board.legal_moves:

            if not played_board.gives_check(
                enemy_move
            ):
                continue

            test_board = played_board.copy()

            test_board.push(enemy_move)

            if test_board.is_checkmate():
                return None

    except Exception:
        return None

    # ======================================================
    # 12. ПОСЛЕ СЫГРАННОГО ХОДА НЕ ДОЛЖНО БЫТЬ
    #     ПРОСТОЙ ПРЯМОЙ ПОТЕРИ ФИГУРЫ
    #
    # Это только дополнительный предохранитель.
    # Более сложные случаи уже должны ловиться
    # существующими детекторами.
    # ======================================================

    try:

        our_color = played_board.turn
        opponent_color = not our_color

        for enemy_move in played_board.legal_moves:

            if not played_board.is_capture(
                enemy_move
            ):
                continue

            captured_piece = played_board.piece_at(
                enemy_move.to_square
            )

            attacker_piece = played_board.piece_at(
                enemy_move.from_square
            )

            if not captured_piece:
                continue

            if not attacker_piece:
                continue

            if captured_piece.color != our_color:
                continue

            if attacker_piece.color != opponent_color:
                continue

            # Соперник может непосредственно взять
            # нашу фигуру — значит это уже конкретная
            # материальная причина.
            return None

    except Exception:
        return None

    # ======================================================
    # 13. ПРОВЕРКА РАВНОЦЕННЫХ ХОДОВ
    # ======================================================

    equivalent_best_moves = (
        equivalent_best_moves
        or []
    )

    equivalent_sans = set()

    for item in equivalent_best_moves:

        if isinstance(item, dict):

            san = (
                item.get("san")
                or ""
            ).strip()

            if san:
                equivalent_sans.add(san)

        elif isinstance(item, str):

            san = item.strip()

            if san:
                equivalent_sans.add(san)

    # Если сыгранный ход уже считается равноценным,
    # это не "неточность без пользы".
    if (
        played_san
        and played_san in equivalent_sans
    ):
        return None

    # ======================================================
    # 14. ПРОВЕРКА, ЧТО BEST ДЕЙСТВИТЕЛЬНО ЛУЧШЕ
    #
    # Если есть оценка после лучшего хода, используем её.
    # ======================================================

    if (
        best_after_score is not None
        and before_score is not None
    ):

        try:

            best_after_score = float(
                best_after_score
            )

            before_score = float(
                before_score
            )

            improvement = (
                best_after_score
                - before_score
            )

            # Лучший ход должен хотя бы немного
            # улучшать оценку позиции.
            if improvement < 5:
                return None

        except Exception:
            pass

    # ======================================================
    # 15. БЛИЗКИЕ АЛЬТЕРНАТИВЫ
    # ======================================================

    alternative_count = 0

    for san in equivalent_sans:

        if not san:
            continue

        if san == played_san:
            continue

        if san == best_san:
            continue

        alternative_count += 1

    # ======================================================
    # 16. ФОРМИРУЕМ ОБЪЯСНЕНИЕ
    # ======================================================

    if alternative_count > 0:

        text = (
            f"Ход {played_san} был допустим, "
            f"но {best_san} позволял получить "
            "более благоприятную позицию. "
            "При этом были и другие близкие "
            "по силе продолжения."
        )

    else:

        text = (
            f"Ход {played_san} был допустим, "
            f"но {best_san} был немного точнее "
            "и позволял улучшить позицию. "
            "Здесь не было непосредственной "
            "тактической потери."
        )

    return {
        "text": text,
        "played_move": played_move,
        "best_move": best_move,
        "loss": loss,
        "has_close_alternatives": (
            alternative_count > 0
        ),
        "alternative_count": alternative_count,
    }
def detect_delayed_capture(
    board_before,
    played_move,
    best_move
):
    """
    Определяет ситуацию, когда игрок слишком рано забрал материал:

        played_move = взятие
        best_move   = полезный невзятие

    После best_move взятая фигура и наша атакующая фигура
    всё ещё сохраняются, и после возможного ответа соперника
    первоначальное взятие остаётся возможным.

    Пример:

        Nxc2?! вместо h6!

        h6 Nb1 Nxc2

    В этом случае функция сообщает:

        "Вы слишком рано забрали ладью. Сначала стоило сыграть h6.
        После этого взятие ладьи всё ещё оставалось возможным
        ходом Nxc2."
    """

    print("==============================================")
    print("=== ВХОД В detect_delayed_capture() ===")
    print("==============================================")

    if board_before is None:
        print("DELAYED CAPTURE: board_before = None")
        return None

    if played_move is None:
        print("DELAYED CAPTURE: played_move = None")
        return None

    if best_move is None:
        print("DELAYED CAPTURE: best_move = None")
        return None

    try:

        # ------------------------------------------------------
        # 1. Проверяем легальность ходов в исходной позиции
        # ------------------------------------------------------

        if played_move not in board_before.legal_moves:
            print("DELAYED CAPTURE: сыгранный ход нелегален")
            return None

        if best_move not in board_before.legal_moves:
            print("DELAYED CAPTURE: лучший ход нелегален")
            return None

        # ------------------------------------------------------
        # 2. Сыгранный ход ОБЯЗАТЕЛЬНО должен быть взятием
        # ------------------------------------------------------

        if not board_before.is_capture(played_move):
            print("DELAYED CAPTURE: сыгранный ход не является взятием")
            return None

        # ------------------------------------------------------
        # 3. Лучший ход НЕ должен быть взятием
        # ------------------------------------------------------

        if board_before.is_capture(best_move):
            print("DELAYED CAPTURE: лучший ход является взятием")
            return None

        # ------------------------------------------------------
        # 4. Получаем фигуру, которой мы ходим
        # ------------------------------------------------------

        played_piece = board_before.piece_at(
            played_move.from_square
        )

        if played_piece is None:
            print("DELAYED CAPTURE: не найдена сыгранная фигура")
            return None

        # Только наша фигура
        if played_piece.color != board_before.turn:
            print("DELAYED CAPTURE: цвет фигуры не совпадает с ходом")
            return None

        # ------------------------------------------------------
        # 5. Определяем взятую фигуру
        #
        # Для en passant отдельно обрабатываем пешку.
        # ------------------------------------------------------

        captured_piece = None
        captured_square = played_move.to_square

        if board_before.is_en_passant(played_move):

            # При en passant взятая пешка находится не на
            # конечном поле хода.
            if played_piece.piece_type != chess.PAWN:
                print("DELAYED CAPTURE: странный en passant")
                return None

            captured_square = chess.square(
                chess.square_file(played_move.to_square),
                chess.square_rank(played_move.from_square)
            )

            captured_piece = board_before.piece_at(
                captured_square
            )

        else:
            captured_piece = board_before.piece_at(
                played_move.to_square
            )

        # ------------------------------------------------------
        # 6. Должна существовать реальная фигура соперника
        # ------------------------------------------------------

        if captured_piece is None:
            print("DELAYED CAPTURE: взятая фигура не найдена")
            return None

        if captured_piece.color == played_piece.color:
            print("DELAYED CAPTURE: пытаемся взять свою фигуру")
            return None

        # Короля не считаем обычным материалом
        if captured_piece.piece_type == chess.KING:
            print("DELAYED CAPTURE: взятие короля")
            return None

        # ------------------------------------------------------
        # 7. SAN сыгранного хода
        # ------------------------------------------------------

        played_san = board_before.san(played_move)

        # ------------------------------------------------------
        # 8. Выполняем лучший ход
        # ------------------------------------------------------

        board_after_best = board_before.copy(stack=False)

        board_after_best.push(best_move)

        print("BEST MOVE =", best_move)
        print("BEST SAN =", board_before.san(best_move))
        print("POSITION AFTER BEST =", board_after_best)

        # ------------------------------------------------------
        # 9. Проверяем, что наша фигура после best_move
        #    всё ещё находится на исходном поле
        # ------------------------------------------------------

        piece_after_best = board_after_best.piece_at(
            played_move.from_square
        )

        if piece_after_best is None:
            print(
                "DELAYED CAPTURE: наша фигура исчезла "
                "после лучшего хода"
            )
            return None

        if piece_after_best.color != played_piece.color:
            print(
                "DELAYED CAPTURE: на исходном поле "
                "уже другая сторона"
            )
            return None

        if piece_after_best.piece_type != played_piece.piece_type:
            print(
                "DELAYED CAPTURE: наша фигура изменилась"
            )
            return None

        # ------------------------------------------------------
        # 10. Проверяем, что целевая фигура соперника
        #     всё ещё находится на исходном поле
        # ------------------------------------------------------

        target_after_best = board_after_best.piece_at(
            captured_square
        )

        if target_after_best is None:
            print(
                "DELAYED CAPTURE: целевая фигура исчезла "
                "после лучшего хода"
            )
            return None

        if target_after_best.color == played_piece.color:
            print(
                "DELAYED CAPTURE: на цели теперь наша фигура"
            )
            return None

        if target_after_best.piece_type != captured_piece.piece_type:
            print(
                "DELAYED CAPTURE: на цели уже другая фигура"
            )
            return None

        # ------------------------------------------------------
        # 11. Теперь главное.
        #
        # После best_move ход переходит сопернику.
        #
        # Нам НЕ нужно требовать, чтобы played_move был
        # легален прямо сейчас.
        #
        # Проверяем:
        #
        #   best_move
        #       ↓
        #   ход соперника
        #       ↓
        #   played_move снова возможен
        #
        # Это позволяет обнаруживать:
        #
        #   h6 Nb1 Nxc2
        #
        # ------------------------------------------------------

        delayed_capture_possible = False
        opponent_reply = None
        board_after_reply = None

        # На всякий случай ограничиваемся одним ответом соперника.
        # Это важно: мы хотим доказать, что взятие не пропадает
        # сразу, а не искать его через половину партии.

        legal_replies = list(board_after_best.legal_moves)

        print(
            "DELAYED CAPTURE: количество ответов соперника =",
            len(legal_replies)
        )

        # ------------------------------------------------------
        # Сначала проверяем редкий случай:
        # вдруг best_move сам является ходом соперника и
        # наше взятие каким-то образом уже доступно.
        # ------------------------------------------------------

        if played_move in board_after_best.legal_moves:

            delayed_capture_possible = True
            board_after_reply = board_after_best.copy(stack=False)

            print(
                "DELAYED CAPTURE: взятие доступно сразу после best_move"
            )

        else:

            # --------------------------------------------------
            # Перебираем возможные ответы соперника
            # --------------------------------------------------

            for reply in legal_replies:

                # Ответ соперника не должен сам убрать
                # нашу атакующую фигуру или целевую фигуру.
                temp_board = board_after_best.copy(stack=False)

                # Проверяем ответ
                temp_board.push(reply)

                # Наша фигура всё ещё должна быть на исходном поле
                our_piece_after_reply = temp_board.piece_at(
                    played_move.from_square
                )

                if our_piece_after_reply is None:
                    continue

                if our_piece_after_reply.color != played_piece.color:
                    continue

                if our_piece_after_reply.piece_type != played_piece.piece_type:
                    continue

                # Целевая фигура всё ещё должна быть на месте
                target_after_reply = temp_board.piece_at(
                    captured_square
                )

                if target_after_reply is None:
                    continue

                if target_after_reply.color == played_piece.color:
                    continue

                if target_after_reply.piece_type != captured_piece.piece_type:
                    continue

                # --------------------------------------------------
                # Теперь проверяем именно первоначальное взятие
                # --------------------------------------------------

                if played_move not in temp_board.legal_moves:
                    continue

                # Успех
                delayed_capture_possible = True
                opponent_reply = reply
                board_after_reply = temp_board

                print(
                    "DELAYED CAPTURE FOUND!"
                )

                print(
                    "BEST MOVE =",
                    best_move
                )

                print(
                    "BEST SAN =",
                    board_before.san(best_move)
                )

                print(
                    "OPPONENT REPLY =",
                    reply
                )

                print(
                    "OPPONENT REPLY SAN =",
                    board_after_best.san(reply)
                )

                print(
                    "DELAYED CAPTURE =",
                    played_move
                )

                print(
                    "DELAYED CAPTURE SAN =",
                    temp_board.san(played_move)
                )

                break

        # ------------------------------------------------------
        # 12. Если взятие после ответа соперника уже невозможно
        # ------------------------------------------------------

        if not delayed_capture_possible:

            print(
                "DELAYED CAPTURE: после лучшего хода "
                "взятие больше не сохраняется"
            )

            return None

        # ------------------------------------------------------
        # 13. Получаем SAN лучшего хода
        # ------------------------------------------------------

        best_san = board_before.san(best_move)

        # ------------------------------------------------------
        # 14. Получаем SAN отложенного взятия
        # ------------------------------------------------------

        if board_after_reply is not None:

            try:
                delayed_capture_san = board_after_reply.san(
                    played_move
                )
            except Exception:
                delayed_capture_san = played_san

        else:
            delayed_capture_san = played_san

        # ------------------------------------------------------
        # 15. Название взятой фигуры
        # ------------------------------------------------------

        piece_names = {
            chess.PAWN: "пешку",
            chess.KNIGHT: "коня",
            chess.BISHOP: "слона",
            chess.ROOK: "ладью",
            chess.QUEEN: "ферзя",
            chess.KING: "короля",
        }

        captured_name = piece_names.get(
            captured_piece.piece_type,
            "фигуру"
        )

        # ------------------------------------------------------
        # 16. Главное объяснение
        #
        # Именно этот текст нужен пользователю.
        # Никаких дополнительных "конь оказывается под атакой"
        # здесь не добавляем.
        # ------------------------------------------------------

        text = (
            f"Вы слишком рано забрали {captured_name}. "
            f"Сначала стоило сыграть {best_san}. "
            f"После этого взятие {captured_name} всё ещё "
            f"оставалось возможным ходом {delayed_capture_san}."
        )

        # ------------------------------------------------------
        # 17. Возвращаем информацию
        # ------------------------------------------------------

        result = {
            "type": "delayed_capture",

            "best_move": best_move,
            "best_san": best_san,

            "played_move": played_move,
            "played_san": played_san,

            "captured_piece": captured_piece,
            "captured_piece_name": captured_name,

            "played_piece": played_piece,

            "opponent_reply": opponent_reply,

            "text": text,
        }

        print("==============================================")
        print("=== DELAYED CAPTURE RESULT ===")
        print(result)
        print("==============================================")

        return result

    except Exception as e:

        print(
            "Ошибка detect_delayed_capture:",
            repr(e)
        )

        return None

# ==========================================================
# ЛУЧШИЙ ХОД ДОБАВЛЯЕТ ЗАЩИТНИКА К УЯЗВИМОЙ ПЕШКЕ
# ==========================================================

def detect_add_defender_to_vulnerable_pawn(
    board_before,
    best_move,
    played_move
):
    """
    Определяет ситуацию, когда лучший ход добавляет нового
    защитника к уязвимой пешке.

    Пример:

        сыграно: Nxc6
        лучший ход: Rh4

    Пешка d4 атакуется соперником.
    После Rh4 ладья с h4 начинает защищать d4.

    Возвращает информацию только если:

    1. лучший ход легален;
    2. у нашей стороны есть пешка, которая атакуется соперником;
    3. до лучшего хода эта пешка имела меньше защитников,
       чем атакующих фигур соперника;
    4. после лучшего хода появляется новый защитник;
    5. именно фигура, сделавшая лучший ход, становится
       новым защитником этой пешки.
    """

    if (
        board_before is None
        or best_move is None
        or played_move is None
    ):
        return None

    try:

        # ==================================================
        # 1. ХОД ДОЛЖЕН БЫТЬ ЛЕГАЛЬНЫМ
        # ==================================================

        if best_move not in board_before.legal_moves:
            return None

        our_color = board_before.turn
        opponent_color = not our_color

        # ==================================================
        # 2. ФИГУРА, КОТОРАЯ ДЕЛАЕТ ЛУЧШИЙ ХОД
        # ==================================================

        best_piece = board_before.piece_at(
            best_move.from_square
        )

        if not best_piece:
            return None

        if best_piece.piece_type == chess.KING:
            return None

        # ==================================================
        # 3. ПОЗИЦИЯ ПОСЛЕ ЛУЧШЕГО ХОДА
        # ==================================================

        board_after_best = make_position_after(
            board_before,
            best_move
        )

        if not board_after_best:
            return None

        # ==================================================
        # 4. ИЩЕМ УЯЗВИМЫЕ НАШИ ПЕШКИ
        # ==================================================

        candidates = []

        for pawn_square in board_before.pieces(
            chess.PAWN,
            our_color
        ):

            # Пешка должна остаться на той же клетке
            # после лучшего хода.
            pawn_after = (
                board_after_best.piece_at(
                    pawn_square
                )
            )

            if not pawn_after:
                continue

            if pawn_after.piece_type != chess.PAWN:
                continue

            if pawn_after.color != our_color:
                continue

            # ==================================================
            # 5. АТАКУЮЩИЕ СОПЕРНИКА ДО ХОДА
            # ==================================================

            before_attackers = set(
                board_before.attackers(
                    opponent_color,
                    pawn_square
                )
            )

            if not before_attackers:
                continue

            # ==================================================
            # 6. ЗАЩИТНИКИ НАШЕЙ ПЕШКИ ДО ХОДА
            # ==================================================

            before_defenders = set(
                board_before.attackers(
                    our_color,
                    pawn_square
                )
            )

            # ==================================================
            # 7. ПОСЛЕ ЛУЧШЕГО ХОДА
            # ==================================================

            after_attackers = set(
                board_after_best.attackers(
                    opponent_color,
                    pawn_square
                )
            )

            after_defenders = set(
                board_after_best.attackers(
                    our_color,
                    pawn_square
                )
            )

            # ==================================================
            # 8. НОВЫЙ ЗАЩИТНИК
            # ==================================================

            new_defenders = (
                after_defenders
                - before_defenders
            )

            # Именно фигура лучшего хода должна стать
            # новым защитником.
            if best_move.to_square not in new_defenders:
                continue

            # ==================================================
            # 9. ПЕШКА ДЕЙСТВИТЕЛЬНО УЯЗВИМА
            #
            # До лучшего хода атакующих не меньше,
            # чем защитников.
            # ==================================================

            if len(before_attackers) < len(before_defenders):
                continue

            # ==================================================
            # 10. После лучшего хода новый защитник
            # действительно увеличивает число защитников.
            # ==================================================

            if len(after_defenders) <= len(before_defenders):
                continue

            # ==================================================
            # 11. Пешка всё ещё подвергается атаке.
            #
            # Это важно: мы не хотим называть ход
            # "добавлением защитника", если лучший ход
            # просто полностью убрал саму угрозу.
            # ==================================================

            if not after_attackers:
                continue

            # ==================================================
            # 12. Ход должен реально защищать пешку.
            # ==================================================

            try:
                test_board = board_after_best.copy()

                # Проверяем, что фигура с клетки best_move.to_square
                # действительно атакует клетку пешки.
                if pawn_square not in test_board.attacks(
                    best_move.to_square
                ):
                    continue

            except Exception:
                continue

            # ==================================================
            # 13. Сохраняем кандидата
            # ==================================================

            candidates.append(
                {
                    "pawn_square": pawn_square,
                    "before_attackers": before_attackers,
                    "before_defenders": before_defenders,
                    "after_attackers": after_attackers,
                    "after_defenders": after_defenders,
                    "new_defenders": new_defenders,
                    "best_piece": best_piece,
                }
            )

        if not candidates:
            return None

        # ==================================================
        # 14. Выбираем наиболее уязвимую пешку
        #
        # Чем больше перевес атакующих над защитниками,
        # тем более уязвима пешка.
        # ==================================================

        candidates.sort(
            key=lambda item: (
                len(item["before_attackers"])
                - len(item["before_defenders"]),
                -len(item["before_defenders"])
            ),
            reverse=True
        )

        selected = candidates[0]

        pawn_square = selected[
            "pawn_square"
        ]

        pawn_square_name = chess.square_name(
            pawn_square
        )

        try:
            best_san = board_before.san(
                best_move
            )
        except Exception:
            best_san = str(best_move)

        # ==================================================
        # 15. ТЕКСТ
        # ==================================================

        text = (
            f"Лучше было сыграть {best_san}, "
            f"добавляя защитника к уязвимой пешке "
            f"на {pawn_square_name}."
        )

        # ==================================================
        # 16. DEBUG
        # ==================================================

        print()
        print(
            "========== ДОБАВЛЕНИЕ ЗАЩИТНИКА =========="
        )

        print(
            "BEST MOVE =",
            best_move
        )

        print(
            "BEST SAN =",
            best_san
        )

        print(
            "BEST PIECE =",
            best_piece.symbol()
        )

        print(
            "VULNERABLE PAWN =",
            pawn_square_name
        )

        print(
            "BEFORE ATTACKERS =",
            len(
                selected["before_attackers"]
            )
        )

        print(
            "BEFORE DEFENDERS =",
            len(
                selected["before_defenders"]
            )
        )

        print(
            "AFTER ATTACKERS =",
            len(
                selected["after_attackers"]
            )
        )

        print(
            "AFTER DEFENDERS =",
            len(
                selected["after_defenders"]
            )
        )

        print(
            "NEW DEFENDERS =",
            [
                chess.square_name(square)
                for square in selected[
                    "new_defenders"
                ]
            ]
        )

        print(
            "TEXT =",
            text
        )

        print(
            "========== КОНЕЦ ЗАЩИТНИКА ==========\n"
        )

        return {
            "type": "add_defender_to_vulnerable_pawn",
            "best_move": best_move,
            "best_san": best_san,
            "best_piece": best_piece,
            "pawn_square": pawn_square,
            "pawn_square_name": pawn_square_name,
            "before_attackers": selected[
                "before_attackers"
            ],
            "before_defenders": selected[
                "before_defenders"
            ],
            "after_attackers": selected[
                "after_attackers"
            ],
            "after_defenders": selected[
                "after_defenders"
            ],
            "new_defenders": selected[
                "new_defenders"
            ],
            "text": text,
        }

    except Exception as e:

        print(
            "ADD DEFENDER DETECTOR ERROR:",
            repr(e)
        )

        return None

# ==========================================================
# ПОСТЕПЕННОЕ УСИЛЕНИЕ ДАВЛЕНИЯ НА СВЯЗАННУЮ ФИГУРУ
# ==========================================================

def detect_material_pressure_on_linked_piece(
    board,
    played_move,
    best_move,
    played_results=None,
    best_pv=None,
    loss=0
):
    """
    Определяет стратегический мотив:

        лучший ход позволяет постепенно усилить давление
        на ограниченную / связанную фигуру соперника.

    Пример:

        ...Ne8 Re1 f6

    После ...f6:

        Bd6
          \
           Ne5
             \
              Bf4

    Пешка f6 атакует Ne5.

    Если Ne5 уйдёт, линия Bd6-e5-f4 открывается,
    и слон d6 получает возможность взять слона f4.

    Это НЕ классическая связка с королём.
    Это постепенное усиление давления на фигуру,
    которая одновременно защищает / блокирует более ценную фигуру.
    """

    # ==========================================================
    # БАЗОВЫЕ ПРОВЕРКИ
    # ==========================================================

    if board is None:
        return None

    if best_move is None:
        return None

    if not best_pv:
        return None

    try:
        pv = list(best_pv)
    except Exception:
        return None

    if not pv:
        return None

    try:
        if best_move not in board.legal_moves:
            return None
    except Exception:
        return None

    # ==========================================================
    # НАЗВАНИЯ И ЦЕННОСТИ ФИГУР
    # ==========================================================

    piece_names = {
        chess.PAWN: "пешка",
        chess.KNIGHT: "конь",
        chess.BISHOP: "слон",
        chess.ROOK: "ладья",
        chess.QUEEN: "ферзь",
        chess.KING: "король",
    }

    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 100,
    }

    def name_of(piece):

        if piece is None:
            return None

        return piece_names.get(
            piece.piece_type,
            "фигура"
        )

    # ==========================================================
    # ПОЛУЧИТЬ КЛЕТОЧКИ МЕЖДУ ДВУМЯ ПОЛЯМИ
    # ==========================================================

    def get_line_between(a, b):

        af = chess.square_file(a)
        ar = chess.square_rank(a)

        bf = chess.square_file(b)
        br = chess.square_rank(b)

        df = bf - af
        dr = br - ar

        # Поля должны находиться на одной линии:
        # вертикаль, горизонталь или диагональ.
        if df != 0 and dr != 0:

            if abs(df) != abs(dr):
                return None

        step_f = (
            0
            if df == 0
            else (1 if df > 0 else -1)
        )

        step_r = (
            0
            if dr == 0
            else (1 if dr > 0 else -1)
        )

        squares = []

        f = af + step_f
        r = ar + step_r

        while (f, r) != (bf, br):

            if not (
                0 <= f <= 7
                and 0 <= r <= 7
            ):
                return None

            squares.append(
                chess.square(f, r)
            )

            f += step_f
            r += step_r

        return squares

    # ==========================================================
    # ИЩЕМ КОНСТРУКЦИЮ
    #
    # НАША ФИГУРА-СЛАЙДЕР
    #        |
    # ФИГУРА СОПЕРНИКА
    #        |
    # БОЛЕЕ ЦЕННАЯ ФИГУРА СОПЕРНИКА
    #
    # Например:
    #
    #        Bd6
    #          \
    #           Ne5
    #             \
    #              Bf4
    #
    # Здесь:
    #
    # slider   = Bd6
    # target   = Ne5
    # behind   = Bf4
    # ==========================================================

    def find_linked_targets(position):

        result = []

        our_color = position.turn

        for slider_sq, slider in position.piece_map().items():

            # Нас интересуют только наши дальнобойные фигуры.
            if slider.color != our_color:
                continue

            if slider.piece_type not in (
                chess.BISHOP,
                chess.ROOK,
                chess.QUEEN,
            ):
                continue

            # Ищем вражескую target-фигуру.
            for target_sq, target in position.piece_map().items():

                if target.color == our_color:
                    continue

                if target.piece_type == chess.KING:
                    continue

                line = get_line_between(
                    slider_sq,
                    target_sq
                )

                if line is None:
                    continue

                # Между slider и target ничего не должно быть.
                blocked = False

                for sq in line:

                    if position.piece_at(sq) is not None:

                        blocked = True
                        break

                if blocked:
                    continue

                # ==================================================
                # Ищем поле СРАЗУ ЗА target.
                # ==================================================

                sf = chess.square_file(slider_sq)
                sr = chess.square_rank(slider_sq)

                tf = chess.square_file(target_sq)
                tr = chess.square_rank(target_sq)

                step_f = (
                    0
                    if tf == sf
                    else (1 if tf > sf else -1)
                )

                step_r = (
                    0
                    if tr == sr
                    else (1 if tr > sr else -1)
                )

                behind_f = tf + step_f
                behind_r = tr + step_r

                if not (
                    0 <= behind_f <= 7
                    and 0 <= behind_r <= 7
                ):
                    continue

                behind_sq = chess.square(
                    behind_f,
                    behind_r
                )

                behind_piece = position.piece_at(
                    behind_sq
                )

                if behind_piece is None:
                    continue

                if behind_piece.color == our_color:
                    continue

                if behind_piece.piece_type == chess.KING:
                    continue

                # За target должна стоять более ценная фигура.
                target_value = piece_values.get(
                    target.piece_type,
                    0
                )

                behind_value = piece_values.get(
                    behind_piece.piece_type,
                    0
                )

                if behind_value < target_value:
                    continue

                result.append({
                    "target_square": target_sq,
                    "target_piece": target,

                    "slider_square": slider_sq,
                    "slider_piece": slider,

                    "behind_square": behind_sq,
                    "behind_piece": behind_piece,
                })

        return result

    # ==========================================================
    # ПОДГОТОВКА BEST PV
    # ==========================================================

    pv_board = board.copy()

    # Нормализуем PV.
    #
    # В нормальном случае:
    #
    # pv[0] == best_move
    #
    # Например:
    #
    # f6e8
    # f1e1
    # f7f6
    # ...

    if pv[0] == best_move:

        pv_moves = pv

    else:

        # Если переданный PV начинается уже после best_move,
        # сначала самостоятельно выполняем best_move.
        try:
            pv_board.push(best_move)
        except Exception:
            return None

        pv_moves = pv

    # ==========================================================
    # ПРОХОДИМ BEST PV
    # ==========================================================

    for index, move in enumerate(pv_moves):

        # ------------------------------------------------------
        # Проверяем легальность хода.
        # ------------------------------------------------------

        try:

            if move not in pv_board.legal_moves:
                return None

        except Exception:

            return None

        # ------------------------------------------------------
        # Определяем фигуру, которая делает ход,
        # ДО push().
        #
        # ВАЖНО:
        # chess.Move НЕ имеет move.piece().
        # ------------------------------------------------------

        moving_piece = pv_board.piece_at(
            move.from_square
        )

        if moving_piece is None:
            return None

        # ------------------------------------------------------
        # Если это ход нашей стороны,
        # проверяем, не создаёт ли он давление.
        # ------------------------------------------------------

        if moving_piece.color == board.turn:

            # ==================================================
            # Ищем конструкции ДО нашего усиливающего хода.
            # ==================================================

            linked_targets = find_linked_targets(
                pv_board
            )

            if linked_targets:

                # ==================================================
                # Создаём позицию ПОСЛЕ хода.
                # ==================================================

                test_board = pv_board.copy()

                try:
                    test_board.push(move)
                except Exception:
                    continue

                # ==================================================
                # Проверяем каждую связанную фигуру.
                # ==================================================

                for info in linked_targets:

                    target_sq = info["target_square"]

                    slider_sq = info["slider_square"]

                    behind_sq = info["behind_square"]

                    target_before = pv_board.piece_at(
                        target_sq
                    )

                    target_after = test_board.piece_at(
                        target_sq
                    )

                    # Target должна остаться на месте.
                    if target_before is None:
                        continue

                    if target_after is None:
                        continue

                    if target_after.color == board.turn:
                        continue

                    # ==================================================
                    # АТАКИ НА TARGET ДО И ПОСЛЕ ХОДА
                    # ==================================================

                    attackers_before = list(
                        pv_board.attackers(
                            board.turn,
                            target_sq
                        )
                    )

                    attackers_after = list(
                        test_board.attackers(
                            board.turn,
                            target_sq
                        )
                    )

                    # Новая атака.
                    newly_attacked = (
                        len(attackers_before) == 0
                        and
                        len(attackers_after) > 0
                    )

                    # Появился дополнительный атакующий.
                    more_attackers = (
                        len(attackers_after)
                        >
                        len(attackers_before)
                    )

                    # ==================================================
                    # ОСОБАЯ ПРОВЕРКА:
                    #
                    # Ход самой пешки создаёт атаку.
                    #
                    # Например:
                    #
                    # f7-f6
                    #
                    # после чего:
                    #
                    # f6 -> e5
                    #
                    # ==================================================

                    pawn_attacks_target = False

                    if moving_piece.piece_type == chess.PAWN:

                        pawn_after = test_board.piece_at(
                            move.to_square
                        )

                        if (
                            pawn_after is not None
                            and
                            pawn_after.piece_type == chess.PAWN
                            and
                            pawn_after.color == board.turn
                        ):

                            pawn_attacks_target = (
                                target_sq in
                                test_board.attacks(
                                    move.to_square
                                )
                            )

                    # ==================================================
                    # Для остальных фигур тоже можно определить,
                    # атакует ли фигура target после своего хода.
                    # ==================================================

                    piece_attacks_target = False

                    moved_piece_after = test_board.piece_at(
                        move.to_square
                    )

                    if moved_piece_after is not None:

                        if (
                            moved_piece_after.color
                            == board.turn
                        ):

                            piece_attacks_target = (
                                target_sq in
                                test_board.attacks(
                                    move.to_square
                                )
                            )

                    pressure_created = (
                        newly_attacked
                        or
                        more_attackers
                        or
                        pawn_attacks_target
                        or
                        piece_attacks_target
                    )

                    if not pressure_created:
                        continue

                    # ==================================================
                    # ТЕПЕРЬ ПРОВЕРЯЕМ САМОЕ ГЛАВНОЕ:
                    #
                    # Если убрать target,
                    # открывается ли slider -> behind?
                    # ==================================================

                    opened_board = test_board.copy()

                    # Target должна находиться на доске.
                    if opened_board.piece_at(
                        target_sq
                    ) is None:
                        continue

                    opened_board.remove_piece_at(
                        target_sq
                    )

                    slider_piece = opened_board.piece_at(
                        slider_sq
                    )

                    if slider_piece is None:
                        continue

                    if slider_piece.color != board.turn:
                        continue

                    # После удаления target slider должен видеть
                    # более ценную behind-фигуру.
                    slider_attacks_behind = (
                        behind_sq in
                        opened_board.attacks(
                            slider_sq
                        )
                    )

                    if not slider_attacks_behind:
                        continue

                    # ==================================================
                    # ДОПОЛНИТЕЛЬНО:
                    #
                    # Проверяем, что behind-фигура действительно
                    # более ценная.
                    # ==================================================

                    behind_piece = opened_board.piece_at(
                        behind_sq
                    )

                    if behind_piece is None:
                        continue

                    target_piece = target_before

                    target_value = piece_values.get(
                        target_piece.piece_type,
                        0
                    )

                    behind_value = piece_values.get(
                        behind_piece.piece_type,
                        0
                    )

                    if behind_value < target_value:
                        continue

                    # ==================================================
                    # УСПЕШНО НАШЛИ МОТИВ
                    # ==================================================

                    try:
                        strengthening_move_san = (
                            pv_board.san(move)
                        )
                    except Exception:
                        strengthening_move_san = (
                            chess.square_name(
                                move.from_square
                            )
                            +
                            chess.square_name(
                                move.to_square
                            )
                        )

                    return {
                        "type": "material_pressure",

                        "text": (
                            "Так вы теряете материал. "
                            "У вас была возможность выиграть материал, "
                            "постепенно усиливая давление на связанную фигуру."
                        ),

                        "target_piece": name_of(
                            target_piece
                        ),

                        "target_square": chess.square_name(
                            target_sq
                        ),

                        "attacker_piece": name_of(
                            slider_piece
                        ),

                        "attacker_square": chess.square_name(
                            slider_sq
                        ),

                        "behind_piece": name_of(
                            behind_piece
                        ),

                        "behind_square": chess.square_name(
                            behind_sq
                        ),

                        "strengthening_move": move,

                        "strengthening_move_san": (
                            strengthening_move_san
                        ),

                        "attacker_count_before": len(
                            attackers_before
                        ),

                        "attacker_count_after": len(
                            attackers_after
                        ),

                        "pv_index": index,
                    }

        # ======================================================
        # Переходим к следующему ходу PV.
        # ======================================================

        try:
            pv_board.push(move)
        except Exception:
            return None

    return None