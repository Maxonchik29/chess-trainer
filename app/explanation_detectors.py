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
    """
    Проверяет, создаёт ли сыгранный ход новую пешечную
    угрозу против нашей фигуры.

    Логика:

        1. После нашего хода существует легальный ход пешкой
           соперника.

        2. После этого хода пешка начинает атаковать нашу фигуру.

        3. До нашего хода эта же пешка не атаковала
           эту фигуру.

        4. Пешка действительно может следующим ходом
           взять эту фигуру.

        5. Если после взятия пешку можно нормально забрать,
           это не считается серьёзной угрозой.

    Важно:
    функция ищет именно НОВУЮ угрозу, созданную нашим ходом.
    """

    if (
        board_before is None
        or board_after is None
    ):
        return None

    try:

        opponent_color = not our_color

        candidates = []

        # ==================================================
        # 1. НАШИ ФИГУРЫ ПОСЛЕ ХОДА
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

        if not our_pieces:
            return None

        # ==================================================
        # 2. ИЩЕМ ЛЕГАЛЬНЫЕ ПЕШЕЧНЫЕ ХОДЫ СОПЕРНИКА
        # ==================================================

        for opponent_move in board_after.legal_moves:

            pawn = board_after.piece_at(
                opponent_move.from_square
            )

            if pawn is None:
                continue

            if pawn.color != opponent_color:
                continue

            if pawn.piece_type != chess.PAWN:
                continue

            # ==================================================
            # 3. ДЕЛАЕМ ХОД ПЕШКОЙ
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

            moved_pawn = test_board.piece_at(
                attacker_square
            )

            if moved_pawn is None:
                continue

            if moved_pawn.color != opponent_color:
                continue

            if moved_pawn.piece_type != chess.PAWN:
                continue

            # ==================================================
            # 4. ПРОВЕРЯЕМ НАШИ ФИГУРЫ
            # ==================================================

            for target_square, target_piece in our_pieces:

                current_piece = (
                    test_board.piece_at(
                        target_square
                    )
                )

                if current_piece is None:
                    continue

                if current_piece.color != our_color:
                    continue

                if current_piece.piece_type in (
                    chess.KING,
                    chess.PAWN,
                ):
                    continue

                # ==================================================
                # 5. ПЕШКА ДОЛЖНА ДЕЙСТВИТЕЛЬНО АТАКОВАТЬ
                #    НАШУ ФИГУРУ ПОСЛЕ ХОДА
                # ==================================================

                attackers_after = test_board.attackers(
                    opponent_color,
                    target_square
                )

                if attacker_square not in attackers_after:
                    continue

                # ==================================================
                # 6. ДО НАШЕГО ХОДА ЭТА ЖЕ ПЕШКА НЕ ДОЛЖНА
                #    УЖЕ АТАКОВАТЬ ЭТУ ФИГУРУ
                # ==================================================

                before_attackers = (
                    board_before.attackers(
                        opponent_color,
                        target_square
                    )
                )

                if opponent_move.from_square in before_attackers:

                    before_pawn = (
                        board_before.piece_at(
                            opponent_move.from_square
                        )
                    )

                    if (
                        before_pawn is not None
                        and before_pawn.color == opponent_color
                        and before_pawn.piece_type == chess.PAWN
                    ):
                        continue

                # ==================================================
                # 7. ПЕШКА ДОЛЖНА ИМЕТЬ РЕАЛЬНОЕ ВЗЯТИЕ
                #    ЭТОЙ ФИГУРЫ
                # ==================================================

                pawn_capture = None

                for enemy_capture in test_board.legal_moves:

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

                    pawn_capture = enemy_capture
                    break

                if pawn_capture is None:
                    continue

                # ==================================================
                # 8. ПРОВЕРЯЕМ, МОЖНО ЛИ ЗАБРАТЬ ПЕШКУ
                #    ПОСЛЕ ЕЁ ВЗЯТИЯ НАШЕЙ ФИГУРЫ
                # ==================================================

                capture_board = test_board.copy()

                try:

                    capture_board.push(
                        pawn_capture
                    )

                except Exception:

                    continue

                pawn_after_capture_square = (
                    pawn_capture.to_square
                )

                recapture_found = False

                for our_response in capture_board.legal_moves:

                    if (
                        our_response.to_square
                        != pawn_after_capture_square
                    ):
                        continue

                    if not capture_board.is_capture(
                        our_response
                    ):
                        continue

                    captured_piece = (
                        capture_board.piece_at(
                            our_response.to_square
                        )
                    )

                    if captured_piece is None:
                        continue

                    if captured_piece.color == our_color:
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

                    recapture_found = True
                    break

                # ==================================================
                # 9. ЕСЛИ ПЕШКУ МОЖНО НОРМАЛЬНО ЗАБРАТЬ,
                #    ЭТО НЕ СЕРЬЁЗНАЯ ПЕШЕЧНАЯ УГРОЗА
                # ==================================================

                if recapture_found:
                    continue

                # ==================================================
                # 10. КАНДИДАТ ДЕЙСТВИТЕЛЬНО ОПАСЕН
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

                        "attacker_type": (
                            chess.PAWN
                        ),

                        "attacker_square": (
                            attacker_square
                        ),

                        "pawn_move": (
                            opponent_move
                        ),

                        "pawn_capture": (
                            pawn_capture
                        ),

                        "is_new": True,
                    }
                )

        # ==================================================
        # 11. НЕТ НОВОЙ ПЕШЕЧНОЙ УГРОЗЫ
        # ==================================================

        if not candidates:
            return None

        # ==================================================
        # 12. ПРИОРИТЕТ ПО ЦЕННОСТИ ФИГУРЫ
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
            repr(e)
        )

        return None

def find_queen_tempo(
    position_before,
    board_after_played,
    played_move
):
    """
    Проверяет, позволил ли сыгранный ход получить
    НОВУЮ непосредственную атаку на нашего ферзя.

    Условия:

    1. Ферзь принадлежит нашей стороне.
    2. Ферзь существует после сыгранного хода.
    3. Если ферзь был передвинут, проверяется именно он.
    4. До нашего хода выбранный ферзь не находился
       под атакой выбранной фигурой.
    5. После нашего хода существует легальный ход соперника.
    6. Именно фигура, которая делает этот ход,
       после хода непосредственно атакует ферзя.
    7. Простое открытие линии другой фигуре
       не считается queen tempo.
    8. Взятие ферзя также считается атакой.
    """

    if (
        position_before is None
        or board_after_played is None
        or played_move is None
    ):
        return None

    try:

        # ==================================================
        # 1. СТОРОНЫ
        # ==================================================

        our_color = position_before.turn
        opponent_color = not our_color

        # ==================================================
        # 2. ФЕРЗИ ДО ХОДА
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
        # 3. ФЕРЗИ ПОСЛЕ ХОДА
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
        # 4. ОПРЕДЕЛЯЕМ КОНКРЕТНОГО ФЕРЗЯ
        #
        # Если сыгранный ход был ходом ферзя,
        # рассматриваем именно его.
        #
        # Иначе допускаем другого нашего ферзя
        # только если он реально существует после хода.
        # ==================================================

        candidate_queens = []

        played_piece_before = (
            position_before.piece_at(
                played_move.from_square
            )
        )

        played_piece_after = (
            board_after_played.piece_at(
                played_move.to_square
            )
        )

        if (
            played_piece_before is not None
            and played_piece_before.color == our_color
            and played_piece_before.piece_type == chess.QUEEN
            and played_piece_after is not None
            and played_piece_after.color == our_color
            and played_piece_after.piece_type == chess.QUEEN
        ):

            candidate_queens = [
                played_move.to_square
            ]

        else:

            candidate_queens = list(
                queen_after
            )

        # ==================================================
        # 5. ПРОВЕРЯЕМ КАЖДОГО КАНДИДАТА
        # ==================================================

        candidates = []

        for queen_square in candidate_queens:

            queen_piece = (
                board_after_played.piece_at(
                    queen_square
                )
            )

            if (
                queen_piece is None
                or queen_piece.piece_type != chess.QUEEN
                or queen_piece.color != our_color
            ):
                continue

            # ==================================================
            # 6. КТО АТАКОВАЛ ФЕРЗЯ ДО ХОДА?
            # ==================================================

            before_attackers = set(
                position_before.attackers(
                    opponent_color,
                    queen_square
                )
            )

            # ==================================================
            # 7. КТО АТАКУЕТ ФЕРЗЯ ПОСЛЕ ХОДА?
            # ==================================================

            after_attackers = set(
                board_after_played.attackers(
                    opponent_color,
                    queen_square
                )
            )

            # ==================================================
            # 8. НОВЫЕ АТАКУЮЩИЕ
            # ==================================================

            new_attackers = (
                after_attackers
                - before_attackers
            )

            if not new_attackers:
                continue

            # ==================================================
            # 9. ИЩЕМ КОНКРЕТНЫЙ ХОД СОПЕРНИКА
            # ==================================================

            for opponent_move in board_after_played.legal_moves:

                attacker_square = (
                    opponent_move.from_square
                )

                if attacker_square not in new_attackers:
                    continue

                attacker_before = (
                    board_after_played.piece_at(
                        attacker_square
                    )
                )

                if attacker_before is None:
                    continue

                if attacker_before.color != opponent_color:
                    continue

                if attacker_before.piece_type == chess.KING:
                    continue

                # ==================================================
                # 10. ДЕЛАЕМ ХОД СОПЕРНИКА
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
                # 11. ПРОВЕРЯЕМ ФИГУРУ ПОСЛЕ ХОДА
                # ==================================================

                moved_piece = (
                    test_board.piece_at(
                        opponent_move.to_square
                    )
                )

                if moved_piece is None:
                    continue

                if moved_piece.color != opponent_color:
                    continue

                if moved_piece.piece_type == chess.KING:
                    continue

                # ==================================================
                # 12. ИМЕННО ПЕРЕДВИНУВШАЯСЯ ФИГУРА
                #     ДОЛЖНА АТАКОВАТЬ ФЕРЗЯ
                # ==================================================

                if queen_square not in test_board.attacks(
                    opponent_move.to_square
                ):
                    continue

                # ==================================================
                # 13. ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА
                # ==================================================

                actual_attackers = set(
                    test_board.attackers(
                        opponent_color,
                        queen_square
                    )
                )

                if opponent_move.to_square not in actual_attackers:
                    continue

                # ==================================================
                # 14. SAN
                # ==================================================

                try:

                    move_san = (
                        board_after_played.san(
                            opponent_move
                        )
                    )

                except Exception:

                    move_san = opponent_move.uci()

                # ==================================================
                # 15. ДОБАВЛЯЕМ КАНДИДАТА
                # ==================================================

                candidates.append(
                    {
                        "queen_square":
                            queen_square,

                        "attacker_square":
                            opponent_move.from_square,

                        "attacker_piece":
                            attacker_before,

                        "move":
                            opponent_move,

                        "san":
                            move_san,

                        "is_new":
                            True,
                    }
                )

        # ==================================================
        # 16. НИ ОДНОЙ НОВОЙ АТАКИ НЕТ
        # ==================================================

        if not candidates:
            return None

        # ==================================================
        # 17. ПРИОРИТЕТ ФИГУРЫ
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
        # 18. DEBUG
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
            repr(e)
        )

        return None
    
def find_newly_attacked_piece_info(
    board_before,
    board_after,
    our_color
):
    """
    Ищет нашу фигуру, которая ПОСЛЕ сыгранного хода
    оказалась под НОВОЙ атакой соперника.

    Этот детектор НЕ определяет:
        - является ли атака тактически сильной;
        - можно ли выгодно разменяться;
        - является ли это лучшим ответом Stockfish;
        - является ли атака темпом;
        - является ли атака пешечной угрозой.

    Его задача только:

        BEFORE:
            фигура не была атакована конкретным соперником

        AFTER:
            тот же атакующий теперь атакует фигуру

    Специализированные детекторы:
        find_pawn_attack_threat()
        find_piece_tempo_attack()
        find_queen_tempo()

    занимаются более конкретными случаями.
    """

    if board_before is None or board_after is None:
        return None

    try:

        # ==================================================
        # ПРИОРИТЕТ ФИГУР
        # ==================================================

        piece_order = [
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ]

        candidates = []

        opponent_color = not our_color

        # ==================================================
        # ИЩЕМ НАШИ ФИГУРЫ ПОСЛЕ ХОДА
        # ==================================================

        for piece_type in piece_order:

            after_squares = set(
                board_after.pieces(
                    piece_type,
                    our_color
                )
            )

            if not after_squares:
                continue

            before_squares = set(
                board_before.pieces(
                    piece_type,
                    our_color
                )
            )

            for square in after_squares:

                piece = board_after.piece_at(square)

                if piece is None:
                    continue

                if piece.color != our_color:
                    continue

                # ==================================================
                # АТАКИ ПОСЛЕ НАШЕГО ХОДА
                # ==================================================

                attackers_after = set(
                    board_after.attackers(
                        opponent_color,
                        square
                    )
                )

                if not attackers_after:
                    continue

                # ==================================================
                # АТАКИ ДО НАШЕГО ХОДА
                #
                # Если фигура осталась на том же поле,
                # сравниваем реальные атаки.
                #
                # Если фигура появилась на новом поле,
                # до хода именно этой фигуры там не было,
                # поэтому считаем все атаки новыми.
                # ==================================================

                if square in before_squares:

                    attackers_before = set(
                        board_before.attackers(
                            opponent_color,
                            square
                        )
                    )

                else:

                    attackers_before = set()

                new_attackers = (
                    attackers_after
                    - attackers_before
                )

                if not new_attackers:
                    continue

                # ==================================================
                # СОХРАНЯЕМ НОВЫХ АТАКУЮЩИХ
                # ==================================================

                for attacker_square in new_attackers:

                    attacker_piece = (
                        board_after.piece_at(
                            attacker_square
                        )
                    )

                    if attacker_piece is None:
                        continue

                    if attacker_piece.color != opponent_color:
                        continue

                    # ==================================================
                    # ПРОВЕРЯЕМ, ЧТО АТАКА ДЕЙСТВИТЕЛЬНО
                    # ПРИНАДЛЕЖИТ ЭТОЙ ФИГУРЕ
                    #
                    # Это особенно полезно для линий:
                    #
                    # Rook -> piece
                    # Bishop -> piece
                    # Queen -> piece
                    #
                    # где атака могла открыться из-за другой фигуры.
                    # ==================================================

                    actual_attackers = set(
                        board_after.attackers(
                            opponent_color,
                            square
                        )
                    )

                    if attacker_square not in actual_attackers:
                        continue

                    candidates.append(
                        {
                            "piece_name": piece_name(
                                piece
                            ),
                            "piece_type": piece_type,
                            "square": square,

                            "attacker_piece": (
                                attacker_piece
                            ),

                            "attacker_type": (
                                attacker_piece.piece_type
                            ),

                            "attacker_square": (
                                attacker_square
                            ),

                            "is_new": True,

                            "was_on_same_square": (
                                square in before_squares
                            ),
                        }
                    )

        # ==================================================
        # НИЧЕГО НЕ НАЙДЕНО
        # ==================================================

        if not candidates:
            return None

        # ==================================================
        # ПРИОРИТЕТ:
        #
        # 1. Более ценная наша фигура
        # 2. Более сильный атакующий
        #
        # Это НЕ оценка ошибки.
        # Это только выбор кандидата для объяснения.
        # ==================================================

        attacker_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }

        candidates.sort(
            key=lambda item: (
                PIECE_VALUES.get(
                    item.get("piece_type"),
                    0
                ),
                attacker_values.get(
                    item.get("attacker_type"),
                    0
                ),
            ),
            reverse=True
        )

        return candidates[0]

    except Exception as e:

        print(
            "Ошибка find_newly_attacked_piece_info:",
            repr(e)
        )

        return None


def find_newly_attacked_piece(
    board_before,
    board_after,
    our_color
):
    """
    Совместимость со старым кодом.

    Возвращает:

        (piece_name, square)

    либо None.
    """

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
    best_move,
    played_results=None
):
    """
    Определяет ситуацию:

        мы могли взять материал,
        но вместо этого сыграли другой ход;

        после нашего хода соперник получает
        конкретный темп / материальную компенсацию.

    ВАЖНО:

    Используется ПЕРВЫЙ ХОД PV соперника,
    а не любой возможный legal move.

    Поэтому функция не должна придумывать угрозу,
    которую Stockfish реально не выбирает.
    """

    if (
        board is None
        or played_move is None
        or best_move_obj is None
        or not best_move
        or not played_results
    ):
        return None

    try:

        # ==================================================
        # 1. СЫГРАННЫЙ ХОД ДЕЙСТВИТЕЛЬНО ЗАБИРАЕТ МАТЕРИАЛ
        # ==================================================

        captured_name = detect_material_gain(
            board,
            played_move
        )

        if not captured_name:
            return None

        # ==================================================
        # 2. BEST MOVE НЕ ДОЛЖЕН БЫТЬ ПРОСТЫМ ВЗЯТИЕМ
        # ==================================================

        if detect_material_gain(
            board,
            best_move_obj
        ):
            return None

        # ==================================================
        # 3. ЛУЧШАЯ ФИГУРА
        # ==================================================

        best_piece = board.piece_at(
            best_move_obj.from_square
        )

        if best_piece is None:
            return None

        # ==================================================
        # 4. ПОЗИЦИЯ ПОСЛЕ НАШЕГО ХОДА
        # ==================================================

        after_played = make_position_after(
            board,
            played_move
        )

        if after_played is None:
            return None

        opponent_color = after_played.turn
        our_color = not opponent_color

        # ==================================================
        # 5. ПЕРВЫЙ ХОД PV СОПЕРНИКА
        # ==================================================

        first_result = played_results[0]

        if not isinstance(first_result, dict):
            return None

        pv = first_result.get("pv")

        if not pv:
            return None

        opponent_move = pv[0]

        if opponent_move not in after_played.legal_moves:
            return None

        # ==================================================
        # 6. SAN ХОДА СОПЕРНИКА
        # ==================================================

        try:
            opponent_san = after_played.san(
                opponent_move
            )
        except Exception:
            opponent_san = opponent_move.uci()

        # ==================================================
        # 7. ПЕШЕЧНАЯ УГРОЗА
        #
        # Но только если именно ПЕРВЫЙ ХОД PV
        # является той самой пешечной атакой.
        # ==================================================

        pawn_threat = find_pawn_attack_threat(
            board,
            after_played,
            our_color
        )

        if pawn_threat:

            pawn_move = pawn_threat.get(
                "pawn_move"
            )

            if (
                pawn_move is not None
                and pawn_move == opponent_move
            ):

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

                if attacked_square is not None:

                    square_name = chess.square_name(
                        attacked_square
                    )

                    return (
                        f"Вместо взятия {captured_name} "
                        f"ходом {played_move} стоило сыграть "
                        f"{best_move}. После этого соперник "
                        f"получает темп ходом {opponent_san}, "
                        f"атакуя вашу {attacked_piece_name} "
                        f"на {square_name}."
                    )

        # ==================================================
        # 8. ТЕМП НА ФЕРЗЯ
        #
        # find_queen_tempo() тоже должен совпадать
        # именно с первым ходом PV.
        # ==================================================

        queen_tempo = find_queen_tempo(
            board,
            after_played,
            played_move
        )

        if queen_tempo:

            queen_move = queen_tempo.get(
                "move"
            )

            if (
                queen_move is not None
                and queen_move == opponent_move
            ):

                return (
                    f"Вместо взятия {captured_name} "
                    f"ходом {played_move} стоило сыграть "
                    f"{best_move}. После этого соперник "
                    f"получает темп ходом "
                    f"{opponent_san}, атакуя ферзя."
                )

        # ==================================================
        # 9. ПЕРВЫЙ ХОД PV — ШАХ
        # ==================================================

        if after_played.gives_check(
            opponent_move
        ):

            return (
                f"Вместо взятия {captured_name} "
                f"ходом {played_move} стоило сыграть "
                f"{best_move}. После этого соперник "
                f"получает темп с шахом "
                f"{opponent_san}."
            )

        # ==================================================
        # 10. НОВАЯ АТАКА НА ФИГУРУ
        #
        # Здесь используем только если именно первый
        # ход PV создаёт атаку.
        # ==================================================

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
                    f"После этого соперник получает темп "
                    f"ходом {opponent_san}, атакуя вашу "
                    f"{attacked_piece_name} на {square_name}."
                )

            return (
                f"Вместо взятия {captured_name} "
                f"ходом {played_move} стоило сыграть "
                f"{best_move}. После этого соперник "
                f"получает темп ходом {opponent_san}, "
                f"атакуя вашу {attacked_piece_name} "
                f"на {square_name}."
            )

        # ==================================================
        # 11. ПЕРВЫЙ ХОД PV СРАЗУ ЗАБИРАЕТ ФИГУРУ
        # ==================================================

        captured_piece = get_captured_piece(
            after_played,
            opponent_move
        )

        if captured_piece is not None:

            if captured_piece.piece_type not in (
                chess.PAWN,
                chess.KING,
            ):

                captured_name_by_reply = piece_name(
                    captured_piece
                )

                if captured_name_by_reply:

                    return (
                        f"Вместо взятия {captured_name} "
                        f"ходом {played_move} стоило сыграть "
                        f"{best_move}. После этого соперник "
                        f"сразу играет {opponent_san} "
                        f"и забирает "
                        f"{captured_name_by_reply}."
                    )

        return None

    except Exception as e:

        print(
            "Ошибка detect_tempo_material_loss:",
            repr(e)
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
    """
    Ищет конкретную последовательность:

        наш ход
        ->
        новый ход соперника
        ->
        новая абсолютная связка
        ->
        соперник реально может забрать связанную фигуру
        ->
        нормального отбоя нет

    ВАЖНО:
    Этот детектор отвечает именно за материальную потерю
    через абсолютную связку.

    Он НЕ должен срабатывать просто потому, что:
        - фигура оказалась связана;
        - фигура оказалась атакована;
        - фигура временно неподвижна;
        - соперник получил шах.
    """

    if (
        board_before is None
        or board_after is None
    ):
        return None

    try:

        opponent_color = not our_color

        # ==========================================================
        # ТИПЫ ФИГУР, КОТОРЫЕ МОГУТ СОЗДАВАТЬ ЛИНЕЙНУЮ СВЯЗКУ
        # ==========================================================

        slider_types = {
            chess.ROOK,
            chess.BISHOP,
            chess.QUEEN,
        }

        # ==========================================================
        # ЦЕННОСТЬ ФИГУР
        # ==========================================================

        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 100,
        }

        def get_value(piece):
            if piece is None:
                return 0

            return piece_values.get(
                piece.piece_type,
                0
            )

        # ==========================================================
        # ПРОВЕРКА:
        #
        # МОЖНО ЛИ ПОСЛЕ ВЗЯТИЯ ОТБИТЬ АТАКУЮЩУЮ ФИГУРУ?
        #
        # Например:
        #
        # ...Qxe4
        # Rxe4
        #
        # Тогда это не чистая потеря фигуры.
        # ==========================================================

        def can_recapture(
            position,
            capture_move
        ):
            try:

                test = position.copy()

                # ВАЖНО:
                #
                # После capture_move атакующая фигура находится
                # уже НА to_square.
                #
                # Поэтому именно to_square является целью
                # потенциального ответного взятия.

                attacker_square = capture_move.to_square

                test.push(capture_move)

                for reply in list(test.legal_moves):

                    if reply.to_square != attacker_square:
                        continue

                    piece = test.piece_at(
                        reply.from_square
                    )

                    if piece is None:
                        continue

                    if piece.color != our_color:
                        continue

                    target = test.piece_at(
                        reply.to_square
                    )

                    if target is None:
                        continue

                    if target.color != opponent_color:
                        continue

                    # Проверяем, что ответ действительно можно сыграть.
                    after = test.copy()

                    try:
                        after.push(reply)
                    except Exception:
                        continue

                    return True

            except Exception:
                pass

            return False

        # ==========================================================
        # ПРОВЕРКА:
        #
        # ЯВЛЯЕТСЯ ЛИ ФИГУРА АБСОЛЮТНО СВЯЗАННОЙ?
        #
        # Схема:
        #
        # атакующая фигура
        #       |
        #     наша фигура
        #       |
        #      король
        #
        # Причём атакующая фигура должна реально атаковать
        # связанную фигуру.
        # ==========================================================

        def get_absolute_pin_info(
            position,
            pin_move,
            pinned_square
        ):
            try:

                pinned_piece = position.piece_at(
                    pinned_square
                )

                if pinned_piece is None:
                    return None

                if pinned_piece.color != our_color:
                    return None

                if pinned_piece.piece_type == chess.KING:
                    return None

                # --------------------------------------------------
                # Король нашей стороны
                # --------------------------------------------------

                king_square = position.king(
                    our_color
                )

                if king_square is None:
                    return None

                # --------------------------------------------------
                # python-chess уже умеет определять абсолютную
                # связку.
                # --------------------------------------------------

                if not position.is_pinned(
                    our_color,
                    pinned_square
                ):
                    return None

                # --------------------------------------------------
                # Ход соперника должен быть именно той фигурой,
                # которая сейчас создаёт связку.
                # --------------------------------------------------

                attacker_square = pin_move.to_square

                attacker_piece = position.piece_at(
                    attacker_square
                )

                if attacker_piece is None:
                    return None

                if attacker_piece.color != opponent_color:
                    return None

                if attacker_piece.piece_type not in slider_types:
                    return None

                # --------------------------------------------------
                # Координаты
                # --------------------------------------------------

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
                # Все три точки должны находиться на одной линии.
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
                # Проверяем направление:
                #
                # attacker -> pinned -> king
                # --------------------------------------------------

                dx1 = pinned_file - attacker_file
                dy1 = pinned_rank - attacker_rank

                dx2 = king_file - pinned_file
                dy2 = king_rank - pinned_rank

                if dx1 != 0:
                    dx1 = (
                        1
                        if dx1 > 0
                        else -1
                    )

                if dy1 != 0:
                    dy1 = (
                        1
                        if dy1 > 0
                        else -1
                    )

                if dx2 != 0:
                    dx2 = (
                        1
                        if dx2 > 0
                        else -1
                    )

                if dy2 != 0:
                    dy2 = (
                        1
                        if dy2 > 0
                        else -1
                    )

                if (
                    dx1 != dx2
                    or dy1 != dy2
                ):
                    return None

                # --------------------------------------------------
                # Проверяем, что между attacker и pinned нет
                # другой фигуры.
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

                # --------------------------------------------------
                # Король действительно существует.
                # --------------------------------------------------

                king_piece = position.piece_at(
                    king_square
                )

                if king_piece is None:
                    return None

                if king_piece.color != our_color:
                    return None

                if king_piece.piece_type != chess.KING:
                    return None

                # --------------------------------------------------
                # Атакующая фигура должна реально атаковать
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

        # ==========================================================
        # БЫЛА ЛИ ТАКАЯ СВЯЗКА ДО НАШЕГО ХОДА?
        #
        # Если фигура уже была абсолютно связана,
        # наш ход не создавал эту тактику.
        # ==========================================================

        def pin_already_existed(
            pinned_square
        ):
            try:

                before_piece = board_before.piece_at(
                    pinned_square
                )

                if before_piece is None:
                    return False

                if before_piece.color != our_color:
                    return False

                if before_piece.piece_type == chess.KING:
                    return False

                return board_before.is_pinned(
                    our_color,
                    pinned_square
                )

            except Exception:
                return False

        # ==========================================================
        # КАНДИДАТЫ
        # ==========================================================

        candidates = []

        # ==========================================================
        # ПЕРЕБИРАЕМ ХОДЫ СОПЕРНИКА ПОСЛЕ НАШЕГО ХОДА
        #
        # ВАЖНО:
        # Мы НЕ признаём сам факт связки достаточным.
        # Ниже обязательно должно быть конкретное взятие.
        # ==========================================================

        for pin_move in list(
            board_after.legal_moves
        ):

            try:

                attacker = board_after.piece_at(
                    pin_move.from_square
                )

                if attacker is None:
                    continue

                if attacker.color != opponent_color:
                    continue

                if attacker.piece_type not in slider_types:
                    continue

                # --------------------------------------------------
                # Выполняем ход соперника.
                # --------------------------------------------------

                test_board = board_after.copy()

                try:
                    test_board.push(
                        pin_move
                    )
                except Exception:
                    continue

                # --------------------------------------------------
                # После хода соперника перебираем наши фигуры.
                # --------------------------------------------------

                for pinned_square, pinned_piece in list(
                    test_board.piece_map().items()
                ):

                    if pinned_piece.color != our_color:
                        continue

                    # Король сам себя не считаем связанной фигурой.
                    if pinned_piece.piece_type == chess.KING:
                        continue

                    # Пешка здесь не является материальной целью
                    # для pin_material_loss.
                    if pinned_piece.piece_type == chess.PAWN:
                        continue

                    # Нужна как минимум лёгкая фигура.
                    if get_value(pinned_piece) < 3:
                        continue

                    # --------------------------------------------------
                    # Связка должна быть новой.
                    # --------------------------------------------------

                    if pin_already_existed(
                        pinned_square
                    ):
                        continue

                    # --------------------------------------------------
                    # Проверяем абсолютную связку.
                    # --------------------------------------------------

                    pin_info = get_absolute_pin_info(
                        test_board,
                        pin_move,
                        pinned_square
                    )

                    if not pin_info:
                        continue

                    # ==================================================
                    # ИЩЕМ КОНКРЕТНОЕ ВЗЯТИЕ СВЯЗАННОЙ ФИГУРЫ
                    # ==================================================
                    #
                    # Если ход pin_move даёт шах, legal_moves уже
                    # автоматически содержит только допустимые ответы
                    # на шах.
                    #
                    # Но нам НЕ нужно считать ответ на шах самой
                    # причиной потери.
                    #
                    # Нас интересует:
                    #
                    # после pin_move
                    # или после обязательного ответа на шах
                    # соперник получает реальное взятие фигуры.
                    # ==================================================

                    positions_to_check = []

                    # Позиция сразу после pin_move.
                    positions_to_check.append(
                        (
                            test_board,
                            None
                        )
                    )

                    # --------------------------------------------------
                    # Если pin_move дал шах, добавляем позиции после
                    # каждого легального ответа.
                    # --------------------------------------------------

                    if test_board.is_check():

                        for reply in list(
                            test_board.legal_moves
                        ):

                            reply_board = (
                                test_board.copy()
                            )

                            try:
                                reply_board.push(
                                    reply
                                )
                            except Exception:
                                continue

                            positions_to_check.append(
                                (
                                    reply_board,
                                    reply
                                )
                            )

                    # --------------------------------------------------
                    # Ищем лучший конкретный capture.
                    # --------------------------------------------------

                    best_capture = None
                    best_capture_board = None
                    best_reply = None

                    for (
                        position_after_pin,
                        reply
                    ) in positions_to_check:

                        for capture_move in list(
                            position_after_pin.legal_moves
                        ):

                            # Целью должна быть именно связанная фигура.
                            if (
                                capture_move.to_square
                                != pinned_square
                            ):
                                continue

                            # Должно быть настоящее взятие.
                            if not position_after_pin.is_capture(
                                capture_move
                            ):
                                continue

                            captured_piece = get_captured_piece(
                                position_after_pin,
                                capture_move
                            )

                            if captured_piece is None:
                                continue

                            if captured_piece.color != our_color:
                                continue

                            # Пешка и король здесь не считаются
                            # материальной потерей через этот детектор.
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

                            if capturing_piece is None:
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

                            # --------------------------------------------------
                            # Если соперник отдаёт более дорогую фигуру
                            # за более дешёвую — это не тот случай.
                            # --------------------------------------------------

                            if attacker_value > captured_value:
                                continue

                            # --------------------------------------------------
                            # Если мы можем нормально отбить атакующую
                            # фигуру — чистой потери нет.
                            # --------------------------------------------------

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
                                best_capture[
                                    "captured_value"
                                ]
                            ):
                                best_capture = candidate
                                best_capture_board = (
                                    position_after_pin
                                )
                                best_reply = reply

                    # --------------------------------------------------
                    # КРИТИЧЕСКО:
                    #
                    # Если конкретного взятия нет —
                    # это НЕ pin_material_loss.
                    #
                    # Просто новая связка недостаточна.
                    # --------------------------------------------------

                    if best_capture is None:
                        continue

                    # ==================================================
                    # SAN ХОДА, СОЗДАЮЩЕГО СВЯЗКУ
                    # ==================================================

                    try:
                        pin_san = board_after.san(
                            pin_move
                        )
                    except Exception:
                        pin_san = ""

                    if not pin_san:
                        continue

                    # ==================================================
                    # SAN ВЗЯТИЯ
                    # ==================================================

                    capture_san = ""

                    try:
                        capture_san = (
                            best_capture_board.san(
                                best_capture["move"]
                            )
                        )
                    except Exception:
                        capture_san = ""

                    if not capture_san:
                        continue

                    # ==================================================
                    # ИМЕНА
                    # ==================================================

                    pinned_name = piece_name(
                        pinned_piece
                    )

                    if not pinned_name:
                        continue

                    capturing_piece = (
                        best_capture_board.piece_at(
                            best_capture["move"].from_square
                        )
                    )

                    if capturing_piece is None:
                        continue

                    capturing_piece_name = piece_name(
                        capturing_piece
                    )

                    if not capturing_piece_name:
                        continue

                    behind_piece = pin_info.get(
                        "behind_piece"
                    )

                    behind_piece_name = ""

                    if behind_piece is not None:
                        behind_piece_name = piece_name(
                            behind_piece
                        )

                    # ==================================================
                    # СОХРАНЯЕМ КАНДИДАТ
                    # ==================================================

                    candidates.append(
                        {
                            "pin_move": pin_move,

                            "pin_san": pin_san,

                            "capture_move": (
                                best_capture["move"]
                            ),

                            "capture_san": capture_san,

                            "pinned_piece": pinned_piece,

                            "pinned_piece_name": (
                                pinned_name
                            ),

                            "pinned_square": (
                                pinned_square
                            ),

                            "capturing_piece": (
                                capturing_piece
                            ),

                            "capturing_piece_name": (
                                capturing_piece_name
                            ),

                            "behind_piece": (
                                behind_piece
                            ),

                            "behind_piece_name": (
                                behind_piece_name
                            ),

                            "behind_square": (
                                pin_info.get(
                                    "behind_square"
                                )
                            ),

                            "pin_type": "absolute",

                            "reply": best_reply,

                            "priority": (
                                1000,
                                get_value(
                                    pinned_piece
                                ),
                                best_capture[
                                    "captured_value"
                                ],
                            ),
                        }
                    )

            except Exception as e:

                print(
                    "PIN MOVE ANALYSIS ERROR:",
                    repr(e)
                )

                continue

        # ==========================================================
        # НИ ОДНОЙ РЕАЛЬНОЙ ПОСЛЕДОВАТЕЛЬНОСТИ
        # ==========================================================

        if not candidates:
            return None

        # ==========================================================
        # ВЫБИРАЕМ НАИБОЛЕЕ ЗНАЧИМУЮ ПОТЕРЮ
        # ==========================================================

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
            repr(e)
        )

        return None

def detect_pin_material_loss(
    board_before,
    board_after,
    played_move,
    loss=0
):
    """
    Определяет материальную потерю, связанную со связкой.

    Важно:
    конкретная последовательность связки определяется
    внутри _find_pin_material_sequence().
    """

    if (
        board_before is None
        or board_after is None
        or played_move is None
    ):
        return None

    try:

        # ==================================================
        # ПРОВЕРЯЕМ РАЗМЕР ПОТЕРИ
        # ==================================================

        try:
            numeric_loss = float(loss)
        except (TypeError, ValueError):
            numeric_loss = 0.0

        if numeric_loss < 100:
            return None

        # ==================================================
        # ЦВЕТ НАШЕЙ СТОРОНЫ
        # ==================================================

        our_color = board_before.turn

        # ==================================================
        # ИЩЕМ КОНКРЕТНУЮ ПОСЛЕДОВАТЕЛЬНОСТЬ СВЯЗКИ
        # ==================================================

        info = _find_pin_material_sequence(
            board_before,
            board_after,
            our_color
        )

        if not info:
            return None

        # ==================================================
        # ДОБАВЛЯЕМ КОНТЕКСТ
        # ==================================================

        info["played_move"] = played_move
        info["loss"] = numeric_loss

        return info

    except Exception as e:

        print(
            "Ошибка detect_pin_material_loss:",
            repr(e)
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
    loss=0,
    played_results=None
):
    """
    Ищет ситуацию:

        после нашего хода
            ↓
        соперник первым ходом из PV забирает нашу фигуру
            ↓
        мы можем сразу забрать фигуру соперника

    Это нужно для отделения реальной потери фигуры
    от кажущейся потери, которая фактически является разменом.

    ВАЖНО:

    Детектор использует конкретный первый ход из PV Stockfish.
    Он НЕ перебирает произвольные ходы соперника.

    Требуемая последовательность:

        наш ошибочный ход
            ->
        конкретный ответ Stockfish
            ->
        взятие нашей фигуры
            ->
        наше немедленное ответное взятие
    """

    if (
        board is None
        or played_move is None
        or best_move is None
        or not played_results
    ):
        return None

    try:

        # ==================================================
        # БАЗОВАЯ ПРОВЕРКА LOSS
        # ==================================================

        try:
            numeric_loss = float(loss)
        except (TypeError, ValueError):
            numeric_loss = 0.0

        # Детектор нужен только для ситуаций,
        # которые уже выглядят как серьёзная потеря.
        if numeric_loss < 200:
            return None

        # ==================================================
        # ПОЗИЦИЯ ПОСЛЕ НАШЕГО ХОДА
        # ==================================================

        board_after = make_position_after(
            board,
            played_move
        )

        if board_after is None:
            return None

        our_color = board.turn
        opponent_color = not our_color

        # ==================================================
        # ПОЛУЧАЕМ ПЕРВЫЙ ХОД ИЗ PV
        # ==================================================

        first_result = played_results[0]

        if not isinstance(
            first_result,
            dict
        ):
            return None

        pv = first_result.get(
            "pv"
        )

        if not pv:
            return None

        opponent_move = pv[0]

        if opponent_move is None:
            return None

        # ==================================================
        # ПРОВЕРЯЕМ, ЧТО ЭТО ДЕЙСТВИТЕЛЬНО
        # ПЕРВЫЙ ЛЕГАЛЬНЫЙ ОТВЕТ СОПЕРНИКА
        # ==================================================

        try:

            if opponent_move not in board_after.legal_moves:
                return None

        except Exception:
            return None

        # ==================================================
        # ПЕРВЫЙ ХОД ДОЛЖЕН БЫТЬ ВЗЯТИЕМ
        # ==================================================

        try:

            if not board_after.is_capture(
                opponent_move
            ):
                return None

        except Exception:
            return None

        # ==================================================
        # ЧТО ИМЕННО СОПЕРНИК ЗАБИРАЕТ?
        # ==================================================

        captured_piece = get_captured_piece(
            board_after,
            opponent_move
        )

        if captured_piece is None:
            return None

        # Только наша фигура.
        if captured_piece.color != our_color:
            return None

        # Пешки и короли здесь не рассматриваются.
        if captured_piece.piece_type in (
            chess.PAWN,
            chess.KING,
        ):
            return None

        # ==================================================
        # ФИГУРА, КОТОРАЯ ДЕЛАЕТ ВЗЯТИЕ
        # ==================================================

        attacker_piece = (
            board_after.piece_at(
                opponent_move.from_square
            )
        )

        if attacker_piece is None:
            return None

        if attacker_piece.color != opponent_color:
            return None

        if attacker_piece.piece_type == chess.KING:
            return None

        # ==================================================
        # СРАВНИВАЕМ СТОИМОСТЬ
        # ==================================================

        captured_value = piece_value(
            captured_piece
        )

        attacker_value = piece_value(
            attacker_piece
        )

        # Если соперник забирает нашу фигуру
        # фигурой равной или большей стоимости,
        # этот узкий детектор не используем.
        #
        # Нас интересует именно ситуация:
        #
        # дешёвая фигура
        #      ↓
        # забирает дорогую
        #      ↓
        # сразу получает ответное взятие
        if attacker_value >= captured_value:
            return None

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
            return None

        # ==================================================
        # ИЩЕМ НЕМЕДЛЕННОЕ ОТВЕТНОЕ ВЗЯТИЕ
        # ==================================================

        recapture_candidates = []

        for our_reply in list(
            board_after_capture.legal_moves
        ):

            # Нужно забрать именно фигуру,
            # которая только что забрала нашу фигуру.
            if (
                our_reply.to_square
                != opponent_move.to_square
            ):
                continue

            # Это должно быть настоящее взятие.
            if not board_after_capture.is_capture(
                our_reply
            ):
                continue

            # Что именно мы забираем?
            recaptured_piece = get_captured_piece(
                board_after_capture,
                our_reply
            )

            if recaptured_piece is None:
                continue

            # Это должна быть фигура соперника.
            if recaptured_piece.color != opponent_color:
                continue

            # Короля забрать нельзя.
            if recaptured_piece.piece_type == chess.KING:
                continue

            # ==================================================
            # НАША ФИГУРА, КОТОРАЯ ДЕЛАЕТ RECAPTURE
            # ==================================================

            our_recapturing_piece = (
                board_after_capture.piece_at(
                    our_reply.from_square
                )
            )

            if our_recapturing_piece is None:
                continue

            if our_recapturing_piece.color != our_color:
                continue

            # ==================================================
            # ПРОВЕРЯЕМ ЛЕГАЛЬНОСТЬ RECAPTURE
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

            # После нашего взятия на целевой клетке
            # должна находиться наша фигура.
            final_piece = (
                test_exchange.piece_at(
                    our_reply.to_square
                )
            )

            if final_piece is None:
                continue

            if final_piece.color != our_color:
                continue

            # НЕ проверяем test_exchange.is_check().
            #
            # После нашего recapture соперник может
            # оказаться под шахом — это нормальная ситуация.
            #
            # Сам push() уже гарантирует легальность
            # нашего хода и то, что наш король не остаётся
            # под шахом.

            recapture_candidates.append(
                {
                    "move":
                        our_reply,

                    "piece":
                        our_recapturing_piece,

                    "captured_piece":
                        recaptured_piece,

                    "board_after":
                        test_exchange,
                }
            )

        # ==================================================
        # НЕТ НЕМЕДЛЕННОГО RECAPTURE
        # ==================================================

        if not recapture_candidates:
            return None

        # ==================================================
        # ВЫБИРАЕМ RECAPTURE,
        # КОТОРЫЙ ЗАБИРАЕТ НАИБОЛЕЕ ЦЕННУЮ ФИГУРУ
        # ==================================================

        recapture_candidates.sort(
            key=lambda item: piece_value(
                item.get(
                    "captured_piece"
                )
            ),
            reverse=True
        )

        selected = recapture_candidates[0]

        recapture_move = selected.get(
            "move"
        )

        recapturing_piece = selected.get(
            "piece"
        )

        recaptured_attacker = selected.get(
            "captured_piece"
        )

        board_after_exchange = selected.get(
            "board_after"
        )

        if (
            recapture_move is None
            or recapturing_piece is None
            or recaptured_attacker is None
            or board_after_exchange is None
        ):
            return None

        # ==================================================
        # SAN
        # ==================================================

        try:

            opponent_san = board_after.san(
                opponent_move
            )

        except Exception:

            opponent_san = opponent_move.uci()

        try:

            recapture_san = (
                board_after_capture.san(
                    recapture_move
                )
            )

        except Exception:

            recapture_san = recapture_move.uci()

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
            return None

        if not attacker_name:
            return None

        if not recapturing_name:
            return None

        if not recaptured_attacker_name:
            return None

        # ==================================================
        # DEBUG
        # ==================================================

        print(
            "\n========== APPARENT PIECE LOSS =========="
        )

        print(
            "PLAYED:",
            played_move.uci()
        )

        print(
            "BEST:",
            (
                best_move.uci()
                if isinstance(
                    best_move,
                    chess.Move
                )
                else best_move
            )
        )

        print(
            "ENGINE REPLY:",
            opponent_san
        )

        print(
            "CAPTURED:",
            captured_name,
            captured_value
        )

        print(
            "ATTACKER:",
            attacker_name,
            attacker_value
        )

        print(
            "RECAPTURE:",
            recapture_san
        )

        print(
            "RECAPTURES:",
            recaptured_attacker_name
        )

        print(
            "LOSS:",
            numeric_loss
        )

        print(
            "========== END APPARENT PIECE LOSS ==========\n"
        )

        # ==================================================
        # ВОЗВРАЩАЕМ РЕЗУЛЬТАТ
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
                piece_value(
                    recaptured_attacker
                ),

            "loss":
                numeric_loss,

            "board_after_exchange":
                board_after_exchange,

            "is_immediate_recapture":
                True,

            # Здесь True означает именно:
            # атакующая фигура дешевле той фигуры,
            # которую она забрала.
            #
            # Это НЕ означает, что размен выгоден.
            "is_attacker_cheaper_than_captured":
                (
                    attacker_value
                    <
                    captured_value
                ),
        }

    except Exception as e:

        print(
            "Ошибка detect_apparent_piece_loss_but_recapturable:",
            repr(e)
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
    best_pv = (
        mistake.get("best_pv")
        or mistake.get("best_line")
        or mistake.get("pv")
        or []
    )
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

    captured_piece_name = info.get(
        "captured_piece_name"
    )

    opponent_san = info.get(
        "opponent_san"
    )

    recapture_san = info.get(
        "recapture_san"
    )

    attacker_piece_name = info.get(
        "attacker_piece_name"
    )

    if (
        not captured_piece_name
        or not opponent_san
        or not recapture_san
    ):
        return ""

    best_text = best or "лучшего хода"

    if attacker_piece_name:

        return (
            f"Соперник может сыграть {opponent_san} "
            f"и забрать вашего {captured_piece_name}, "
            f"но после {recapture_san} вы забираете "
            f"{attacker_piece_name}. Поэтому {captured_piece_name} "
            f"не теряется безвозвратно. Однако после этого "
            f"размена позиция остаётся значительно хуже, "
            f"чем после {best_text}."
        )

    return (
        f"Соперник может забрать вашего "
        f"{captured_piece_name} ходом {opponent_san}, "
        f"но после {recapture_san} вы можете ответить "
        f"взятием. Поэтому {captured_piece_name} "
        f"не теряется безвозвратно. Однако после этого "
        f"размена позиция остаётся значительно хуже, "
        f"чем после {best_text}."
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
    Ищет нашу пешку, которая после played_move:

    1. существовала до хода;
    2. была защищена до хода;
    3. после хода больше не имеет защитников;
    4. соперник действительно может сразу её взять;
    5. потеря защиты связана с изменением позиции после played_move.

    Возвращает информацию о пешке или None.
    """

    if (
        position_before is None
        or board_after_played is None
        or played_move is None
    ):
        return None

    try:

        # ==================================================
        # ЦВЕТ НАШЕЙ СТОРОНЫ
        # ==================================================

        our_color = position_before.turn
        opponent_color = not our_color

        candidate_pawns = []

        # ==================================================
        # ИЩЕМ НАШИ ПЕШКИ
        # ==================================================

        for square in chess.SQUARES:

            piece_before = (
                position_before.piece_at(square)
            )

            piece_after = (
                board_after_played.piece_at(square)
            )

            # --------------------------------------------------
            # Пешка должна существовать ДО и ПОСЛЕ хода
            # на том же поле.
            #
            # Если пешка сама только что переместилась,
            # это уже отдельный случай.
            # --------------------------------------------------

            if piece_before is None:
                continue

            if piece_before.color != our_color:
                continue

            if piece_before.piece_type != chess.PAWN:
                continue

            if piece_after is None:
                continue

            if piece_after.color != our_color:
                continue

            if piece_after.piece_type != chess.PAWN:
                continue

            # ==================================================
            # 1. ЗАЩИТНИКИ ДО НАШЕГО ХОДА
            # ==================================================

            defenders_before = set(
                position_before.attackers(
                    our_color,
                    square
                )
            )

            # Сама пешка не может быть своим защитником
            defenders_before.discard(square)

            if not defenders_before:
                continue

            # ==================================================
            # 2. ЗАЩИТНИКИ ПОСЛЕ НАШЕГО ХОДА
            # ==================================================

            defenders_after = set(
                board_after_played.attackers(
                    our_color,
                    square
                )
            )

            defenders_after.discard(square)

            # Если хотя бы один защитник остался,
            # пешка не стала полностью незащищённой.
            if defenders_after:
                continue

            # ==================================================
            # 3. ПРОВЕРЯЕМ, ЧТО ЗАЩИТА ДЕЙСТВИТЕЛЬНО ИСЧЕЗЛА
            # ==================================================

            lost_defenders = (
                defenders_before
                - defenders_after
            )

            if not lost_defenders:
                continue

            # ==================================================
            # 4. МОЖЕТ ЛИ СОПЕРНИК СРАЗУ ВЗЯТЬ ПЕШКУ?
            # ==================================================

            opponent_capture = None
            capture_san = ""

            for opponent_move in board_after_played.legal_moves:

                if opponent_move.to_square != square:
                    continue

                if not board_after_played.is_capture(
                    opponent_move
                ):
                    continue

                captured_piece = (
                    board_after_played.piece_at(
                        opponent_move.to_square
                    )
                )

                if captured_piece is None:
                    continue

                if captured_piece.color != our_color:
                    continue

                if captured_piece.piece_type != chess.PAWN:
                    continue

                try:

                    capture_san = (
                        board_after_played.san(
                            opponent_move
                        )
                    )

                except Exception:

                    capture_san = (
                        opponent_move.uci()
                    )

                opponent_capture = opponent_move
                break

            if opponent_capture is None:
                continue

            # ==================================================
            # 5. СОХРАНЯЕМ КАНДИДАТА
            # ==================================================

            candidate_pawns.append(
                {
                    "square": square,

                    "piece": piece_after,

                    "capture_move": (
                        opponent_capture
                    ),

                    "capture_san": capture_san,

                    "defenders_before": (
                        list(defenders_before)
                    ),

                    "defenders_after": (
                        list(defenders_after)
                    ),

                    "lost_defenders": (
                        list(lost_defenders)
                    ),

                    "is_newly_undefended": True,
                }
            )

        # ==================================================
        # 6. НИЧЕГО НЕ НАЙДЕНО
        # ==================================================

        if not candidate_pawns:
            return None

        # ==================================================
        # 7. ЕСЛИ ПЕШЕК НЕСКОЛЬКО —
        # БЕРЁМ БОЛЕЕ ЦЕННУЮ ПОЗИЦИЮ НЕЛЬЗЯ ОЦЕНИВАТЬ
        # ТОЛЬКО ПО ЦЕННОСТИ ПЕШКИ, ПОЭТОМУ ПРОСТО
        # ВОЗВРАЩАЕМ ПЕРВУЮ.
        # ==================================================

        return candidate_pawns[0]

    except Exception as e:

        print(
            "NEWLY UNDEFENDED PAWN ERROR:",
            repr(e)
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
                "material",
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
                    loss,
                    mistake.get("played_results") or []
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
            "pawn_attack",
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
    # 10. АТАКА НА ФИГУРУ С ТЕМПОМ
    # ======================================================

    piece_tempo_attack = None

    if (
        board_after_played
        and played_move
    ):
        try:
            our_color = not board_after_played.turn

            piece_tempo_attack = find_piece_tempo_attack(
                board_after_played,
                played_move,
                mistake.get("played_results") or [],
                our_color
            )

        except Exception as e:
            print(
                "CONSEQUENCES PIECE TEMPO ERROR:",
                repr(e)
            )

    if piece_tempo_attack:

        add_event(
            "piece_tempo_attack",
            72,
            piece_tempo_attack.get(
                "text",
                ""
            ),
            info=piece_tempo_attack,
        )

    # ======================================================
    # 10. НОВЫЙ ШАХ СОПЕРНИКА
    #
    # ВАЖНО:
    #
    # Недостаточно просто найти шах после played_move.
    # Нужно убедиться, что этот шах:
    #
    #     1. доступен ПОСЛЕ нашего хода;
    #     2. НЕ был доступен ДО нашего хода.
    #
    # Только тогда это действительно новая шаховая угроза.
    # ======================================================

    new_check_threat = None

    if (
        position_before
        and board_after_played
        and played_move
    ):

        try:

            opponent_color = board_after_played.turn

            # --------------------------------------------------
            # Шахи, которые уже существовали ДО нашего хода.
            #
            # Сохраняем их в виде UCI:
            #
            # "e7e1", "d8h4" и т. п.
            # --------------------------------------------------

            checks_before = set()

            try:

                for opponent_move_before in (
                    position_before.legal_moves
                ):

                    try:

                        if (
                            opponent_move_before
                            not in position_before.legal_moves
                        ):
                            continue

                        if position_before.gives_check(
                            opponent_move_before
                        ):

                            checks_before.add(
                                opponent_move_before.uci()
                            )

                    except Exception:

                        continue

            except Exception:

                checks_before = set()

            # --------------------------------------------------
            # Ищем шахи после нашего хода.
            # --------------------------------------------------

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

                    # --------------------------------------------------
                    # Это уже существовавший шаховой ход?
                    #
                    # Если да — он не является новой угрозой.
                    #
                    # Важно: после played_move некоторые ходы могут
                    # получить другой контекст, поэтому сравниваем
                    # конкретный UCI-ход.
                    # --------------------------------------------------

                    if opponent_move.uci() in checks_before:

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

            # --------------------------------------------------
            # Приоритет шахов:
            #
            # Q > R > B > N > P
            # --------------------------------------------------

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
                    "is_new": True,
                    "checks_before": checks_before,
                }

        except Exception as e:

            print(
                "CONSEQUENCES NEW CHECK ERROR:",
                repr(e)
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
            "new_check_threat",
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
                    best,
                    mistake.get("played_results") or []
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
    # 20. ВИЛКА ЛУЧШИМ ХОДОМ
    #
    # ВАЖНО:
    #
    # Недостаточно, чтобы после best_move конь атаковал
    # две фигуры.
    #
    # Нужно проверить, что best_move ДЕЙСТВИТЕЛЬНО
    # создал новые атаки.
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

                # --------------------------------------------------
                # Какие ценные фигуры атаковал конь ДО хода?
                # --------------------------------------------------

                attacks_before = set()

                for square in position_before.attacks(
                    best_move.from_square
                ):

                    target_piece = (
                        position_before.piece_at(
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

                        attacks_before.add(
                            square
                        )

                # --------------------------------------------------
                # Позиция после лучшего хода.
                # --------------------------------------------------

                board_after_best = (
                    position_before.copy()
                )

                board_after_best.push(
                    best_move
                )

                # --------------------------------------------------
                # Какие ценные фигуры атакует конь ПОСЛЕ хода?
                # --------------------------------------------------

                attacks_after = set()

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

                        attacks_after.add(
                            square
                        )

                # --------------------------------------------------
                # Только НОВЫЕ атаки.
                # --------------------------------------------------

                new_attack_squares = (
                    attacks_after
                    - attacks_before
                )

                fork_targets = []

                for square in new_attack_squares:

                    target_piece = (
                        board_after_best.piece_at(
                            square
                        )
                    )

                    if not target_piece:
                        continue

                    if (
                        target_piece.color
                        == best_piece.color
                    ):
                        continue

                    if target_piece.piece_type in (
                        chess.PAWN,
                        chess.KING,
                    ):
                        continue

                    fork_targets.append(
                        (
                            target_piece,
                            square
                        )
                    )

                # --------------------------------------------------
                # Настоящая новая вилка:
                #
                # минимум две новые атаки на фигуры.
                # --------------------------------------------------

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

                    first_name = (
                        PIECE_NAMES.get(
                            first_piece.piece_type,
                            "фигуру"
                        )
                    )

                    second_name = (
                        PIECE_NAMES.get(
                            second_piece.piece_type,
                            "фигуру"
                        )
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
                        new_attack_squares=(
                            list(new_attack_squares)
                        ),
                    )

        except Exception as e:

            print(
                "CONSEQUENCES FORK ERROR:",
                repr(e)
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

    ВАЖНО:

    Детектор считает это piece tempo attack только если:

        1. фигура действительно находится на destination
           сыгранного хода;

        2. первый ход PV соперника легален;

        3. именно фигура соперника, сделавшая этот ход,
           атакует нашу фигуру;

        4. эта атака появилась именно после нашего хода,
           то есть ДО нашего хода такой атаки не было;

        5. наша фигура не является королём.

    Возвращает информацию о такой атаке.
    """

    # ==========================================================
    # 1. ПРОВЕРКА ВХОДНЫХ ДАННЫХ
    # ==========================================================

    if (
        board_after is None
        or played_move is None
        or not played_results
    ):
        return None

    try:

        # ======================================================
        # 2. ФИГУРА, КОТОРУЮ МЫ ТОЛЬКО ЧТО ПЕРЕДВИНУЛИ
        # ======================================================

        attacked_square = played_move.to_square

        our_piece = board_after.piece_at(
            attacked_square
        )

        if our_piece is None:
            return None

        # Короля здесь не рассматриваем.
        # Для шаха существует отдельная логика.
        if our_piece.piece_type == chess.KING:
            return None

        if our_piece.color != our_color:
            return None

        # ======================================================
        # 3. ПЕРВЫЙ ХОД PV — ОТВЕТ СОПЕРНИКА
        # ======================================================

        first_result = played_results[0]

        if not isinstance(first_result, dict):
            return None

        pv = first_result.get("pv")

        if not pv:
            return None

        opponent_move = pv[0]

        # ======================================================
        # 4. ПРОВЕРЯЕМ ЛЕГАЛЬНОСТЬ ОТВЕТА
        # ======================================================

        if opponent_move not in board_after.legal_moves:
            return None

        # ======================================================
        # 5. ФИГУРА, КОТОРАЯ СДЕЛАЛА ОТВЕТ
        # ======================================================

        attacker_piece = board_after.piece_at(
            opponent_move.from_square
        )

        if attacker_piece is None:
            return None

        # Это должна быть фигура соперника.
        if attacker_piece.color == our_color:
            return None

        # ======================================================
        # 6. ВОССТАНАВЛИВАЕМ ПОЗИЦИЮ ДО НАШЕГО ХОДА
        #
        # board_after должен быть позицией непосредственно
        # после played_move.
        #
        # Делаем копию, чтобы не изменять оригинальную доску.
        # ======================================================

        board_before = None

        try:

            board_before = board_after.copy()

            # Проверяем, что последний ход действительно
            # соответствует played_move.
            if not board_before.move_stack:
                return None

            last_move = board_before.peek()

            if last_move != played_move:
                return None

            board_before.pop()

        except Exception as e:

            print(
                "PIECE TEMPO ATTACK RESTORE BEFORE ERROR:",
                repr(e)
            )

            return None

        # ======================================================
        # 7. АТАКОВАЛАСЬ ЛИ ЭТА ФИГУРА ДО НАШЕГО ХОДА?
        #
        # Если уже атаковалалась, это НЕ новая tempo attack.
        #
        # Например:
        #
        # до нашего хода:
        #     конь уже атакует ферзя
        #
        # мы делаем другой ход
        #     Qe3
        #
        # соперник играет Nd5
        #
        # Это не новая атака, созданная нашим ходом.
        # ======================================================

        was_already_attacked = False

        try:

            was_already_attacked = (
                board_before.is_attacked_by(
                    not our_color,
                    attacked_square
                )
            )

        except Exception:

            was_already_attacked = False

        if was_already_attacked:
            return None

        # ======================================================
        # 8. ДЕЛАЕМ ПЕРВЫЙ ХОД СОПЕРНИКА
        # ======================================================

        board_reply = board_after.copy()

        try:

            board_reply.push(
                opponent_move
            )

        except Exception as e:

            print(
                "PIECE TEMPO ATTACK PUSH ERROR:",
                repr(e)
            )

            return None

        # ======================================================
        # 9. ПОСЛЕ ХОДА СОПЕРНИКА НАША ФИГУРА
        #    ДОЛЖНА НАХОДИТЬСЯ ПОД АТАКОЙ
        # ======================================================

        if not board_reply.is_attacked_by(
            not our_color,
            attacked_square
        ):
            return None

        # ======================================================
        # 10. ПРОВЕРЯЕМ, ЧТО ИМЕННО ХОДИВШАЯ ФИГУРА
        #     СОПЕРНИКА СОЗДАЁТ АТАКУ
        #
        # Это важно.
        #
        # После хода соперника наша фигура может стать
        # атакованной другой фигурой, например из-за открытия
        # линии слону или ладье.
        #
        # Нас это здесь не интересует.
        #
        # Нам нужна именно:
        #
        #     Qe3 Nd5
        #          ↑
        #       этот конь
        #       атакует ферзя
        # ======================================================

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

        # ======================================================
        # 11. ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА:
        #     АТАКА ДЕЙСТВИТЕЛЬНО НОВАЯ
        #
        # Проверяем ту же самую фигуру соперника
        # в позиции ДО нашего хода.
        #
        # Это особенно полезно для случаев, когда фигура
        # соперника уже стояла на таком поле и уже атаковала
        # destination.
        # ======================================================

        attacker_was_on_destination = (
            board_before.piece_at(
                opponent_move.to_square
            )
        )

        if (
            attacker_was_on_destination is not None
            and attacker_was_on_destination.color
            != our_color
        ):
            try:

                old_attacks = board_before.attacks(
                    opponent_move.to_square
                )

                if attacked_square in old_attacks:
                    return None

            except Exception:
                pass

        # ======================================================
        # 12. SAN ОТВЕТА СОПЕРНИКА
        # ======================================================

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

        # ======================================================
        # 13. НАЗВАНИЯ ФИГУР
        # ======================================================

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

        # ======================================================
        # 14. РЕЗУЛЬТАТ
        # ======================================================

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

            "is_new_attack":
                True,

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
            repr(e)
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
    # Если после Rxd4 наша сторона сразу играет Qxd4,
    # Nxd4, Bxd4 и т.п. — это нормальный размен.
    #
    # Если Stockfish после Rxd4 НЕ забирает фигуру соперника,
    # значит потеря материала не компенсируется немедленно.
    # ==========================================================

    normal_recap = False

    if best_reply is not None:

        print(
            "BEST REPLY TO SQUARE =",
            chess.square_name(best_reply.to_square)
        )

        print(
            "OPPONENT CAPTURE TO SQUARE =",
            chess.square_name(opponent_move.to_square)
        )

        if after_capture.is_capture(best_reply):

            print(
                "BEST REPLY IS CAPTURE = True"
            )

            # Обычный ответный размен:
            # наша фигура после взятия соперника
            # забирает именно фигуру соперника.
            if best_reply.to_square == opponent_move.to_square:
                normal_recap = True

        else:
            print(
                "BEST REPLY IS CAPTURE = False"
            )

    print(
        "NORMAL RECAPTURE =",
        normal_recap
    )

    if normal_recap:

        print(
            "FORCED LOSS EXIT: "
            "Stockfish показывает обычный ответный размен"
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
    Ищет потерю нашей пешки, возникшую после сыгранного хода.

    Пешка отслеживается по исходному квадрату, поэтому
    её перемещения учитываются:

        e4 -> e5 -> dxe5

    или:

        d4 -> d5 -> d6 -> Bxd6

    Важно:

    PLAYED PV:
        рассматривается после сыгранного хода.

    BEST PV может храниться как:

        best_move + ответ + ...

    либо:

        ответ + ...

    В обоих случаях board_best приводится
    к позиции ПОСЛЕ best_move.

    Дополнительно:

    Если после первого взятия пешки есть короткая
    материальная последовательность, она сохраняется.

    Например:

        Bxb2+ Nxb2 Qxb2+

    В таком случае текст может показать всю
    короткую последовательность, а причина всё равно
    остаётся именно pawn_loss, а не causal_material_loss.
    """

    if not mistake:
        return None

    position_before = mistake.get("position_before")

    if position_before is None:
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

    our_color = position_before.turn

    # ==========================================================
    # ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
    # ==========================================================

    def get_captured_piece(board, move):
        """
        Возвращает реально взятую фигуру.

        Учитывает обычное взятие и en passant.
        """

        try:

            if not board.is_capture(move):
                return None, None

            # --------------------------------------------------
            # Обычное взятие
            # --------------------------------------------------

            if not board.is_en_passant(move):

                return (
                    board.piece_at(
                        move.to_square
                    ),
                    move.to_square,
                )

            # --------------------------------------------------
            # En passant
            # --------------------------------------------------

            captured_square = chess.square(
                chess.square_file(
                    move.to_square
                ),
                chess.square_rank(
                    move.from_square
                ),
            )

            return (
                board.piece_at(
                    captured_square
                ),
                captured_square,
            )

        except Exception:

            return None, None

    # ==========================================================
    # ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
    # ==========================================================

    def material_swing_for_our_side(
        captured_piece,
        mover_color,
    ):
        """
        Возвращает изменение материала нашей стороны
        от одного взятия.

        +N = наша сторона получила материал.
        -N = наша сторона потеряла материал.

        Например:

            соперник Bxb2:
                -1

            мы Nxb2:
                +3

            соперник Qxb2:
                -3

        Итого:

            -1 + 3 - 3 = -1

        То есть мы потеряли одну пешку.
        """

        if captured_piece is None:
            return 0

        piece_value = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0,
        }.get(
            captured_piece.piece_type,
            0,
        )

        if mover_color != our_color:

            # Соперник забирает нашу фигуру.
            return -piece_value

        # Мы забираем фигуру соперника.
        return piece_value

    # ==========================================================
    # 1. СОЗДАЁМ ОТСЛЕЖИВАНИЕ ПЕШЕК ДО НАШЕГО ХОДА
    #
    # original_square -> current_square
    # ==========================================================

    tracked_pawns = {}

    for square in position_before.pieces(
        chess.PAWN,
        our_color
    ):

        tracked_pawns[square] = square

    # ==========================================================
    # 2. ПОЗИЦИЯ ПОСЛЕ НАШЕГО ХОДА
    # ==========================================================

    try:

        board_after_played = (
            position_before.copy()
        )

        played_move = (
            board_after_played.parse_san(
                played_san
            )
        )

        # ------------------------------------------------------
        # Если нашим ходом двигалась пешка,
        # обновляем её реальную позицию ДО push().
        # ------------------------------------------------------

        played_piece = (
            board_after_played.piece_at(
                played_move.from_square
            )
        )

        if (
            played_piece is not None
            and played_piece.color == our_color
            and played_piece.piece_type == chess.PAWN
        ):

            if (
                played_move.from_square
                in tracked_pawns
            ):

                tracked_pawns[
                    played_move.from_square
                ] = played_move.to_square

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

    # ==========================================================
    # 3. PV ПОСЛЕ СЫГРАННОГО ХОДА
    # ==========================================================

    first_result = played_results[0]

    if not isinstance(first_result, dict):
        return None

    pv_played = (
        first_result.get("pv")
        or []
    )

    if not pv_played:

        print(
            "PAWN LOSS: PV после сыгранного хода отсутствует"
        )

        return None

    # ==========================================================
    # 4. ПРОИГРЫВАЕМ PLAYED PV
    # ==========================================================

    board = (
        board_after_played.copy()
    )

    lost_pawn_square = None
    lost_pawn_move = None
    lost_pawn_san = None
    lost_pawn_original_square = None

    # ----------------------------------------------------------
    # Короткая последовательность вокруг потери пешки.
    #
    # Например:
    #
    # Bxb2+ Nxb2 Qxb2+
    #
    # Храним SAN и материальный результат этой
    # короткой последовательности.
    # ----------------------------------------------------------

    pawn_loss_sequence = []
    pawn_loss_sequence_swing = 0

    # После обнаружения потери пешки продолжаем
    # ещё несколько полуходов.
    #
    # 3 полухода достаточно для типичного:
    #
    # Bxb2+ Nxb2 Qxb2+
    #
    # но сам поиск пешки НЕ зависит от длины
    # этой последовательности.
    sequence_plies_after_capture = 2

    try:

        for move_index, move in enumerate(pv_played):

            if move not in board.legal_moves:

                print(
                    "PAWN LOSS: нелегальный ход в PV:",
                    move
                )

                break

            # ==================================================
            # СНАЧАЛА ПОЛУЧАЕМ SAN
            # ==================================================

            try:

                move_san = board.san(move)

            except Exception:

                move_san = ""

            # ==================================================
            # СНАЧАЛА ПРОВЕРЯЕМ ВЗЯТИЕ
            # ==================================================

            captured_piece, captured_square = (
                get_captured_piece(
                    board,
                    move
                )
            )

            # ==================================================
            # ЕСЛИ ПЕШКА УЖЕ БЫЛА НАЙДЕНА —
            # СОБИРАЕМ КОРОТКОЕ ПРОДОЛЖЕНИЕ
            # ==================================================

            if (
                lost_pawn_square is not None
                and len(pawn_loss_sequence)
                < sequence_plies_after_capture + 1
            ):

                if move_san:

                    pawn_loss_sequence.append(
                        move_san
                    )

                pawn_loss_sequence_swing += (
                    material_swing_for_our_side(
                        captured_piece,
                        board.turn,
                    )
                )

            # ==================================================
            # ИЩЕМ ПЕРВОЕ ВЗЯТИЕ НАШЕЙ ПЕШКИ
            # ==================================================

            if (
                lost_pawn_square is None
                and captured_piece is not None
                and captured_piece.color == our_color
                and captured_piece.piece_type == chess.PAWN
            ):

                for (
                    original_square,
                    current_square
                ) in list(tracked_pawns.items()):

                    if current_square != captured_square:
                        continue

                    lost_pawn_square = (
                        captured_square
                    )

                    lost_pawn_original_square = (
                        original_square
                    )

                    lost_pawn_san = move_san
                    lost_pawn_move = move

                    # --------------------------------------------------
                    # Первый ход последовательности.
                    # --------------------------------------------------

                    if move_san:

                        pawn_loss_sequence = [
                            move_san
                        ]

                    pawn_loss_sequence_swing = (
                        material_swing_for_our_side(
                            captured_piece,
                            board.turn,
                        )
                    )

                    print(
                        "!!! PAWN LOSS FOUND !!!"
                    )

                    print(
                        "ORIGINAL PAWN =",
                        chess.square_name(
                            original_square
                        )
                    )

                    print(
                        "LOST PAWN =",
                        chess.square_name(
                            captured_square
                        )
                    )

                    print(
                        "CAPTURE MOVE =",
                        lost_pawn_san
                    )

                    break

            # ==================================================
            # ЕСЛИ ЭТО НАШ ХОД —
            # ПЕРЕМЕЩАЕМ ОТСЛЕЖИВАЕМУЮ ПЕШКУ
            # ==================================================

            if board.turn == our_color:

                for (
                    original_square,
                    current_square
                ) in list(
                    tracked_pawns.items()
                ):

                    if (
                        current_square
                        != move.from_square
                    ):
                        continue

                    tracked_pawns[
                        original_square
                    ] = move.to_square

                    break

            # ==================================================
            # ДЕЛАЕМ ХОД
            # ==================================================

            board.push(move)

            # ==================================================
            # ЕСЛИ УЖЕ НАШЛИ ПЕШКУ И СОБРАЛИ
            # ДОСТАТОЧНО КОРОТКУЮ ПОСЛЕДОВАТЕЛЬНОСТЬ —
            # ОСТАНАВЛИВАЕМСЯ.
            # ==================================================

            if (
                lost_pawn_square is not None
                and len(pawn_loss_sequence)
                >= sequence_plies_after_capture + 1
            ):

                break

    except Exception as e:

        print(
            "PAWN LOSS: ошибка анализа PV:",
            repr(e)
        )

        return None

    # ==========================================================
    # 5. ПЕШКА НЕ НАЙДЕНА
    # ==========================================================

    if (
        lost_pawn_square is None
        or lost_pawn_original_square is None
    ):

        print(
            "PAWN LOSS: в PV после сыгранного "
            "хода потеря нашей пешки не найдена"
        )

        return None

    # ==========================================================
    # 6. ПОЛУЧАЕМ BEST PV
    # ==========================================================

    best_results = (
        mistake.get("best_results")
        or []
    )

    pv_best = []

    if best_results:

        try:

            if isinstance(
                best_results[0],
                dict
            ):

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

    # ==========================================================
    # 7. ФОРМИРУЕМ ТЕКСТ
    #
    # Здесь используем короткую последовательность,
    # если она действительно содержит продолжение.
    # ==========================================================

    pawn_name = chess.square_name(
        lost_pawn_square
    )

    def build_pawn_loss_text():

        # ------------------------------------------------------
        # Если есть последовательность:
        #
        # Bxb2+ Nxb2 Qxb2+
        #
        # и её итог действительно означает потерю
        # материала нашей стороны, показываем её.
        # ------------------------------------------------------

        if (
            len(pawn_loss_sequence) >= 2
            and pawn_loss_sequence_swing < 0
        ):

            sequence_text = (
                " ".join(
                    pawn_loss_sequence
                )
            )

            return (
                f"После {played_san} соперник "
                f"может начать последовательность "
                f"{sequence_text}, в результате "
                f"которой выигрывает пешку."
            )

        # ------------------------------------------------------
        # Обычная потеря пешки без продолжения.
        # ------------------------------------------------------

        if lost_pawn_san:

            return (
                f"После {played_san} соперник "
                f"может забрать пешку на "
                f"{pawn_name} ходом "
                f"{lost_pawn_san}."
            )

        return (
            "Ваш ход приводит к потере пешки."
        )

    # ==========================================================
    # 8. ЕСЛИ BEST PV НЕТ
    #
    # Возвращаем найденную потерю,
    # но помечаем её как непроверенную
    # относительно лучшего хода.
    # ==========================================================

    if not pv_best:

        text = build_pawn_loss_text()

        return {
            "text": text,
            "pawn_square": lost_pawn_square,
            "pawn_square_name": pawn_name,
            "pawn_original_square": (
                lost_pawn_original_square
            ),
            "capture_move": lost_pawn_move,
            "capture_san": lost_pawn_san,
            "sequence": (
                pawn_loss_sequence
            ),
            "sequence_swing": (
                pawn_loss_sequence_swing
            ),
            "verified_against_best": False,
        }

    # ==========================================================
    # 9. ВОССТАНАВЛИВАЕМ BEST MOVE
    # ==========================================================

    board_best = position_before.copy(
        stack=False
    )

    best_move_obj = None

    best = (
        mistake.get("best")
        or ""
    )

    if best:

        try:

            best_move_obj = (
                position_before.parse_san(
                    best
                )
            )

        except Exception:

            best_move_obj = None

    if best_move_obj is None:

        print(
            "PAWN LOSS: не удалось восстановить best_move"
        )

        return None

    # ==========================================================
    # 10. ОПРЕДЕЛЯЕМ ФОРМАТ BEST PV
    # ==========================================================

    pv_starts_with_best = (
        bool(pv_best)
        and pv_best[0] == best_move_obj
    )

    # ==========================================================
    # 11. ПРИМЕНЯЕМ BEST MOVE К ДОСКЕ
    #
    # board_best должен оказаться
    # ПОСЛЕ best_move.
    # ==========================================================

    try:

        if best_move_obj not in board_best.legal_moves:

            print(
                "PAWN LOSS: best_move нелегален"
            )

            return None

        board_best.push(
            best_move_obj
        )

    except Exception as e:

        print(
            "PAWN LOSS: не удалось применить "
            "best_move:",
            repr(e)
        )

        return None

    # ==========================================================
    # 12. ОПРЕДЕЛЯЕМ, ЧТО ОСТАЁТСЯ ПРОИГРАТЬ
    # ИЗ BEST PV
    # ==========================================================

    if pv_starts_with_best:

        pv_best_to_play = (
            pv_best[1:]
        )

    else:

        pv_best_to_play = pv_best

    # ==========================================================
    # 13. ОТСЛЕЖИВАЕМ ПЕШКИ В BEST PV
    # ==========================================================

    best_pawns = {}

    for square in position_before.pieces(
        chess.PAWN,
        our_color
    ):

        best_pawns[square] = square

    # ==========================================================
    # 14. ЕСЛИ BEST MOVE БЫЛ ХОДОМ НАШЕЙ ПЕШКИ
    # ==========================================================

    best_move_piece = (
        position_before.piece_at(
            best_move_obj.from_square
        )
    )

    if (
        best_move_piece is not None
        and best_move_piece.color == our_color
        and best_move_piece.piece_type == chess.PAWN
    ):

        if (
            best_move_obj.from_square
            in best_pawns
        ):

            best_pawns[
                best_move_obj.from_square
            ] = best_move_obj.to_square

    # ==========================================================
    # 15. ПРОИГРЫВАЕМ ОСТАТОК BEST PV
    # ==========================================================

    pawn_lost_in_best = False
    best_pawn_capture_san = None

    try:

        for move in pv_best_to_play:

            if move not in board_best.legal_moves:

                print(
                    "PAWN LOSS: нелегальный ход "
                    "в BEST PV:",
                    move
                )

                break

            # ==================================================
            # ПРОВЕРЯЕМ ВЗЯТИЕ НАШЕЙ ПЕШКИ
            # ==================================================

            captured_piece, captured_square = (
                get_captured_piece(
                    board_best,
                    move
                )
            )

            if (
                captured_piece is not None
                and captured_piece.color == our_color
                and captured_piece.piece_type == chess.PAWN
            ):

                captured_original_square = None

                for (
                    original_square,
                    current_square
                ) in list(
                    best_pawns.items()
                ):

                    if (
                        current_square
                        != captured_square
                    ):
                        continue

                    captured_original_square = (
                        original_square
                    )

                    if (
                        original_square
                        == lost_pawn_original_square
                    ):

                        pawn_lost_in_best = True

                        try:

                            best_pawn_capture_san = (
                                board_best.san(move)
                            )

                        except Exception:

                            best_pawn_capture_san = ""

                        print(
                            "PAWN LOSS: та же пешка "
                            "теряется и в BEST PV"
                        )

                        break

                # --------------------------------------------------
                # Удаляем реально взятую пешку
                # из отслеживания.
                # --------------------------------------------------

                if (
                    captured_original_square
                    is not None
                ):

                    best_pawns.pop(
                        captured_original_square,
                        None
                    )

                if pawn_lost_in_best:
                    break

            # ==================================================
            # ЕСЛИ ЭТО НАШ ХОД —
            # ПЕРЕМЕЩАЕМ ОТСЛЕЖИВАЕМУЮ ПЕШКУ
            # ==================================================

            if board_best.turn == our_color:

                for (
                    original_square,
                    current_square
                ) in list(
                    best_pawns.items()
                ):

                    if (
                        current_square
                        != move.from_square
                    ):
                        continue

                    best_pawns[
                        original_square
                    ] = move.to_square

                    break

            # ==================================================
            # ДЕЛАЕМ ХОД
            # ==================================================

            board_best.push(move)

    except Exception as e:

        print(
            "PAWN LOSS: ошибка анализа BEST PV:",
            repr(e)
        )

    # ==========================================================
    # 16. ЕСЛИ ТА ЖЕ ПЕШКА ТЕРЯЕТСЯ И ПОСЛЕ BEST
    #
    # Тогда сыгранный ход не является причиной
    # именно этой потери пешки.
    # ==========================================================

    if pawn_lost_in_best:

        print(
            "PAWN LOSS: та же пешка теряется "
            "и после лучшего хода — НЕ считаем причиной"
        )

        return None

    # ==========================================================
    # 17. ФОРМИРУЕМ ФИНАЛЬНЫЙ ТЕКСТ
    # ==========================================================

    text = build_pawn_loss_text()

    # ==========================================================
    # 18. DEBUG
    # ==========================================================

    print(
        "=============================================="
    )

    print(
        "!!! PAWN LOSS НАЙДЕН !!!"
    )

    print(
        "PAWN ORIGINAL =",
        chess.square_name(
            lost_pawn_original_square
        )
    )

    print(
        "PAWN CURRENT =",
        pawn_name
    )

    print(
        "CAPTURE =",
        lost_pawn_san
    )

    print(
        "SEQUENCE =",
        " ".join(
            pawn_loss_sequence
        )
    )

    print(
        "SEQUENCE SWING =",
        pawn_loss_sequence_swing
    )

    print(
        "BEST PV CAPTURE =",
        best_pawn_capture_san
    )

    print(
        "TEXT =",
        text
    )

    print(
        "=============================================="
    )

    # ==========================================================
    # 19. РЕЗУЛЬТАТ
    # ==========================================================

    return {
        "text": text,
        "pawn_square": lost_pawn_square,
        "pawn_square_name": pawn_name,
        "pawn_original_square": (
            lost_pawn_original_square
        ),
        "capture_move": lost_pawn_move,
        "capture_san": lost_pawn_san,
        "sequence": (
            pawn_loss_sequence
        ),
        "sequence_swing": (
            pawn_loss_sequence_swing
        ),
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
    best_move,
    best_pv=None
):
    """
    Определяет ситуацию, когда игрок слишком рано забрал материал:

        played_move = взятие
        best_move   = полезный невзятие

    После best_move используется КОНКРЕТНЫЙ ответ соперника
    из PV Stockfish. После этого первоначальное взятие должно
    снова быть легальным.

    Пример:

        сыграно: Nxc2?!
        лучше:   h6!

        PV:
            h6 Nb1 Nxc2

    Тогда функция сообщает:

        "Вы слишком рано забрали ладью. Сначала стоило сыграть h6.
        После этого взятие ладьи всё ещё оставалось возможным
        ходом Nxc2."

    ВАЖНО:
    Не перебираем все legal moves соперника.
    Иначе можно случайно найти совершенно искусственный ответ,
    который Stockfish вообще не рассматривал.
    """

    print("==============================================")
    print("=== ВХОД В detect_delayed_capture() ===")
    print("==============================================")

    try:

        # ======================================================
        # 1. Базовые проверки
        # ======================================================

        if board_before is None:
            print("DELAYED CAPTURE: board_before = None")
            return None

        if played_move is None:
            print("DELAYED CAPTURE: played_move = None")
            return None

        if best_move is None:
            print("DELAYED CAPTURE: best_move = None")
            return None

        if played_move not in board_before.legal_moves:
            print("DELAYED CAPTURE: сыгранный ход нелегален")
            return None

        if best_move not in board_before.legal_moves:
            print("DELAYED CAPTURE: лучший ход нелегален")
            return None

        # ======================================================
        # 2. Сыгранный ход обязательно должен быть взятием
        # ======================================================

        if not board_before.is_capture(played_move):
            print(
                "DELAYED CAPTURE: сыгранный ход "
                "не является взятием"
            )
            return None

        # ======================================================
        # 3. Лучший ход не должен быть взятием
        # ======================================================

        if board_before.is_capture(best_move):
            print(
                "DELAYED CAPTURE: лучший ход "
                "является взятием"
            )
            return None

        # ======================================================
        # 4. Получаем нашу фигуру
        # ======================================================

        played_piece = board_before.piece_at(
            played_move.from_square
        )

        if played_piece is None:
            print(
                "DELAYED CAPTURE: "
                "не найдена сыгранная фигура"
            )
            return None

        if played_piece.color != board_before.turn:
            print(
                "DELAYED CAPTURE: цвет фигуры "
                "не совпадает с ходом"
            )
            return None

        # ======================================================
        # 5. Определяем взятую фигуру
        #
        # Отдельно учитываем en passant.
        # ======================================================

        captured_piece = None
        captured_square = played_move.to_square

        if board_before.is_en_passant(played_move):

            if played_piece.piece_type != chess.PAWN:
                print(
                    "DELAYED CAPTURE: "
                    "странный en passant"
                )
                return None

            captured_square = chess.square(
                chess.square_file(
                    played_move.to_square
                ),
                chess.square_rank(
                    played_move.from_square
                )
            )

            captured_piece = board_before.piece_at(
                captured_square
            )

        else:

            captured_piece = board_before.piece_at(
                played_move.to_square
            )

        # ======================================================
        # 6. Проверяем взятую фигуру
        # ======================================================

        if captured_piece is None:
            print(
                "DELAYED CAPTURE: "
                "взятая фигура не найдена"
            )
            return None

        if captured_piece.color == played_piece.color:
            print(
                "DELAYED CAPTURE: "
                "пытаемся взять свою фигуру"
            )
            return None

        # Короля не рассматриваем как обычный материал.
        if captured_piece.piece_type == chess.KING:
            print(
                "DELAYED CAPTURE: "
                "взятие короля"
            )
            return None

        # ======================================================
        # 7. SAN сыгранного хода
        # ======================================================

        played_san = board_before.san(
            played_move
        )

        best_san = board_before.san(
            best_move
        )

        print(
            "PLAYED MOVE =",
            played_move
        )

        print(
            "PLAYED SAN =",
            played_san
        )

        print(
            "BEST MOVE =",
            best_move
        )

        print(
            "BEST SAN =",
            best_san
        )

        # ======================================================
        # 8. Проверяем PV
        # ======================================================
        #
        # Нам нужен ответ соперника ПОСЛЕ best_move.
        #
        # Возможны два формата PV:
        #
        #   Вариант 1:
        #       [best_move, opponent_reply, ...]
        #
        #   Вариант 2:
        #       [opponent_reply, ...]
        #
        # В нашем анализаторе наиболее вероятен первый вариант,
        # но поддерживаем оба.
        # ======================================================

        if not best_pv:
            print(
                "DELAYED CAPTURE: "
                "best_pv отсутствует"
            )
            return None

        pv = list(best_pv)

        print(
            "DELAYED CAPTURE: BEST PV =",
            pv
        )

        opponent_reply = None

        # ------------------------------------------------------
        # Если PV начинается с best_move:
        #
        #   best_move
        #   opponent_reply
        #   ...
        # ------------------------------------------------------

        if len(pv) >= 2 and pv[0] == best_move:

            opponent_reply = pv[1]

            print(
                "DELAYED CAPTURE: "
                "PV начинается с best_move"
            )

        # ------------------------------------------------------
        # Если PV уже начинается с ответа соперника:
        #
        #   opponent_reply
        #   ...
        # ------------------------------------------------------

        elif len(pv) >= 1 and pv[0] != best_move:

            opponent_reply = pv[0]

            print(
                "DELAYED CAPTURE: "
                "PV начинается с ответа соперника"
            )

        else:

            print(
                "DELAYED CAPTURE: "
                "не удалось определить ответ соперника"
            )

            return None

        if opponent_reply is None:
            print(
                "DELAYED CAPTURE: "
                "opponent_reply = None"
            )
            return None

        # ======================================================
        # 9. Сыгрываем best_move
        # ======================================================

        board_after_best = board_before.copy(
            stack=False
        )

        board_after_best.push(best_move)

        print(
            "POSITION AFTER BEST MOVE:"
        )
        print(
            board_after_best
        )

        # ======================================================
        # 10. Проверяем нашу фигуру
        #
        # Она должна остаться на исходном поле.
        # ======================================================

        piece_after_best = (
            board_after_best.piece_at(
                played_move.from_square
            )
        )

        if piece_after_best is None:
            print(
                "DELAYED CAPTURE: "
                "наша фигура исчезла "
                "после best_move"
            )
            return None

        if piece_after_best.color != played_piece.color:
            print(
                "DELAYED CAPTURE: "
                "на исходном поле уже "
                "другая сторона"
            )
            return None

        if piece_after_best.piece_type != played_piece.piece_type:
            print(
                "DELAYED CAPTURE: "
                "наша фигура изменилась"
            )
            return None

        # ======================================================
        # 11. Проверяем целевую фигуру
        #
        # Она тоже должна остаться на исходном поле.
        # ======================================================

        target_after_best = (
            board_after_best.piece_at(
                captured_square
            )
        )

        if target_after_best is None:
            print(
                "DELAYED CAPTURE: "
                "целевая фигура исчезла "
                "после best_move"
            )
            return None

        if target_after_best.color == played_piece.color:
            print(
                "DELAYED CAPTURE: "
                "на цели теперь наша фигура"
            )
            return None

        if target_after_best.piece_type != captured_piece.piece_type:
            print(
                "DELAYED CAPTURE: "
                "на цели уже другая фигура"
            )
            return None

        # ======================================================
        # 12. Проверяем конкретный ответ из PV
        # ======================================================

        if opponent_reply not in board_after_best.legal_moves:

            print(
                "DELAYED CAPTURE: "
                "ответ из PV нелегален после best_move"
            )

            print(
                "BEST MOVE =",
                best_move
            )

            print(
                "OPPONENT REPLY =",
                opponent_reply
            )

            return None

        opponent_reply_san = (
            board_after_best.san(
                opponent_reply
            )
        )

        print(
            "OPPONENT REPLY =",
            opponent_reply
        )

        print(
            "OPPONENT REPLY SAN =",
            opponent_reply_san
        )

        # ======================================================
        # 13. Сыгрываем ответ соперника
        # ======================================================

        board_after_reply = (
            board_after_best.copy(
                stack=False
            )
        )

        board_after_reply.push(
            opponent_reply
        )

        # ======================================================
        # 14. Проверяем, что наша фигура всё ещё существует
        # ======================================================

        our_piece_after_reply = (
            board_after_reply.piece_at(
                played_move.from_square
            )
        )

        if our_piece_after_reply is None:

            print(
                "DELAYED CAPTURE: "
                "наша фигура исчезла "
                "после ответа соперника"
            )

            return None

        if (
            our_piece_after_reply.color
            != played_piece.color
        ):

            print(
                "DELAYED CAPTURE: "
                "после ответа соперника "
                "на исходном поле другая сторона"
            )

            return None

        if (
            our_piece_after_reply.piece_type
            != played_piece.piece_type
        ):

            print(
                "DELAYED CAPTURE: "
                "наша фигура изменилась "
                "после ответа соперника"
            )

            return None

        # ======================================================
        # 15. Проверяем, что целевая фигура всё ещё существует
        # ======================================================

        target_after_reply = (
            board_after_reply.piece_at(
                captured_square
            )
        )

        if target_after_reply is None:

            print(
                "DELAYED CAPTURE: "
                "целевая фигура исчезла "
                "после ответа соперника"
            )

            return None

        if (
            target_after_reply.color
            == played_piece.color
        ):

            print(
                "DELAYED CAPTURE: "
                "после ответа соперника "
                "на цели наша фигура"
            )

            return None

        if (
            target_after_reply.piece_type
            != captured_piece.piece_type
        ):

            print(
                "DELAYED CAPTURE: "
                "на цели уже другая фигура "
                "после ответа соперника"
            )

            return None

        # ======================================================
        # 16. Главное доказательство:
        #
        # первоначальное взятие снова должно быть
        # ЛЕГАЛЬНЫМ.
        # ======================================================

        if played_move not in board_after_reply.legal_moves:

            print(
                "DELAYED CAPTURE: "
                "первоначальное взятие "
                "НЕ стало снова легальным"
            )

            return None

        # ======================================================
        # 17. Получаем SAN отложенного взятия
        # ======================================================

        delayed_capture_san = (
            board_after_reply.san(
                played_move
            )
        )

        print(
            "DELAYED CAPTURE FOUND!"
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
            "OPPONENT REPLY =",
            opponent_reply
        )

        print(
            "OPPONENT REPLY SAN =",
            opponent_reply_san
        )

        print(
            "DELAYED CAPTURE =",
            played_move
        )

        print(
            "DELAYED CAPTURE SAN =",
            delayed_capture_san
        )

        # ======================================================
        # 18. Название взятой фигуры
        # ======================================================

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

        # ======================================================
        # 19. Главное объяснение
        # ======================================================

        text = (
            f"Вы слишком рано забрали {captured_name}. "
            f"Сначала стоило сыграть {best_san}. "
            f"После этого взятие {captured_name} всё ещё "
            f"оставалось возможным ходом "
            f"{delayed_capture_san}."
        )

        # ======================================================
        # 20. Возвращаем результат
        # ======================================================

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
            "opponent_reply_san": opponent_reply_san,

            "delayed_capture": played_move,
            "delayed_capture_san": delayed_capture_san,

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

    Идея:

        наша дальнобойная фигура
                |
                v
        вражеская target-фигура
                |
                v
        более ценная вражеская фигура

    Например:

        Bd6
          \
           Ne5
             \
              Bf4

    Если мы усиливаем давление на Ne5, сопернику может
    потребоваться убрать Ne5.

    После ухода Ne5 линия Bd6-e5-f4 открывается,
    и Bd6 получает возможность взять Bf4.

    ВАЖНО:

    Самого факта "линия открывается" недостаточно.

    Функция дополнительно проверяет:

        1. target действительно подверглась новому давлению;
        2. target может легально уйти;
        3. после ухода target наша конкретная slider-фигура
           действительно может легально взять behind-фигуру;
        4. behind-фигура действительно ценнее target.

    Это позволяет не выдавать объяснение просто потому,
    что на доске существует красивая связанная конструкция.
    """

    # ==========================================================
    # 1. БАЗОВЫЕ ПРОВЕРКИ
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
    # 2. НАЗВАНИЯ И ЦЕННОСТИ ФИГУР
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
    # 3. ПОЛЯ МЕЖДУ ДВУМЯ КЛЕТКАМИ
    # ==========================================================

    def get_line_between(a, b):

        af = chess.square_file(a)
        ar = chess.square_rank(a)

        bf = chess.square_file(b)
        br = chess.square_rank(b)

        df = bf - af
        dr = br - ar

        # Должна быть вертикаль, горизонталь или диагональ.
        if df != 0 and dr != 0:

            if abs(df) != abs(dr):
                return None

        # Одинаковое поле нам не подходит.
        if df == 0 and dr == 0:
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
    # 4. ПОЛУЧАЕМ ПОЛЕ СРАЗУ ЗА TARGET
    # ==========================================================

    def get_behind_square(
        slider_sq,
        target_sq
    ):

        sf = chess.square_file(slider_sq)
        sr = chess.square_rank(slider_sq)

        tf = chess.square_file(target_sq)
        tr = chess.square_rank(target_sq)

        df = tf - sf
        dr = tr - sr

        if df != 0 and dr != 0:

            if abs(df) != abs(dr):
                return None

        if df == 0 and dr == 0:
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

        behind_f = tf + step_f
        behind_r = tr + step_r

        if not (
            0 <= behind_f <= 7
            and 0 <= behind_r <= 7
        ):
            return None

        return chess.square(
            behind_f,
            behind_r
        )

    # ==========================================================
    # 5. ИЩЕМ СВЯЗАННЫЕ ФИГУРЫ
    # ==========================================================
    #
    # Наша дальнобойная фигура
    #          |
    #          v
    #       TARGET
    #          |
    #          v
    #       BEHIND
    #
    # Между ними не должно быть других фигур.
    #
    # BEHIND должен быть строго ценнее TARGET.
    # ==========================================================

    def find_linked_targets(position):

        result = []

        our_color = position.turn

        for slider_sq, slider in position.piece_map().items():

            # --------------------------------------------------
            # Только наши фигуры.
            # --------------------------------------------------

            if slider.color != our_color:
                continue

            # --------------------------------------------------
            # Только дальнобойные фигуры.
            # --------------------------------------------------

            if slider.piece_type not in (
                chess.BISHOP,
                chess.ROOK,
                chess.QUEEN,
            ):
                continue

            # --------------------------------------------------
            # Ищем вражескую target-фигуру.
            # --------------------------------------------------

            for target_sq, target in position.piece_map().items():

                if target.color == our_color:
                    continue

                if target.piece_type == chess.KING:
                    continue

                # --------------------------------------------------
                # Slider и target должны находиться на одной линии.
                # --------------------------------------------------

                line = get_line_between(
                    slider_sq,
                    target_sq
                )

                if line is None:
                    continue

                # --------------------------------------------------
                # Между slider и target не должно быть фигур.
                # --------------------------------------------------

                blocked = False

                for sq in line:

                    if position.piece_at(sq) is not None:

                        blocked = True
                        break

                if blocked:
                    continue

                # --------------------------------------------------
                # Поле сразу за target.
                # --------------------------------------------------

                behind_sq = get_behind_square(
                    slider_sq,
                    target_sq
                )

                if behind_sq is None:
                    continue

                behind_piece = position.piece_at(
                    behind_sq
                )

                if behind_piece is None:
                    continue

                if behind_piece.color == our_color:
                    continue

                if behind_piece.piece_type == chess.KING:
                    continue

                # --------------------------------------------------
                # Behind должна быть СТРОГО ценнее target.
                # --------------------------------------------------

                target_value = piece_values.get(
                    target.piece_type,
                    0
                )

                behind_value = piece_values.get(
                    behind_piece.piece_type,
                    0
                )

                if behind_value <= target_value:
                    continue

                # --------------------------------------------------
                # Сохраняем конструкцию.
                # --------------------------------------------------

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
    # 6. ПОДГОТОВКА PV
    # ==========================================================

    pv_board = board.copy(
        stack=False
    )

    # ----------------------------------------------------------
    # Возможны два варианта переданного PV:
    #
    # A:
    #
    #   [best_move, reply, ...]
    #
    # B:
    #
    #   [reply, ...]
    #
    # В варианте B самостоятельно выполняем best_move.
    # ----------------------------------------------------------

    if pv[0] == best_move:

        pv_moves = pv

    else:

        try:

            if best_move not in pv_board.legal_moves:
                return None

            pv_board.push(best_move)

        except Exception:
            return None

        pv_moves = pv

    # ==========================================================
    # 7. ПРОХОДИМ PV
    # ==========================================================

    for index, move in enumerate(pv_moves):

        # ------------------------------------------------------
        # Проверяем легальность.
        # ------------------------------------------------------

        try:

            if move not in pv_board.legal_moves:
                return None

        except Exception:

            return None

        # ------------------------------------------------------
        # Получаем фигуру до хода.
        # ------------------------------------------------------

        moving_piece = pv_board.piece_at(
            move.from_square
        )

        if moving_piece is None:
            return None

        # ------------------------------------------------------
        # Нас интересуют только ходы нашей стороны.
        # ------------------------------------------------------

        if moving_piece.color == board.turn:

            # ==================================================
            # Ищем связанные конструкции ДО нашего хода.
            # ==================================================

            linked_targets = find_linked_targets(
                pv_board
            )

            if linked_targets:

                # ==================================================
                # Позиция после нашего хода.
                # ==================================================

                test_board = pv_board.copy(
                    stack=False
                )

                try:

                    test_board.push(move)

                except Exception:

                    continue

                # ==================================================
                # Проверяем все найденные конструкции.
                # ==================================================

                for info in linked_targets:

                    target_sq = info[
                        "target_square"
                    ]

                    slider_sq = info[
                        "slider_square"
                    ]

                    behind_sq = info[
                        "behind_square"
                    ]

                    # --------------------------------------------------
                    # Фигура target до хода.
                    # --------------------------------------------------

                    target_before = (
                        pv_board.piece_at(
                            target_sq
                        )
                    )

                    if target_before is None:
                        continue

                    if target_before.color == board.turn:
                        continue

                    # --------------------------------------------------
                    # Target после нашего хода должна существовать.
                    # --------------------------------------------------

                    target_after = (
                        test_board.piece_at(
                            target_sq
                        )
                    )

                    if target_after is None:
                        continue

                    if target_after.color == board.turn:
                        continue

                    if (
                        target_after.piece_type
                        != target_before.piece_type
                    ):
                        continue

                    # ==================================================
                    # SLIDER ДО ХОДА
                    # ==================================================

                    slider_before = (
                        pv_board.piece_at(
                            slider_sq
                        )
                    )

                    if slider_before is None:
                        continue

                    if slider_before.color != board.turn:
                        continue

                    if slider_before.piece_type not in (
                        chess.BISHOP,
                        chess.ROOK,
                        chess.QUEEN,
                    ):
                        continue

                    # ==================================================
                    # SLIDER ПОСЛЕ ХОДА
                    # ==================================================

                    slider_after = (
                        test_board.piece_at(
                            slider_sq
                        )
                    )

                    if slider_after is None:
                        continue

                    if slider_after.color != board.turn:
                        continue

                    if (
                        slider_after.piece_type
                        != slider_before.piece_type
                    ):
                        continue

                    # ==================================================
                    # АТАКИ НА TARGET ДО И ПОСЛЕ
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

                    # --------------------------------------------------
                    # Новая атака.
                    # --------------------------------------------------

                    newly_attacked = (
                        len(attackers_before) == 0
                        and
                        len(attackers_after) > 0
                    )

                    # --------------------------------------------------
                    # Появился дополнительный атакующий.
                    # --------------------------------------------------

                    more_attackers = (
                        len(attackers_after)
                        >
                        len(attackers_before)
                    )

                    # ==================================================
                    # Проверяем, атакует ли target именно сделавшая
                    # ход пешка.
                    # ==================================================

                    pawn_attacks_target = False

                    if moving_piece.piece_type == chess.PAWN:

                        moved_piece_after = (
                            test_board.piece_at(
                                move.to_square
                            )
                        )

                        if (
                            moved_piece_after is not None
                            and
                            moved_piece_after.color
                            == board.turn
                            and
                            moved_piece_after.piece_type
                            == chess.PAWN
                        ):

                            pawn_attacks_target = (
                                target_sq in
                                test_board.attacks(
                                    move.to_square
                                )
                            )

                    # ==================================================
                    # Проверяем, атакует ли target сама сделавшая ход
                    # фигура.
                    # ==================================================

                    piece_attacks_target = False

                    moved_piece_after = (
                        test_board.piece_at(
                            move.to_square
                        )
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

                    # ==================================================
                    # Создано ли вообще давление?
                    # ==================================================

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
                    # ПРОВЕРЯЕМ BEHIND ПОСЛЕ УСИЛИВАЮЩЕГО ХОДА
                    # ==================================================

                    behind_piece_after = (
                        test_board.piece_at(
                            behind_sq
                        )
                    )

                    if behind_piece_after is None:
                        continue

                    if (
                        behind_piece_after.color
                        == board.turn
                    ):
                        continue

                    if (
                        behind_piece_after.piece_type
                        == chess.KING
                    ):
                        continue

                    # --------------------------------------------------
                    # Target должна быть более дешёвой.
                    # --------------------------------------------------

                    target_value = piece_values.get(
                        target_before.piece_type,
                        0
                    )

                    behind_value = piece_values.get(
                        behind_piece_after.piece_type,
                        0
                    )

                    if behind_value <= target_value:
                        continue

                    # ==================================================
                    # Теперь самое важное.
                    #
                    # Мы НЕ просто удаляем target и смотрим,
                    # открылась ли линия.
                    #
                    # Сначала ищем РЕАЛЬНЫЙ ЛЕГАЛЬНЫЙ ХОД target,
                    # которым она может уйти.
                    # ==================================================

                    target_escape_move = None
                    board_after_target_escape = None

                    for candidate in list(
                        test_board.legal_moves
                    ):

                        if (
                            candidate.from_square
                            != target_sq
                        ):
                            continue

                        # --------------------------------------------------
                        # После хода target она действительно должна
                        # покинуть исходное поле.
                        # --------------------------------------------------

                        if (
                            candidate.to_square
                            == target_sq
                        ):
                            continue

                        candidate_board = (
                            test_board.copy(
                                stack=False
                            )
                        )

                        try:

                            candidate_board.push(
                                candidate
                            )

                        except Exception:

                            continue

                        # --------------------------------------------------
                        # Target должна уйти.
                        # --------------------------------------------------

                        target_after_escape = (
                            candidate_board.piece_at(
                                target_sq
                            )
                        )

                        if target_after_escape is not None:
                            continue

                        # --------------------------------------------------
                        # Наша slider-фигура должна всё ещё существовать.
                        # --------------------------------------------------

                        slider_after_escape = (
                            candidate_board.piece_at(
                                slider_sq
                            )
                        )

                        if slider_after_escape is None:
                            continue

                        if (
                            slider_after_escape.color
                            != board.turn
                        ):
                            continue

                        if (
                            slider_after_escape.piece_type
                            != slider_before.piece_type
                        ):
                            continue

                        # --------------------------------------------------
                        # Behind-фигура должна всё ещё существовать.
                        # --------------------------------------------------

                        behind_after_escape = (
                            candidate_board.piece_at(
                                behind_sq
                            )
                        )

                        if behind_after_escape is None:
                            continue

                        if (
                            behind_after_escape.color
                            == board.turn
                        ):
                            continue

                        if (
                            behind_after_escape.piece_type
                            == chess.KING
                        ):
                            continue

                        # ==================================================
                        # Ищем КОНКРЕТНЫЙ ЛЕГАЛЬНЫЙ capture:
                        #
                        # slider -> behind
                        #
                        # Если такого хода нет, мотив не считается
                        # доказанным.
                        # ==================================================

                        capture_move = None

                        for candidate_capture in list(
                            candidate_board.legal_moves
                        ):

                            if (
                                candidate_capture.from_square
                                != slider_sq
                            ):
                                continue

                            if (
                                candidate_capture.to_square
                                != behind_sq
                            ):
                                continue

                            if not candidate_board.is_capture(
                                candidate_capture
                            ):
                                continue

                            capture_move = (
                                candidate_capture
                            )

                            break

                        if capture_move is None:
                            continue

                        # --------------------------------------------------
                        # Реальное взятие найдено.
                        # --------------------------------------------------

                        target_escape_move = candidate
                        board_after_target_escape = (
                            candidate_board
                        )

                        break

                    # ==================================================
                    # Если target вообще не может уйти так,
                    # чтобы открыть реальное взятие behind,
                    # этот мотив не подтверждён.
                    # ==================================================

                    if target_escape_move is None:
                        continue

                    if board_after_target_escape is None:
                        continue

                    # ==================================================
                    # Получаем SAN усиливающего хода.
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

                    # ==================================================
                    # SAN ухода target.
                    # ==================================================

                    try:

                        target_escape_move_san = (
                            test_board.san(
                                target_escape_move
                            )
                        )

                    except Exception:

                        target_escape_move_san = None

                    # ==================================================
                    # SAN будущего взятия behind.
                    # ==================================================

                    capture_move = None

                    for candidate_capture in list(
                        board_after_target_escape.legal_moves
                    ):

                        if (
                            candidate_capture.from_square
                            == slider_sq
                            and
                            candidate_capture.to_square
                            == behind_sq
                            and
                            board_after_target_escape.is_capture(
                                candidate_capture
                            )
                        ):

                            capture_move = (
                                candidate_capture
                            )

                            break

                    if capture_move is None:
                        continue

                    try:

                        capture_move_san = (
                            board_after_target_escape.san(
                                capture_move
                            )
                        )

                    except Exception:

                        capture_move_san = None

                    # ==================================================
                    # УСПЕШНО НАШЛИ МОТИВ
                    # ==================================================

                    return {
                        "type": "material_pressure",

                        "text": (
                            "Так вы теряете материал. "
                            "У вас была возможность выиграть материал, "
                            "постепенно усиливая давление на связанную фигуру."
                        ),

                        "target_piece": name_of(
                            target_before
                        ),

                        "target_square": (
                            chess.square_name(
                                target_sq
                            )
                        ),

                        "attacker_piece": name_of(
                            slider_after
                        ),

                        "attacker_square": (
                            chess.square_name(
                                slider_sq
                            )
                        ),

                        "behind_piece": name_of(
                            behind_piece_after
                        ),

                        "behind_square": (
                            chess.square_name(
                                behind_sq
                            )
                        ),

                        "strengthening_move": move,

                        "strengthening_move_san": (
                            strengthening_move_san
                        ),

                        "target_escape_move": (
                            target_escape_move
                        ),

                        "target_escape_move_san": (
                            target_escape_move_san
                        ),

                        "capture_behind_move": (
                            capture_move
                        ),

                        "capture_behind_move_san": (
                            capture_move_san
                        ),

                        "attacker_count_before": (
                            len(attackers_before)
                        ),

                        "attacker_count_after": (
                            len(attackers_after)
                        ),

                        "target_value": (
                            target_value
                        ),

                        "behind_value": (
                            behind_value
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