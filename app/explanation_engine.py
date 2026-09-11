
import chess

from app.pawn_structure_detector import (
    detect_pawn_structure_damage,
    get_pawn_structure_text,
)

from app.explanation_utils import (
    PIECE_NAMES,
    PIECE_VALUES,
    piece_value,
    piece_name,
    get_move_piece,
    get_captured_piece,
    make_position_after,
    get_best_move,
    CENTER_SQUARES,
    PIECE_NAMES,
)

from app.explanation_detectors import (
    detect_equal_trade_info,
    detect_material_gain,
    detect_castling,
    detect_mate,
    detect_check,
    detect_tempo_material_loss,

    find_newly_attacked_piece_info,
    find_pawn_attack_threat,
    find_queen_tempo,
    detect_equal_trade,
    get_equal_trade_text,
    detect_center_pawn_move,
    _find_pin_material_sequence,
    detect_pin_material_loss,
    get_pin_material_loss_text,
    detect_apparent_piece_loss_but_recapturable,
    detect_newly_pinned_pawn,
    detect_queen_activity,
    detect_open_file_rook_idea,
    detect_neutralized_opponent_plan,
    detect_forced_piece_loss_after_pawn_tempo,
    get_apparent_piece_loss_text,
    find_attacked_piece_after_move,
    find_attacked_piece,
    king_is_in_check,
    detect_active_queen_move,
    square_lies_between,
    detect_clearance_followup_idea,
    detect_newly_undefended_pawn,
    get_clearance_followup_text,
    generate_best_move_idea,
    analyze_move_consequences,
    find_piece_tempo_attack,
    detect_isolated_pawn_after_move,
    detect_forced_piece_loss,
    detect_trapped_piece,
    detect_pawn_loss,
    detect_inaccuracy_no_benefit,
    detect_delayed_capture,
    detect_add_defender_to_vulnerable_pawn,
    detect_material_pressure_on_linked_piece,
)


def generate_explanation(mistake):

    played = mistake.get("played_san", "")
    best = mistake.get("best", "")
    before = mistake.get("before_score")
    after = mistake.get("after_score")
    loss = mistake.get("loss", 0)

    alternatives = mistake.get("alternatives") or []

    played_results = mistake.get(
        "played_results",
        []
    )

    equivalent_best_moves = mistake.get(
        "equivalent_best_moves"
    ) or []

    print(
        "DEBUG EQUIVALENT FROM MISTAKE:",
        equivalent_best_moves
    )

    equivalent_best_sans = []

    for item in equivalent_best_moves:

        if not isinstance(item, dict):
            continue

        san = item.get("san") or ""

        if not san:
            continue

        if best and san == best:
            continue

        if san in equivalent_best_sans:
            continue

        equivalent_best_sans.append(san)

    print(
        "DEBUG EQUIVALENT SANS:",
        equivalent_best_sans
    )

    position_before = mistake.get(
        "position_before"
    )

    features = mistake.get(
        "features"
    ) or {}

    pawn_structure_info = (
        mistake.get(
            "pawn_structure_info"
        )
        or features.get(
            "pawn_structure_info"
        )
    )

    try:
        loss = float(loss)
    except Exception:
        loss = 0

    try:
        before = float(before)
    except Exception:
        before = None

    try:
        after = float(after)
    except Exception:
        after = None

    # ======================================================
    # NO POSITION
    # ======================================================

    if not position_before:

        parts = []

        if played and best:

            if equivalent_best_sans:

                parts.append(
                    f"Вы сыграли {played}, "
                    f"но сильнее было {best}. "
                    f"Также практически ту же оценку "
                    f"сохранял ход "
                    f"{equivalent_best_sans[0]}."
                )

            else:

                parts.append(
                    f"Вы сыграли {played}, "
                    f"но сильнее было {best}."
                )

        elif played:

            parts.append(
                f"Вы сыграли {played}."
            )

        elif best:

            parts.append(
                f"Лучшим ходом было {best}."
            )

        return "".join(parts).strip()

    # ======================================================
    # BASIC POSITION DATA
    # ======================================================

    was_in_check_before = (
        position_before.is_check()
    )

    best_move = get_best_move(
        mistake,
        position_before
    )

    played_move = None

    try:

        if played:

            played_move = (
                position_before.parse_san(
                    played
                )
            )

    except Exception as e:

        print(
            "PLAYED MOVE PARSE ERROR:",
            repr(e)
        )

    board_after_played = None

    try:

        if played_move:

            board_after_played = (
                make_position_after(
                    position_before,
                    played_move
                )
            )

    except Exception as e:

        print(
            "BOARD AFTER PLAYED ERROR:",
            repr(e)
        )

    if board_after_played is None:

        try:

            board_after_played = (
                position_before.copy()
            )

        except Exception:

            board_after_played = None

    # ======================================================
    # REASONS
    # ======================================================

    reasons = []

    def add_reason(
        reason_type,
        priority,
        text,
        data=None
    ):

        if not text:
            return

        reasons.append(
            {
                "type": reason_type,
                "priority": priority,
                "text": text,
                "data": data,
            }
        )

    # ======================================================
    # 1. MATE AFTER OUR MOVE
    # ======================================================

    mate_blunder = False

    try:

        if board_after_played:

            mate_blunder = (
                board_after_played.is_checkmate()
            )

    except Exception:

        mate_blunder = False

    if mate_blunder:

        add_reason(
            "mate_blunder",
            120,
            "Вы позволили сопернику поставить вам мат."
        )

    # ======================================================
    # 2. MATE IN ONE
    # ======================================================

    mate_in_one_info = None

    if (
        board_after_played
        and not mate_blunder
    ):

        try:

            for enemy_move in (
                board_after_played.legal_moves
            ):

                try:

                    if not board_after_played.gives_check(
                        enemy_move
                    ):
                        continue

                    test_board = (
                        board_after_played.copy()
                    )

                    test_board.push(
                        enemy_move
                    )

                    if test_board.is_checkmate():

                        mate_in_one_info = {
                            "move": enemy_move,
                            "san": (
                                board_after_played.san(
                                    enemy_move
                                )
                            ),
                        }

                        break

                except Exception:
                    continue

        except Exception:
            pass

    if mate_in_one_info:

        add_reason(
            "mate_in_one",
            112,
            (
                "После вашего хода соперник "
                f"может поставить мат ходом "
                f"{mate_in_one_info['san']}."
            ),
            mate_in_one_info
        )

    # ======================================================
    # 3. UNDEFENDED PAWN
    # ======================================================

    try:

        undefended_pawn_info = (
            detect_newly_undefended_pawn(
                position_before,
                board_after_played,
                played_move
            )
        )

    except Exception as e:

        print(
            "UNDEFENDED PAWN ERROR:",
            repr(e)
        )

        undefended_pawn_info = None

    if undefended_pawn_info:

        pawn_square = (
            undefended_pawn_info.get(
                "square"
            )
        )

        capture_san = (
            undefended_pawn_info.get(
                "capture_san"
            )
        )

        pawn_square_name = (
            chess.square_name(
                pawn_square
            )
            if pawn_square is not None
            else ""
        )

        if capture_san:

            undefended_text = (
                f"После {played} пешка на "
                f"{pawn_square_name} осталась "
                f"без достаточной защиты, и "
                f"соперник может забрать её "
                f"ходом {capture_san}."
            )

        else:

            undefended_text = (
                f"После {played} пешка на "
                f"{pawn_square_name} осталась "
                "без прежней защиты."
            )

        add_reason(
            "undefended_pawn",
            60,
            undefended_text,
            undefended_pawn_info
        )

    # ======================================================
    # 4. PIN -> MATERIAL LOSS
    # ======================================================

    try:

        pin_material_loss_info = (
            detect_pin_material_loss(
                position_before,
                board_after_played,
                played_move,
                loss
            )
        )

    except Exception as e:

        print(
            "PIN MATERIAL LOSS ERROR:",
            repr(e)
        )

        pin_material_loss_info = None

    if pin_material_loss_info:

        try:

            pin_text = (
                get_pin_material_loss_text(
                    pin_material_loss_info
                )
            )

        except Exception:

            pin_text = None

        if pin_text:

            add_reason(
                "pin_material_loss",
                97,
                pin_text,
                pin_material_loss_info
            )

    # ======================================================
    # 5. INDEPENDENT NEW PIN
    # ======================================================

    if (
        board_after_played
        and played_move
    ):

        try:

            our_color = not board_after_played.turn

            for square in board_after_played.pieces(
                chess.KNIGHT,
                our_color
            ) | board_after_played.pieces(
                chess.BISHOP,
                our_color
            ) | board_after_played.pieces(
                chess.ROOK,
                our_color
            ) | board_after_played.pieces(
                chess.QUEEN,
                our_color
            ):

                try:

                    piece = board_after_played.piece_at(
                        square
                    )

                    if not piece:
                        continue

                    if not board_after_played.is_pinned(
                        our_color,
                        square
                    ):
                        continue

                    attacker_square = None
                    attacker_piece = None

                    king_square = (
                        board_after_played.king(
                            our_color
                        )
                    )

                    if king_square is None:
                        continue

                    direction = (
                        chess.square_file(square)
                        - chess.square_file(king_square),
                        chess.square_rank(square)
                        - chess.square_rank(king_square),
                    )

                    step_file = (
                        0
                        if direction[0] == 0
                        else (
                            1
                            if direction[0] > 0
                            else -1
                        )
                    )

                    step_rank = (
                        0
                        if direction[1] == 0
                        else (
                            1
                            if direction[1] > 0
                            else -1
                        )
                    )

                    if (
                        step_file == 0
                        and step_rank == 0
                    ):
                        continue

                    f = (
                        chess.square_file(square)
                        + step_file
                    )

                    r = (
                        chess.square_rank(square)
                        + step_rank
                    )

                    while (
                        0 <= f <= 7
                        and 0 <= r <= 7
                    ):

                        sq = chess.square(
                            f,
                            r
                        )

                        p = (
                            board_after_played.piece_at(
                                sq
                            )
                        )

                        if p:

                            if (
                                p.color != our_color
                                and p.piece_type in (
                                    chess.BISHOP,
                                    chess.ROOK,
                                    chess.QUEEN,
                                )
                            ):

                                attacker_square = sq
                                attacker_piece = p

                            break

                        f += step_file
                        r += step_rank

                    if (
                        attacker_square is None
                        or attacker_piece is None
                    ):
                        continue

                    capture_move = chess.Move(
                        attacker_square,
                        square
                    )

                    if (
                        capture_move
                        not in board_after_played.legal_moves
                    ):
                        continue

                    capture_san = (
                        board_after_played.san(
                            capture_move
                        )
                    )

                    pinned_piece_name = (
                        chess.piece_name(
                            piece.piece_type
                        )
                    )

                    attacker_name = (
                        chess.piece_name(
                            attacker_piece.piece_type
                        )
                    )

                    pinned_square_name = (
                        chess.square_name(
                            square
                        )
                    )

                    attacker_square_name = (
                        chess.square_name(
                            attacker_square
                        )
                    )

                    text = (
                        f"После {played} соперник "
                        f"может связать вашего "
                        f"{pinned_piece_name} на "
                        f"{pinned_square_name} "
                        f"с королём атакой "
                        f"{attacker_name} с "
                        f"{attacker_square_name} "
                        f"и затем выиграть эту фигуру "
                        f"ходом {capture_san}."
                    )

                    add_reason(
                        "pin_material_loss",
                        98,
                        text
                    )

                    break

                except Exception:
                    continue

        except Exception as e:

            print(
                "INDEPENDENT PIN ERROR:",
                repr(e)
            )

    # ======================================================
    # 6. APPARENT PIECE LOSS
    # ======================================================

    apparent_piece_loss_info = None

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
            "APPARENT PIECE LOSS ERROR:",
            repr(e)
        )

        apparent_piece_loss_info = None

    apparent_piece_loss_is_real = (
        apparent_piece_loss_info is not None
    )

    if apparent_piece_loss_info:

        try:

            opponent_move = (
                apparent_piece_loss_info.get(
                    "opponent_move"
                )
            )

            if opponent_move:

                test_board = (
                    board_after_played.copy()
                )

                if (
                    opponent_move
                    not in test_board.legal_moves
                ):
                    apparent_piece_loss_is_real = False

                else:

                    attacker_square = (
                        opponent_move.from_square
                    )

                    test_board.push(
                        opponent_move
                    )

                    recapturable = False

                    for recapture in (
                        test_board.legal_moves
                    ):

                        if (
                            recapture.to_square
                            != attacker_square
                        ):
                            continue

                        recapture_test = (
                            test_board.copy()
                        )

                        recapture_test.push(
                            recapture
                        )

                        if not recapture_test.is_check():
                            recapturable = True
                            break

                    if recapturable:
                        apparent_piece_loss_is_real = False

            else:

                found_recapture = False

                for enemy_move in (
                    board_after_played.legal_moves
                ):

                    if not board_after_played.is_capture(
                        enemy_move
                    ):
                        continue

                    attacker_square = (
                        enemy_move.from_square
                    )

                    test_board = (
                        board_after_played.copy()
                    )

                    test_board.push(
                        enemy_move
                    )

                    for recapture in (
                        test_board.legal_moves
                    ):

                        if (
                            recapture.to_square
                            != attacker_square
                        ):
                            continue

                        recapture_test = (
                            test_board.copy()
                        )

                        recapture_test.push(
                            recapture
                        )

                        if not recapture_test.is_check():

                            found_recapture = True
                            break

                    if found_recapture:
                        break

                if found_recapture:
                    apparent_piece_loss_is_real = False

        except Exception as e:

            print(
                "APPARENT PIECE LOSS VALIDATION ERROR:",
                repr(e)
            )

    if (
        apparent_piece_loss_info
        and apparent_piece_loss_is_real
    ):

        try:

            apparent_text = (
                get_apparent_piece_loss_text(
                    apparent_piece_loss_info
                )
            )

        except Exception:

            apparent_text = None

        if apparent_text:

            add_reason(
                "apparent_piece_loss",
                72,
                apparent_text,
                apparent_piece_loss_info
            )

    elif apparent_piece_loss_info:

        print(
            "APPARENT PIECE LOSS ОТМЕНЁН: "
            "обнаружен полноценный ответный размен."
        )

    # ======================================================
    # 7. OPEN FILE ROOK
    # ======================================================

    try:

        open_file_rook_info = (
            detect_open_file_rook_idea(
                position_before,
                best_move,
                played_move
            )
        )

    except Exception as e:

        print(
            "OPEN FILE ROOK ERROR:",
            repr(e)
        )

        open_file_rook_info = None

    if open_file_rook_info:

        add_reason(
            "open_file_rook",
            80,
            open_file_rook_info
            if isinstance(
                open_file_rook_info,
                str
            )
            else open_file_rook_info.get(
                "text",
                ""
            ),
            open_file_rook_info
        )

    # ======================================================
    # 6.4. ДОБАВЛЕНИЕ ЗАЩИТНИКА К УЯЗВИМОЙ ПЕШКЕ
    # ======================================================

    add_defender_info = None

    if (
        played_move
        and best_move
        and position_before
        and not was_in_check_before
        and not mate_blunder
    ):

        try:

            add_defender_info = (
                detect_add_defender_to_vulnerable_pawn(
                    position_before,
                    best_move,
                    played_move
                )
            )

        except Exception as e:

            print(
                "ADD DEFENDER ERROR:",
                repr(e)
            )

            add_defender_info = None

    if add_defender_info:

        defender_text = (
            add_defender_info.get(
                "text",
                ""
            )
        )

        if defender_text:

            add_reason(
                "add_defender_to_vulnerable_pawn",
                116,
                defender_text,
                add_defender_info
            )

            print(
                "ADD DEFENDER FOUND:",
                defender_text
            )

    # ======================================================
    # 8. DELAYED CAPTURE
    # ======================================================

    delayed_capture_info = None

    try:

        if (
            position_before
            and played_move
            and best_move
        ):

            delayed_capture_info = (
                detect_delayed_capture(
                    position_before,
                    played_move,
                    best_move
                )
            )

    except Exception as e:

        print(
            "DELAYED CAPTURE ERROR:",
            repr(e)
        )

        delayed_capture_info = None


    # ======================================================
    # ОБЪЕДИНЕНИЕ:
    #
    # add_defender_to_vulnerable_pawn
    # +
    # delayed_capture
    #
    # Если оба найдены — оставляем только
    # add_defender_and_delayed_capture.
    # ======================================================

    if delayed_capture_info:

        delayed_text = (
            delayed_capture_info.get(
                "text",
                ""
            )
        )

        if delayed_text:

            if add_defender_info:

                best_san = (
                    add_defender_info.get(
                        "best_san"
                    )
                    or delayed_capture_info.get(
                        "best_san"
                    )
                    or ""
                )

                pawn_square_name = (
                    add_defender_info.get(
                        "pawn_square_name"
                    )
                    or ""
                )

                captured_piece_name = (
                    delayed_capture_info.get(
                        "captured_piece_name"
                    )
                    or "фигуру"
                )

                # --------------------------------------------------
                # Клетка, на которой была взята фигура.
                #
                # Например:
                # Nxc6 -> c6
                # --------------------------------------------------

                captured_square_name = ""

                try:

                    if played_move:

                        captured_square_name = (
                            chess.square_name(
                                played_move.to_square
                            )
                        )

                except Exception:

                    captured_square_name = ""

                # --------------------------------------------------
                # Формируем объединённое объяснение.
                # --------------------------------------------------

                if (
                    pawn_square_name
                    and captured_square_name
                ):

                    combined_text = (
                        f"Лучше было сыграть {best_san}, "
                        f"добавляя защитника к уязвимой "
                        f"пешке на {pawn_square_name}. "
                        f"После этого взятие "
                        f"{captured_piece_name} "
                        f"на {captured_square_name} всё ещё "
                        f"оставалось возможным."
                    )

                elif pawn_square_name:

                    combined_text = (
                        f"Лучше было сыграть {best_san}, "
                        f"добавляя защитника к уязвимой "
                        f"пешке на {pawn_square_name}. "
                        f"После этого ваше взятие всё ещё "
                        f"оставалось возможным."
                    )

                else:

                    combined_text = delayed_text

                # --------------------------------------------------
                # Объединяем данные обоих детекторов.
                # --------------------------------------------------

                combined_info = dict(
                    delayed_capture_info
                )

                combined_info.update(
                    add_defender_info
                )

                combined_info[
                    "type"
                ] = "add_defender_and_delayed_capture"

                combined_info[
                    "delayed_capture"
                ] = delayed_capture_info

                combined_info[
                    "add_defender"
                ] = add_defender_info

                combined_info[
                    "text"
                ] = combined_text

                # --------------------------------------------------
                # ВАЖНО:
                #
                # add_defender_to_vulnerable_pawn уже был добавлен
                # выше. Удаляем его, чтобы одновременно не получить:
                #
                # 1. add_defender_to_vulnerable_pawn
                # 2. add_defender_and_delayed_capture
                #
                # Должно остаться только объединённое объяснение.
                # --------------------------------------------------

                reasons = [
                    item
                    for item in reasons
                    if item.get("type")
                    != "add_defender_to_vulnerable_pawn"
                ]

                add_reason(
                    "add_defender_and_delayed_capture",
                    116,
                    combined_text,
                    combined_info
                )

                print(
                    "COMBINED REASON FOUND:",
                    combined_text
                )

            else:

                # --------------------------------------------------
                # Если добавления защитника нет,
                # оставляем обычный delayed_capture.
                # --------------------------------------------------

                add_reason(
                    "delayed_capture",
                    115,
                    delayed_text,
                    delayed_capture_info
                )

                print(
                    "DELAYED CAPTURE FOUND:",
                    delayed_text
                )

        print(
            "DELAYED CAPTURE FOUND:",
            delayed_capture_info
        )


    # ======================================================
    # ПРИОРИТЕТЫ ВТОРИЧНЫХ ОБЪЯСНЕНИЙ
    # ======================================================

    for item in reasons:

        if item["type"] in {
            "tempo_material_loss",
            "piece_attack",
            "piece_tempo_attack",
            "pawn_attack",
            "pawn_piece_attack",
            "queen_tempo",
            "best_move_idea",
        }:

            item["priority"] = 0

    # ======================================================
    # ПЕРВЫЙ ОТВЕТ STOCKFISH
    # ======================================================

    preferred_reply = None

    try:

        if played_results:

            pv = played_results[0].get(
                "pv",
                []
            )

            if pv:
                preferred_reply = pv[0]

    except Exception as e:

        print(
            "PREFERRED REPLY ERROR:",
            repr(e)
        )

        preferred_reply = None

    print(
        "DEBUG PREFERRED REPLY:",
        preferred_reply
    )

    # ======================================================
    # 8.5. НОВАЯ СВЯЗКА ПЕШКИ
    # ======================================================

    newly_pinned_pawn_info = None

    try:

        if (
            position_before
            and board_after_played
            and played_move
            and not was_in_check_before
            and not mate_blunder
        ):

            newly_pinned_pawn_info = (
                detect_newly_pinned_pawn(
                    position_before,
                    board_after_played,
                    played_move,
                    preferred_move=preferred_reply
                )
            )

    except Exception as e:

        print(
            "NEWLY PINNED PAWN ERROR:",
            repr(e)
        )

        newly_pinned_pawn_info = None

    # ======================================================
    # NORMALIZE NEWLY PINNED PAWN SQUARE
    # ======================================================

    if isinstance(newly_pinned_pawn_info, dict):

        if newly_pinned_pawn_info.get("pawn_square") is None:

            target_square = (
                newly_pinned_pawn_info.get(
                    "target_square"
                )
            )

            if target_square is not None:

                newly_pinned_pawn_info["pawn_square"] = (
                    target_square
                )

    if newly_pinned_pawn_info:

        pin_text = (
            newly_pinned_pawn_info.get(
                "text",
                ""
            )
        )

        if pin_text:

            # --------------------------------------------------
            # Если найденная связка совпадает с первым ответом
            # Stockfish, делаем её приоритетнее material.
            #
            # Обычная геометрическая связка остаётся на 89.
            # --------------------------------------------------

            pin_priority = 89

            try:

                pin_move = (
                    newly_pinned_pawn_info.get(
                        "pin_move"
                    )
                )

                if (
                    preferred_reply is not None
                    and pin_move == preferred_reply
                ):

                    pin_priority = 96

            except Exception:

                pin_priority = 89

            add_reason(
                "newly_pinned_pawn",
                pin_priority,
                pin_text,
                newly_pinned_pawn_info
            )

            print(
                "NEWLY PINNED PAWN FOUND:",
                pin_text
            )

            print(
                "NEWLY PINNED PAWN PRIORITY:",
                pin_priority
            )

    # ======================================================
    # 9. EQUAL TRADE
    # ======================================================

    equal_trade_info = None

    try:

        equal_trade_info = (
            detect_equal_trade_info(
                position_before,
                best_move
            )
        )

    except Exception as e:

        print(
            "EQUAL TRADE ERROR:",
            repr(e)
        )

        equal_trade_info = None

    equal_trade = (
        equal_trade_info is not None
    )

    # ======================================================
    # 9.5. EQUIVALENT MOVE WITH CLEAR PIECE TRADE
    # ======================================================
    #
    # Stockfish может показать один лучший ход,
    # например dxc5, хотя среди equivalent_best_moves
    # есть другой практически равноценный ход, например
    # Bxd6.
    #
    # Для объяснения второй ход иногда намного понятнее:
    #
    #     best = dxc5
    #     equivalent = Bxd6
    #
    # Если Bxd6 означает размен слонов, объяснение должно
    # говорить именно об этой идее, а не механически
    # объяснять dxc5.
    #
    # ВАЖНО:
    #
    # best_move НЕ изменяется.
    # Этот блок влияет только на объяснение.
    # ======================================================

    equivalent_trade_info = None

    try:

        if (
            position_before
            and equivalent_best_moves
        ):

            for item in equivalent_best_moves:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                san = (
                    item.get("san")
                    or ""
                ).strip()

                if not san:
                    continue

                # best уже является основным ходом Stockfish.
                if (
                    best
                    and san == best
                ):
                    continue

                try:

                    candidate_move = (
                        position_before.parse_san(
                            san
                        )
                    )

                except Exception:

                    continue

                # Нас интересуют только взятия.
                try:

                    if not position_before.is_capture(
                        candidate_move
                    ):
                        continue

                except Exception:

                    continue

                moving_piece = (
                    position_before.piece_at(
                        candidate_move.from_square
                    )
                )

                if not moving_piece:
                    continue

                # --------------------------------------------------
                # Определяем, какая фигура была взята.
                #
                # Для en passant это не обычное поле назначения,
                # поэтому учитываем его отдельно.
                # --------------------------------------------------

                captured_square = (
                    candidate_move.to_square
                )

                try:

                    if position_before.is_en_passant(
                        candidate_move
                    ):

                        captured_square = (
                            candidate_move.to_square
                            + (
                                -8
                                if position_before.turn
                                else 8
                            )
                        )

                except Exception:

                    pass

                captured_piece = (
                    position_before.piece_at(
                        captured_square
                    )
                )

                if not captured_piece:
                    continue

                # --------------------------------------------------
                # Нас интересует именно размен одинаковых фигур:
                #
                # B x B
                # R x R
                # Q x Q
                # N x N
                #
                # Пешки здесь специально не учитываем.
                # --------------------------------------------------

                piece_types_for_trade = {
                    chess.BISHOP,
                    chess.KNIGHT,
                    chess.ROOK,
                    chess.QUEEN,
                }

                if (
                    moving_piece.piece_type
                    not in piece_types_for_trade
                ):
                    continue

                if (
                    captured_piece.piece_type
                    != moving_piece.piece_type
                ):
                    continue

                # --------------------------------------------------
                # Проверяем, что после взятия соперник действительно
                # может ответить взятием этой же фигуры.
                #
                # Это отличает настоящий размен от обычного
                # взятия фигуры.
                # --------------------------------------------------

                trade_board = (
                    position_before.copy()
                )

                trade_board.push(
                    candidate_move
                )

                recapture_move = None

                for response in (
                    trade_board.legal_moves
                ):

                    if (
                        response.to_square
                        != candidate_move.to_square
                    ):
                        continue

                    # Должно быть взятие нашей фигуры.
                    try:

                        if not trade_board.is_capture(
                            response
                        ):
                            continue

                    except Exception:

                        continue

                    recapture_move = response
                    break

                if recapture_move is None:
                    continue

                # --------------------------------------------------
                # Получаем SAN ответного взятия.
                # --------------------------------------------------

                try:

                    recapture_san = (
                        trade_board.san(
                            recapture_move
                        )
                    )

                except Exception:

                    recapture_san = ""

                piece_name = (
                    chess.piece_name(
                        moving_piece.piece_type
                    )
                )

                square_name = (
                    chess.square_name(
                        candidate_move.to_square
                    )
                )

                # --------------------------------------------------
                # Формируем объяснение.
                # --------------------------------------------------

                if (
                    moving_piece.piece_type
                    == chess.BISHOP
                ):

                    trade_text = (
                        f"Одним из практически равноценных "
                        f"продолжений было {san}: "
                        f"вы могли разменять слона на "
                        f"слона на {square_name}. "
                        f"После {san} соперник мог ответить "
                        f"{recapture_san}, поэтому идея "
                        "заключалась в размене слонов."
                    )

                else:

                    trade_text = (
                        f"Одним из практически равноценных "
                        f"продолжений было {san}: "
                        f"вы могли разменять "
                        f"{piece_name} на "
                        f"{piece_name} на {square_name}. "
                        f"После {san} соперник мог ответить "
                        f"{recapture_san}, то есть речь "
                        "шла о размене фигур."
                    )

                equivalent_trade_info = {
                    "san": san,
                    "move": candidate_move,
                    "recapture_move": recapture_move,
                    "recapture_san": recapture_san,
                    "piece_type": moving_piece.piece_type,
                    "piece_name": piece_name,
                    "square": candidate_move.to_square,
                    "square_name": square_name,
                    "text": trade_text,
                }

                # Берём первый подходящий эквивалентный размен.
                break

    except Exception as e:

        print(
            "EQUIVALENT TRADE ERROR:",
            repr(e)
        )

        equivalent_trade_info = None

    if equivalent_trade_info:

        add_reason(
            "equivalent_trade_idea",
            70,
            equivalent_trade_info.get(
                "text",
                ""
            ),
            equivalent_trade_info
        )

        print(
            "=============================================="
        )

        print(
            "EQUIVALENT TRADE IDEA FOUND"
        )

        print(
            "BEST =",
            best
        )

        print(
            "EQUIVALENT =",
            equivalent_trade_info.get(
                "san"
            )
        )

        print(
            "PIECE =",
            equivalent_trade_info.get(
                "piece_name"
            )
        )

        print(
            "RECAPTURE =",
            equivalent_trade_info.get(
                "recapture_san"
            )
        )

        print(
            "=============================================="
        )

    # ======================================================
    # 10. PAWN THREAT
    # ======================================================

    pawn_threat = (
        mistake.get(
            "pawn_threat_explanation"
        )
        or features.get(
            "pawn_threat_explanation"
        )
    )

    # ======================================================
    # 11. TEMPO + MATERIAL
    # ======================================================

    try:

        tempo_material_info = (
            detect_tempo_material_loss(
                position_before,
                played_move,
                best_move,
                best
            )
        )

    except Exception as e:

        print(
            "TEMPO MATERIAL ERROR:",
            repr(e)
        )

        tempo_material_info = None

    if tempo_material_info:

        tempo_text = (
            tempo_material_info
            if isinstance(
                tempo_material_info,
                str
            )
            else tempo_material_info.get(
                "text",
                ""
            )
        )

        if tempo_text:

            add_reason(
                "tempo_material_loss",
                91,
                tempo_text,
                tempo_material_info
            )

    # ======================================================
    # PAWN LOSS
    # ======================================================

    try:
        pawn_loss_info = detect_pawn_loss(mistake)
    except Exception as e:
        print(
            "PAWN LOSS ERROR:",
            repr(e)
        )
        pawn_loss_info = None

    if pawn_loss_info:
        pawn_loss_text = (
            pawn_loss_info
            if isinstance(
                pawn_loss_info,
                str
            )
            else pawn_loss_info.get(
                "text",
                ""
            )
        )

        if pawn_loss_text:
            add_reason(
                "pawn_loss",
                105,
                pawn_loss_text,
                pawn_loss_info
            )

    # ======================================================
    # PAWN LOSS vs NEWLY PINNED PAWN
    #
    # Если теряется именно та пешка, которую соперник
    # сначала связывает, значит главная причина — связка.
    #
    # Если теряется другая пешка, pawn_loss остаётся
    # самостоятельной причиной.
    # ======================================================

    if pawn_loss_info and newly_pinned_pawn_info:

        try:

            pawn_loss_square = (
                pawn_loss_info.get(
                    "pawn_square"
                )
            )

            pinned_pawn_square = (
                newly_pinned_pawn_info.get(
                    "pawn_square"
                )
            )

            # На случай, если detector сохранил
            # клетку под именем target_square.
            if pinned_pawn_square is None:

                pinned_pawn_square = (
                    newly_pinned_pawn_info.get(
                        "target_square"
                    )
                )

            print(
                "DEBUG PAWN LOSS vs PIN:",
                "pawn_loss_square =",
                pawn_loss_square,
                "pinned_pawn_square =",
                pinned_pawn_square
            )

            # --------------------------------------------------
            # ОДНА И ТА ЖЕ ПЕШКА
            # --------------------------------------------------

            if (
                pawn_loss_square is not None
                and pinned_pawn_square is not None
                and pawn_loss_square == pinned_pawn_square
            ):

                print(
                    "DEBUG: PAWN LOSS IS CAUSED BY NEW PIN"
                )

                for item in reasons:

                    if (
                        item.get("type")
                        == "newly_pinned_pawn"
                    ):

                        # Pawn loss = 105.
                        # Связка должна быть немного выше.
                        item["priority"] = max(
                            item.get(
                                "priority",
                                0
                            ),
                            106
                        )

                        print(
                            "DEBUG: NEW PIN PRIORITY "
                            "RAISED TO 106"
                        )

                        break

            # --------------------------------------------------
            # РАЗНЫЕ ПЕШКИ
            # --------------------------------------------------

            else:

                print(
                    "DEBUG: PAWN LOSS AND PIN "
                    "ARE DIFFERENT PAWNS"
                )

        except Exception as e:

            print(
                "PAWN LOSS / PIN COMPARISON ERROR:",
                repr(e)
            )

    # ======================================================
    # 12. FORCED PIECE LOSS AFTER PAWN TEMPO
    # ======================================================

    try:

        forced_after_pawn_tempo = (
            detect_forced_piece_loss_after_pawn_tempo(
                mistake
            )
        )

    except Exception as e:

        print(
            "FORCED AFTER PAWN TEMPO ERROR:",
            repr(e)
        )

        forced_after_pawn_tempo = None

    if forced_after_pawn_tempo:

        forced_text = (
            forced_after_pawn_tempo
            if isinstance(
                forced_after_pawn_tempo,
                str
            )
            else forced_after_pawn_tempo.get(
                "text",
                ""
            )
        )

        if forced_text:

            add_reason(
                "forced_piece_loss",
                95,
                forced_text,
                forced_after_pawn_tempo
            )

    # ======================================================
    # 13. NEW ATTACK / PAWN ATTACK
    # ======================================================

    newly_attacked_info = None
    pawn_attack_info = None

    if board_after_played:

        our_color = not board_after_played.turn

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
                "NEWLY ATTACKED ERROR:",
                repr(e)
            )

            newly_attacked_info = None

        try:

            pawn_attack_info = (
                find_pawn_attack_threat(
                    position_before,
                    board_after_played,
                    our_color
                )
            )

        except Exception as e:

            print(
                "PAWN ATTACK ERROR:",
                repr(e)
            )

            pawn_attack_info = None

        # --------------------------------------------------
        # PAWN ATTACK FILTER
        # --------------------------------------------------

        if (
            pawn_attack_info
            and not newly_attacked_info
        ):

            try:

                target_square = (
                    pawn_attack_info.get(
                        "square"
                    )
                )

                attacker_square = (
                    pawn_attack_info.get(
                        "attacker_square"
                    )
                )

                # Не считаем обычным "позволили атаковать",
                # если фигура только что сама пришла
                # на эту клетку.
                if (
                    played_move
                    and target_square
                    == played_move.to_square
                ):

                    pawn_attack_info = None

                else:

                    exchange_possible = False

                    pawn_move = (
                        pawn_attack_info.get(
                            "pawn_move"
                        )
                    )

                    if pawn_move:

                        test_board = (
                            board_after_played.copy()
                        )

                        if (
                            pawn_move
                            in test_board.legal_moves
                        ):

                            test_board.push(
                                pawn_move
                            )

                            if attacker_square is not None:

                                for recapture in (
                                    test_board.legal_moves
                                ):

                                    if (
                                        recapture.to_square
                                        != attacker_square
                                    ):
                                        continue

                                    recapture_test = (
                                        test_board.copy()
                                    )

                                    recapture_test.push(
                                        recapture
                                    )

                                    if not recapture_test.is_check():

                                        exchange_possible = True
                                        break

                    if exchange_possible:
                        pawn_attack_info = None

            except Exception as e:

                print(
                    "PAWN ATTACK FILTER ERROR:",
                    repr(e)
                )

        if pawn_attack_info:

            newly_attacked_info = {
                "piece_name": pawn_attack_info.get(
                    "piece_name"
                ),
                "piece_type": pawn_attack_info.get(
                    "piece_type"
                ),
                "square": pawn_attack_info.get(
                    "square"
                ),
                "attacker_type": chess.PAWN,
                "attacker_square": pawn_attack_info.get(
                    "attacker_square"
                ),
                "pawn_move": pawn_attack_info.get(
                    "pawn_move"
                ),
                "is_pawn_threat": True,
            }

    if newly_attacked_info:

        attacked_piece_name = (
            newly_attacked_info.get(
                "piece_name"
            )
            or "фигуру"
        )

        if newly_attacked_info.get(
            "is_pawn_threat"
        ):

            add_reason(
                "pawn_piece_attack",
                55,
                (
                    f"Вы позволили сопернику "
                    f"атаковать вашего "
                    f"{attacked_piece_name} "
                    "пешкой."
                ),
                newly_attacked_info
            )

        else:

            square = newly_attacked_info.get(
                "square"
            )

            square_name = ""

            try:

                if square is not None:

                    square_name = (
                        chess.square_name(
                            square
                        )
                    )

            except Exception:
                pass

            add_reason(
                "piece_attack",
                65,
                (
                    f"После {played} ваш "
                    f"{attacked_piece_name} "
                    f"на {square_name} "
                    "оказывается под новой атакой."
                ),
                newly_attacked_info
            )

    # ======================================================
    # ЕСЛИ ОБНАРУЖЕНА НОВАЯ СВЯЗКА ПЕШКИ,
    # УБИРАЕМ ОБЩИЕ ОБЪЯСНЕНИЯ ПРО АТАКУ.
    # ======================================================

    if newly_pinned_pawn_info:

        reasons = [
            item
            for item in reasons
            if item.get("type") not in {
                "piece_attack",
                "pawn_attack",
                "pawn_piece_attack",
            }
        ]

        print(
            "NEWLY PINNED PAWN: "
            "удалены общие причины "
            "piece_attack/pawn_attack"
        )

    # ======================================================
    # 14. NEW CHECK THREAT
    # ======================================================

    new_check_threat_info = None

    if (
        board_after_played
        and not mate_blunder
    ):

        try:

            opponent_moves = []

            for enemy_move in (
                board_after_played.legal_moves
            ):

                try:

                    if not board_after_played.gives_check(
                        enemy_move
                    ):
                        continue

                    test_board = (
                        board_after_played.copy()
                    )

                    captured_piece = None
                    captured_square = (
                        enemy_move.to_square
                    )

                    if board_after_played.is_en_passant(
                        enemy_move
                    ):

                        captured_square = (
                            enemy_move.to_square
                            + (
                                -8
                                if board_after_played.turn
                                else 8
                            )
                        )

                    captured_piece = (
                        board_after_played.piece_at(
                            captured_square
                        )
                    )

                    test_board.push(
                        enemy_move
                    )

                    if test_board.is_checkmate():
                        continue

                    # Если атакующую фигуру можно
                    # немедленно забрать без шаха себе,
                    # это не считаем полноценной угрозой.
                    attacker_square = (
                        enemy_move.to_square
                    )

                    can_capture_attacker = False

                    for response in (
                        test_board.legal_moves
                    ):

                        if (
                            response.to_square
                            != attacker_square
                        ):
                            continue

                        response_test = (
                            test_board.copy()
                        )

                        response_test.push(
                            response
                        )

                        if not response_test.is_check():

                            can_capture_attacker = True
                            break

                    if can_capture_attacker:
                        continue

                    attacker_piece = (
                        board_after_played.piece_at(
                            enemy_move.from_square
                        )
                    )

                    attacker_value = 0

                    if attacker_piece:

                        attacker_value = {
                            chess.QUEEN: 5,
                            chess.ROOK: 4,
                            chess.BISHOP: 3,
                            chess.KNIGHT: 2,
                            chess.PAWN: 1,
                        }.get(
                            attacker_piece.piece_type,
                            0
                        )

                    opponent_moves.append(
                        (
                            attacker_value,
                            enemy_move,
                            captured_piece,
                            captured_square,
                        )
                    )

                except Exception:
                    continue

            if opponent_moves:

                opponent_moves.sort(
                    key=lambda x: x[0],
                    reverse=True
                )

                (
                    _,
                    check_move,
                    captured_piece,
                    captured_square,
                ) = opponent_moves[0]

                check_san = (
                    board_after_played.san(
                        check_move
                    )
                )

                new_check_threat_info = {
                    "move": check_move,
                    "san": check_san,
                    "captured_piece": captured_piece,
                    "captured_square": captured_square,
                }

        except Exception as e:

            print(
                "NEW CHECK THREAT ERROR:",
                repr(e)
            )

            new_check_threat_info = None

    if new_check_threat_info:

        captured_piece = (
            new_check_threat_info.get(
                "captured_piece"
            )
        )

        captured_square = (
            new_check_threat_info.get(
                "captured_square"
            )
        )

        check_san = (
            new_check_threat_info.get(
                "san",
                ""
            )
        )

        if captured_piece:

            captured_piece_name = (
                chess.piece_name(
                    captured_piece.piece_type
                )
            )

            try:

                captured_square_name = (
                    chess.square_name(
                        captured_square
                    )
                )

            except Exception:

                captured_square_name = ""

            text = (
                f"После {played} вы позволили "
                f"сопернику забрать "
                f"{captured_piece_name} на "
                f"{captured_square_name} "
                f"с шахом {check_san}. "
                "Это одновременно лишает вас "
                "материала и позволяет сопернику "
                "продолжить атаку на вашего короля."
            )

        else:

            text = (
                f"После {played} вы позволили "
                f"сопернику получить новый шах "
                f"ходом {check_san}."
            )

        add_reason(
            "new_check_threat",
            80,
            text,
            new_check_threat_info
        )

    # ======================================================
    # 15. RESPONSE TO CHECK
    # ======================================================

    check_response_found = False

    if (
        was_in_check_before
        and best_move
        and played_move
    ):

        try:

            played_escapes_check = False
            best_escapes_check = False

            played_test = (
                position_before.copy()
            )

            played_test.push(
                played_move
            )

            if not played_test.is_check():
                played_escapes_check = True

            best_test = (
                position_before.copy()
            )

            best_test.push(
                best_move
            )

            if not best_test.is_check():
                best_escapes_check = True

            if best_escapes_check:

                if played_escapes_check:

                    check_text = (
                        f"После {played} вы выбрали "
                        "не лучший способ уйти "
                        f"из-под шаха. Лучшим ходом "
                        f"было {best}."
                    )

                else:

                    check_text = (
                        f"После {played} вы неправильно "
                        "отреагировали на шах. "
                        f"Лучшим ходом было {best} — "
                        "именно так стоило уйти "
                        "из-под шаха."
                    )

                add_reason(
                    "check_response",
                    105,
                    check_text
                )

                check_response_found = True

        except Exception as e:

            print(
                "CHECK RESPONSE ERROR:",
                repr(e)
            )

    # ======================================================
    # 16. BEST MOVE = MATE
    # ======================================================

    if (
        best_move
        and detect_mate(
            position_before,
            best_move
        )
    ):

        add_reason(
            "mate",
            100,
            (
                f"Ход {best} сразу ставит мат. "
                "Это было решающее тактическое "
                "продолжение."
            )
        )

    # ======================================================
    # 17. BEST MOVE = CHECK
    # ======================================================

    if (
        best_move
        and not was_in_check_before
        and not mate_blunder
        and not mate_in_one_info
    ):

        try:

            best_check_board = (
                position_before.copy()
            )

            best_check_board.push(
                best_move
            )

            if best_check_board.is_check():

                add_reason(
                    "check",
                    83,
                    (
                        f"После {played} вы упустили "
                        f"возможность создать шах "
                        f"ходом {best}. Этот ход "
                        "заставлял соперника "
                        "немедленно реагировать."
                    )
                )

        except Exception as e:

            print(
                "BEST CHECK ERROR:",
                repr(e)
            )

    # ======================================================
    # 18. MATERIAL GAIN
    # ======================================================

    try:

        captured_name = (
            detect_material_gain(
                position_before,
                best_move
            )
        )

    except Exception as e:

        print(
            "MATERIAL GAIN ERROR:",
            repr(e)
        )

        captured_name = None

    if captured_name:

        add_reason(
            "material",
            94,
            (
                f"Лучшим было забрать "
                f"{captured_name} ходом {best}."
            )
        )

    # ======================================================
    # 19. FORK
    # ======================================================

    fork_info = None

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

                test_board = (
                    position_before.copy()
                )

                test_board.push(
                    best_move
                )

                knight_square = (
                    best_move.to_square
                )

                targets = []

                for target_square in (
                    test_board.attacks(
                        knight_square
                    )
                ):

                    target_piece = (
                        test_board.piece_at(
                            target_square
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

                    targets.append(
                        (
                            {
                                chess.QUEEN: 9,
                                chess.ROOK: 5,
                                chess.BISHOP: 3,
                                chess.KNIGHT: 3,
                            }.get(
                                target_piece.piece_type,
                                0
                            ),
                            target_piece,
                            target_square,
                        )
                    )

                if len(targets) >= 2:

                    targets.sort(
                        key=lambda x: x[0],
                        reverse=True
                    )

                    first = targets[0]
                    second = targets[1]

                    first_name = (
                        chess.piece_name(
                            first[1].piece_type
                        )
                    )

                    second_name = (
                        chess.piece_name(
                            second[1].piece_type
                        )
                    )

                    first_square = (
                        test_board.square_name(
                            first[2]
                        )
                    )

                    second_square = (
                        test_board.square_name(
                            second[2]
                        )
                    )

                    fork_info = {
                        "targets": targets
                    }

                    add_reason(
                        "fork",
                        95,
                        (
                            f"После {played} вы упустили "
                            f"возможность сыграть {best}. "
                            f"После этого хода конь "
                            f"одновременно атакует "
                            f"{first_name} на "
                            f"{first_square} и "
                            f"{second_name} на "
                            f"{second_square}, "
                            "создавая вилку."
                        ),
                        fork_info
                    )

        except Exception as e:

            print(
                "FORK ERROR:",
                repr(e)
            )

    # ======================================================
    # 20.5. GRADUAL PRESSURE ON PINNED PIECE
    # ======================================================

    try:

        material_pressure_info = (
            detect_material_pressure_on_linked_piece(
                board=position_before,
                played_move=played_move,
                best_move=best_move,
                played_results=played_results,
                best_pv=(
                    mistake.get("best_pv")
                    or mistake.get("best_line")
                    or mistake.get("pv")
                ),
                loss=loss
            )
        )

    except Exception as e:

        print(
            "MATERIAL PRESSURE ERROR:",
            repr(e)
        )

        material_pressure_info = None

    if material_pressure_info:

        material_pressure_text = (
            material_pressure_info
            if isinstance(
                material_pressure_info,
                str
            )
            else material_pressure_info.get(
                "text",
                ""
            )
        )

        if material_pressure_text:

            add_reason(
                "material_pressure",
                109,
                material_pressure_text,
                material_pressure_info
            )

    # ======================================================
    # 21. FORCED PIECE LOSS
    # ======================================================

    try:

        forced_piece_loss_info = (
            detect_forced_piece_loss(
                board=position_before,
                played_move=played_move,
                played_results=played_results
            )
        )

    except Exception as e:

        print(
            "FORCED PIECE LOSS ERROR:",
            repr(e)
        )

        forced_piece_loss_info = None

    if forced_piece_loss_info:

        forced_piece_loss_text = (
            forced_piece_loss_info
            if isinstance(
                forced_piece_loss_info,
                str
            )
            else forced_piece_loss_info.get(
                "text",
                ""
            )
        )

        if forced_piece_loss_text:

            add_reason(
                "forced_piece_loss",
                110,
                forced_piece_loss_text,
                forced_piece_loss_info
            )

    # ======================================================
    # 22. TRAPPED PIECE
    # ======================================================

    try:

        trapped_piece_info = (
            detect_trapped_piece(
                board=board_after_played,
                played_results=played_results
            )
        )

    except Exception as e:

        print(
            "TRAPPED PIECE ERROR:",
            repr(e)
        )

        trapped_piece_info = None

    if trapped_piece_info:

        trapped_text = (
            trapped_piece_info
            if isinstance(
                trapped_piece_info,
                str
            )
            else trapped_piece_info.get(
                "text",
                ""
            )
        )

        if trapped_text:

            add_reason(
                "trapped_piece",
                85,
                trapped_text,
                trapped_piece_info
            )

    # ======================================================
    # 23. PIECE ATTACK WITH TEMPO
    # ======================================================

    try:

        piece_tempo_attack_info = (
            find_piece_tempo_attack(
                board_after=board_after_played,
                played_move=played_move,
                played_results=played_results,
                our_color=(
                    not board_after_played.turn
                    if board_after_played
                    else None
                )
            )
        )

    except Exception as e:

        print(
            "PIECE TEMPO ATTACK ERROR:",
            repr(e)
        )

        piece_tempo_attack_info = None

    if piece_tempo_attack_info:

        piece_tempo_text = (
            piece_tempo_attack_info
            if isinstance(
                piece_tempo_attack_info,
                str
            )
            else piece_tempo_attack_info.get(
                "text",
                ""
            )
        )

        if piece_tempo_text:

            add_reason(
                "piece_tempo_attack",
                78,
                piece_tempo_text,
                piece_tempo_attack_info
            )


    # ======================================================
    # 23.5. QUEEN ACTIVITY
    # ======================================================

    queen_activity_info = None

    try:

        queen_activity_info = (
            detect_queen_activity(
                position_before=position_before,
                board_after_played=board_after_played,
                played_move=played_move,
                played_results=played_results
            )
        )

    except Exception as e:

        print(
            "QUEEN ACTIVITY ERROR:",
            repr(e)
        )

        queen_activity_info = None

    if queen_activity_info:

        queen_san = (
            queen_activity_info.get(
                "san"
            )
            or ""
        )

        queen_to = (
            queen_activity_info.get(
                "to_name"
            )
            or ""
        )

        if (
            queen_activity_info.get(
                "newly_enabled"
            )
        ):

            queen_activity_text = (
                f"После {played} вы позволили "
                f"сопернику активизировать ферзя "
                f"ходом {queen_san}"
            )

        else:

            queen_activity_text = (
                f"После {played} соперник "
                f"получил возможность значительно "
                f"улучшить позицию ферзя ходом "
                f"{queen_san}"
            )

        if queen_to:

            queen_activity_text += (
                f", переведя его на более "
                f"активное поле {queen_to}"
            )

        queen_activity_text += "."

        add_reason(
            "queen_activity",
            82,
            queen_activity_text,
            queen_activity_info
        )

        print(
            "=============================================="
        )

        print(
            "QUEEN ACTIVITY FOUND"
        )

        print(
            "PLAYED =",
            played
        )

        print(
            "QUEEN MOVE =",
            queen_activity_info.get(
                "san"
            )
        )

        print(
            "QUEEN FROM =",
            queen_activity_info.get(
                "from_name"
            )
        )

        print(
            "QUEEN TO =",
            queen_activity_info.get(
                "to_name"
            )
        )

        print(
            "NEWLY ENABLED =",
            queen_activity_info.get(
                "newly_enabled"
            )
        )

        print(
            "BEFORE ACTIVITY =",
            queen_activity_info.get(
                "before_activity"
            )
        )

        print(
            "AFTER ACTIVITY =",
            queen_activity_info.get(
                "after_activity"
            )
        )

        print(
            "ACTIVITY GAIN =",
            queen_activity_info.get(
                "activity_gain"
            )
        )

        print(
            "=============================================="
        )

    # ======================================================
    # 24. NEUTRALIZED PLAN
    # ======================================================

    try:

        neutralized_plan_info = (
            detect_neutralized_opponent_plan(
                mistake
            )
        )

    except Exception as e:

        print(
            "NEUTRALIZED PLAN ERROR:",
            repr(e)
        )

        neutralized_plan_info = None

    if neutralized_plan_info:

        neutralized_text = (
            neutralized_plan_info
            if isinstance(
                neutralized_plan_info,
                str
            )
            else neutralized_plan_info.get(
                "text",
                ""
            )
        )

        if neutralized_text:

            add_reason(
                "neutralized_plan",
                75,
                neutralized_text,
                neutralized_plan_info
            )

    # ======================================================
    # 25. PAWN THREAT
    # ======================================================

    if (
        pawn_threat
        and not any(
            item.get("type")
            == "pawn_piece_attack"
            for item in reasons
        )
    ):

        add_reason(
            "pawn_attack",
            55,
            pawn_threat
        )

    # ======================================================
    # 26. CENTER
    # ======================================================

    try:

        center_pawn_move = (
            detect_center_pawn_move(
                position_before,
                best_move
            )
        )

    except Exception as e:

        print(
            "CENTER ERROR:",
            repr(e)
        )

        center_pawn_move = False

    if center_pawn_move:

        center_priority = 35

        try:

            if (
                pawn_attack_info
                and played_move
                and pawn_attack_info.get(
                    "square"
                ) == played_move.to_square
            ):

                center_priority = 75

            elif pawn_threat:

                center_priority = 70

        except Exception:
            pass

        add_reason(
            "center",
            center_priority,
            (
                f"Лучшим было ударить по центру "
                f"пешкой ходом {best}. Ваш ход "
                "позволил сопернику сохранить "
                "больше свободы в центре."
            )
        )

    # ======================================================
    # 27. FREE PAWN
    # ======================================================

    free_pawn_explanation = (
        mistake.get(
            "free_pawn_explanation"
        )
        or features.get(
            "free_pawn_explanation"
        )
    )

    if free_pawn_explanation:

        add_reason(
            "free_pawn",
            55,
            free_pawn_explanation
        )

    # ======================================================
    # 28. BAD RECAPTURE
    # ======================================================

    bad_recapture_explanation = (
        mistake.get(
            "bad_recapture_explanation"
        )
        or features.get(
            "bad_recapture_explanation"
        )
    )

    if bad_recapture_explanation:

        add_reason(
            "bad_recapture",
            50,
            bad_recapture_explanation
        )

    # ======================================================
    # 29. CASTLING
    # ======================================================

    try:

        castling_needed = (
            detect_castling(
                position_before,
                best_move
            )
        )

    except Exception as e:

        print(
            "CASTLING ERROR:",
            repr(e)
        )

        castling_needed = False

    if castling_needed:

        add_reason(
            "king_safety",
            30,
            (
                f"В этой позиции важнее было "
                f"обезопасить короля ходом {best}."
            )
        )

    # ======================================================
    # 30. PAWN KING SAFETY
    # ======================================================

    pawn_king_safety_info = None

    try:

        if (
            played_move
            and position_before
        ):

            played_piece = (
                position_before.piece_at(
                    played_move.from_square
                )
            )

            if (
                played_piece
                and played_piece.piece_type
                == chess.PAWN
            ):

                king_square = (
                    position_before.king(
                        played_piece.color
                    )
                )

                if king_square is not None:

                    king_file = (
                        chess.square_file(
                            king_square
                        )
                    )

                    king_rank = (
                        chess.square_rank(
                            king_square
                        )
                    )

                    source_file = (
                        chess.square_file(
                            played_move.from_square
                        )
                    )

                    source_rank = (
                        chess.square_rank(
                            played_move.from_square
                        )
                    )

                    near_king = (
                        abs(
                            source_file
                            - king_file
                        ) <= 2
                        and (
                            (
                                played_piece.color
                                == chess.WHITE
                                and source_rank <= 2
                            )
                            or
                            (
                                played_piece.color
                                == chess.BLACK
                                and source_rank >= 5
                            )
                        )
                    )

                    if near_king:

                        pawn_king_safety_info = {
                            "source_square":
                                played_move.from_square,
                            "king_square":
                                king_square,
                        }

    except Exception as e:

        print(
            "PAWN KING SAFETY ERROR:",
            repr(e)
        )

    if pawn_king_safety_info:

        add_reason(
            "pawn_king_safety",
            88,
            (
                "Пешки — это первая линия "
                "обороны вашего короля; их "
                "перемещение создаёт ненужные "
                "риски."
            ),
            pawn_king_safety_info
        )

    # ======================================================
    # 31. GENERAL BEST MOVE IDEA
    # ======================================================

    try:

        best_idea = (
            generate_best_move_idea(
                position_before,
                best_move,
                best
            )
        )

    except Exception as e:

        print(
            "BEST MOVE IDEA ERROR:",
            repr(e)
        )

        best_idea = None

    if best_idea:

        add_reason(
            "best_move_idea",
            20,
            best_idea
        )

    # ======================================================
    # 32. QUEEN TRADE
    # ======================================================

    queen_trade_best_move = False

    try:

        if best_move:

            best_piece = (
                position_before.piece_at(
                    best_move.from_square
                )
            )

            if (
                best_piece
                and best_piece.piece_type
                == chess.QUEEN
            ):

                queen_test = (
                    position_before.copy()
                )

                queen_test.push(
                    best_move
                )

                for enemy_move in (
                    queen_test.legal_moves
                ):

                    if (
                        enemy_move.to_square
                        == best_move.to_square
                        and queen_test.is_capture(
                            enemy_move
                        )
                    ):

                        queen_trade_best_move = True
                        break

    except Exception as e:

        print(
            "QUEEN TRADE ERROR:",
            repr(e)
        )

    if queen_trade_best_move:

        for item in reasons:

            if item["type"] == "new_check_threat":

                item["priority"] = min(
                    item["priority"],
                    45
                )

    # ======================================================
    # 33. ISOLATED PAWN
    # ======================================================

    try:

        isolated_pawn_info = (
            detect_isolated_pawn_after_move(
                board_before=position_before,
                board_after=board_after_played,
                played_move=played_move,
                best_move=best_move
            )
        )

    except Exception as e:

        print(
            "ISOLATED PAWN ERROR:",
            repr(e)
        )

        isolated_pawn_info = None

    if isolated_pawn_info:

        isolated_text = (
            isolated_pawn_info
            if isinstance(
                isolated_pawn_info,
                str
            )
            else isolated_pawn_info.get(
                "text",
                ""
            )
        )

        if isolated_text:

            add_reason(
                "isolated_pawn",
                96,
                isolated_text,
                isolated_pawn_info
            )

    # ======================================================
    # 34. CONCRETE MATERIAL PRIORITIES
    # ======================================================

    concrete_material_types = {
        "pin_material_loss",
        "material_pressure",
        "apparent_piece_loss",
        "tempo_material_loss",
        "forced_piece_loss",
        "delayed_capture",
        "material",
        "fork",
    }

    has_concrete_material_reason = any(
        item.get("type")
        in concrete_material_types
        and item.get("priority", 0) > 0
        for item in reasons
    )

    if has_concrete_material_reason:

        for item in reasons:

            reason_type = item.get(
                "type"
            )

            if reason_type == "forced_piece_loss":

                item["priority"] = max(
                    item["priority"],
                    110
                )

            elif reason_type == "material_pressure":

                item["priority"] = max(
                    item["priority"],
                    109
                )

            elif reason_type == "delayed_capture":

                item["priority"] = max(
                    item["priority"],
                    96
                )

            elif reason_type in {
                "pawn_attack",
                "pawn_piece_attack",
                "piece_attack",
                "undefended_pawn",
                "queen_tempo",
            }:

                item["priority"] = min(
                    item["priority"],
                    50
                )

            elif reason_type == "piece_tempo_attack":

                item["priority"] = min(
                    item["priority"],
                    72
                )

            elif reason_type == "new_check_threat":

                if (
                    item.get("data")
                    and item["data"].get(
                        "captured_piece"
                    )
                ):

                    item["priority"] = max(
                        item["priority"],
                        80
                    )

                else:

                    item["priority"] = min(
                        item["priority"],
                        50
                    )

    # ======================================================
    # 34.5. INACCURACY WITHOUT CONCRETE BENEFIT
    # ======================================================
    #
    # ВАЖНО:
    #
    # Этот детектор добавляется ПОСЛЕ существующих
    # конкретных причин.
    #
    # Поэтому он не пытается самостоятельно определять
    # форки, связки, потери материала и т. п.
    #
    # Его задача:
    #
    #   "ход немного хуже, но конкретной тактической
    #    причины для этого нет."
    #
    # Приоритет 68:
    #
    #   выше generic piece_attack = 65
    #   ниже конкретных тактических причин.
    #
    # ======================================================

    inaccuracy_no_benefit = None

    concrete_reason_types = {
        "mate_blunder",
        "mate_in_one",
        "mate",
        "check_response",
        "check",
        "material",
        "fork",
        "pin_material_loss",
        "material_pressure",
        "forced_piece_loss",
        "delayed_capture",
        "tempo_material_loss",
        "apparent_piece_loss",
        "new_check_threat",
        "isolated_pawn",
        "undefended_pawn",
        "trapped_piece",
        "piece_tempo_attack",
        "piece_attack",
        "pawn_piece_attack",
        "pawn_attack",
        "queen_tempo",
        "queen_activity",
        "free_pawn",
        "bad_recapture",
        "open_file_rook",
        "pawn_king_safety",
    }

    has_concrete_reason = any(
        item.get("type") in concrete_reason_types
        and item.get("priority", 0) > 0
        for item in reasons
    )

    if (
        not has_concrete_reason
        and position_before
        and played_move
        and best_move
        and not was_in_check_before
        and not mate_blunder
        and not mate_in_one_info
    ):

        try:

            best_after_score = (
                mistake.get(
                    "best_after_score"
                )
            )

            if best_after_score is None:

                best_result = (
                    mistake.get(
                        "best_result"
                    )
                )

                if isinstance(
                    best_result,
                    dict
                ):

                    best_after_score = (
                        best_result.get(
                            "score"
                        )
                        or best_result.get(
                            "after_score"
                        )
                    )

            # --------------------------------------------------
            # ВАЖНО:
            #
            # Не используем здесь внешнюю переменную `best`.
            # SAN получаем непосредственно из позиции.
            # --------------------------------------------------

            try:

                played_san_for_inaccuracy = (
                    position_before.san(
                        played_move
                    )
                )

            except Exception:

                played_san_for_inaccuracy = played

            try:

                best_san_for_inaccuracy = (
                    position_before.san(
                        best_move
                    )
                )

            except Exception:

                best_san_for_inaccuracy = best

            # --------------------------------------------------
            # Если сыгранный ход уже считается равноценным,
            # отдельная "неточность" не нужна.
            # --------------------------------------------------

            is_equivalent = False

            for item in equivalent_best_moves:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                san = (
                    item.get("san")
                    or ""
                ).strip()

                if not san:
                    continue

                if (
                    san
                    == played_san_for_inaccuracy
                ):

                    is_equivalent = True
                    break

            if not is_equivalent:

                try:

                    if (
                        played_move
                        == best_move
                    ):

                        is_equivalent = True

                except Exception:
                    pass

            if not is_equivalent:

                # --------------------------------------------------
                # Проверяем, что best — тихий позиционный ход.
                # --------------------------------------------------

                best_is_quiet = True

                try:

                    if position_before.is_capture(
                        best_move
                    ):

                        best_is_quiet = False

                    if position_before.gives_check(
                        best_move
                    ):

                        best_is_quiet = False

                except Exception:

                    best_is_quiet = False

                if best_is_quiet:

                    # --------------------------------------------------
                    # Если после best оценка известна,
                    # проверяем, что best действительно улучшает
                    # позицию относительно before.
                    #
                    # Для белых:
                    #     больше = лучше
                    #
                    # Для чёрных:
                    #     меньше = лучше
                    #
                    # Поэтому здесь нужно учитывать POV Stockfish.
                    # В твоей системе before/after обычно уже
                    # хранятся относительно стороны игрока.
                    # --------------------------------------------------

                    positional_improvement = True

                    if (
                        best_after_score is not None
                        and before is not None
                    ):

                        try:

                            best_after_score = float(
                                best_after_score
                            )

                            before_score_for_best = float(
                                before
                            )

                            improvement = (
                                best_after_score
                                - before_score_for_best
                            )

                            # Оценка считается POV игрока.
                            # Небольшой допуск против шума Stockfish.
                            if improvement < 5:

                                positional_improvement = False

                        except Exception:

                            positional_improvement = True

                    if positional_improvement:

                        # --------------------------------------------------
                        # Близкие хорошие ходы.
                        #
                        # Они не обязательны для срабатывания.
                        # Если есть — формулировка будет мягче.
                        # --------------------------------------------------

                        close_alternatives = []

                        for san in (
                            equivalent_best_sans
                        ):

                            if not san:
                                continue

                            if (
                                san
                                == played_san_for_inaccuracy
                            ):
                                continue

                            if (
                                san
                                == best_san_for_inaccuracy
                            ):
                                continue

                            if san in close_alternatives:
                                continue

                            close_alternatives.append(
                                san
                            )

                        if close_alternatives:

                            inaccuracy_text = (
                                f"Ход "
                                f"{played_san_for_inaccuracy} "
                                "был допустим, но "
                                f"{best_san_for_inaccuracy} "
                                "позволял получить "
                                "более благоприятную "
                                "позицию. При этом "
                                "были и другие близкие "
                                "по силе продолжения."
                            )

                        else:

                            inaccuracy_text = (
                                f"Ход "
                                f"{played_san_for_inaccuracy} "
                                "был допустим, но "
                                f"{best_san_for_inaccuracy} "
                                "был немного точнее "
                                "и позволял улучшить "
                                "позицию. Здесь не было "
                                "непосредственной "
                                "тактической потери."
                            )

                        inaccuracy_no_benefit = {
                            "text": inaccuracy_text,
                            "played_move": played_move,
                            "best_move": best_move,
                            "loss": loss,
                            "has_close_alternatives": bool(
                                close_alternatives
                            ),
                            "alternative_count": len(
                                close_alternatives
                            ),
                        }

        except Exception as e:

            print(
                "INACCURACY NO BENEFIT ERROR:",
                repr(e)
            )

            inaccuracy_no_benefit = None

    if inaccuracy_no_benefit:

        add_reason(
            "inaccuracy_no_benefit",
            68,
            inaccuracy_no_benefit.get(
                "text",
                ""
            ),
            inaccuracy_no_benefit
        )

        print(
            "INACCURACY NO BENEFIT FOUND:",
            inaccuracy_no_benefit
        )

    # ======================================================
    # 35. MATE IN ONE PRIORITY
    # ======================================================

    if (
        mate_in_one_info
        and not mate_blunder
    ):

        for item in reasons:

            if item["type"] == "mate_in_one":

                item["priority"] = 115

            elif item["type"] == "new_check_threat":

                item["priority"] = min(
                    item["priority"],
                    85
                )

    # ======================================================
    # 36. CHECK RESPONSE PRIORITY
    # ======================================================

    if (
        check_response_found
        and not mate_blunder
    ):

        for item in reasons:

            if item["type"] == "check_response":

                item["priority"] = 105

            elif item["type"] == "mate_in_one":

                item["priority"] = 115

            else:

                item["priority"] = min(
                    item["priority"],
                    90
                )

    # ======================================================
    # INACCURACY WITHOUT CONCRETE TACTICAL BENEFIT
    # ======================================================
    #
    # Идея:
    # Небольшая потеря оценки сама по себе не означает
    # конкретную тактическую ошибку.
    #
    # Если ход:
    #   - потерял 30-79 cp,
    #   - не является взятием,
    #   - не даёт шах/мат,
    #   - не приводит к потере материала,
    #   - не создаёт вилку/связку/жертву,
    #   - не является серьёзной тактической угрозой,
    #   - и при этом лучший ход действительно улучшает позицию,
    #
    # то считаем это позиционной неточностью.
    #
    # Приоритет 68:
    #   выше обычных piece_attack / pawn_attack,
    #   но ниже конкретных тактических объяснений.
    # ======================================================

    inaccuracy_no_benefit = False

    if (
        30 <= loss < 80
        and best_move is not None
        and played_move is not None
        and position_before is not None
    ):

        # --------------------------------------------------
        # 1. Сыгранный ход не должен быть взятием
        # --------------------------------------------------
        played_is_capture = False

        try:
            played_is_capture = position_before.is_capture(
                played_move
            )
        except Exception:
            played_is_capture = False

        # --------------------------------------------------
        # 2. Сыгранный ход не должен давать шах
        # --------------------------------------------------
        played_gives_check = False

        try:
            test_board = position_before.copy()
            test_board.push(played_move)
            played_gives_check = test_board.is_check()
        except Exception:
            played_gives_check = False

        # --------------------------------------------------
        # 3. Лучший ход не должен быть тем же самым ходом
        # --------------------------------------------------
        same_as_best = (
            played_move == best_move
        )

        # --------------------------------------------------
        # 4. Проверяем равноценность сыгранного хода
        #
        # Важный момент:
        # equivalent_best_moves содержит ходы, которые
        # уже признаны системой практически равноценными.
        # Если сыгранный ход там находится — это НЕ
        # inaccuracy_no_benefit.
        # --------------------------------------------------
        played_is_equivalent = False

        played_san_for_equivalent = played

        for item in equivalent_best_moves:
            if not isinstance(item, dict):
                continue

            item_san = item.get("san") or ""

            if (
                item_san
                and played_san_for_equivalent
                and item_san == played_san_for_equivalent
            ):
                played_is_equivalent = True
                break

        # --------------------------------------------------
        # 5. Проверяем конкретные тактические причины.
        #
        # Эти причины должны иметь приоритет над общей
        # позиционной неточностью.
        # --------------------------------------------------

        concrete_reason_types = {
            "mate_blunder",
            "mate_in_one",
            "mate",
            "check",
            "check_response",

            "material",
            "material_pressure",
            "tempo_material_loss",
            "forced_piece_loss",
            "apparent_piece_loss",
            "pin_material_loss",
            "fork",

            "delayed_capture",
            "queen_activity",
        }

        has_concrete_reason = any(
            r.get("type") in concrete_reason_types
            for r in reasons
        )

        # --------------------------------------------------
        # 6. Отдельно проверяем fork / pin по features.
        #
        # Это дополнительная защита на случай, если
        # соответствующий reason ещё не был добавлен.
        # --------------------------------------------------

        feature_has_fork = bool(
            features.get("fork")
        )

        feature_has_pin = bool(
            features.get("pin")
        )

        feature_has_sacrifice = bool(
            features.get("knight_sacrifice")
            or features.get("sacrifice")
        )

        # --------------------------------------------------
        # 7. Серьёзная угроза.
        #
        # Обычная атака фигуры или пешки НЕ считается
        # серьёзной угрозой — именно поэтому они могут
        # остаться вторичными объяснениями.
        # --------------------------------------------------

        serious_threat = False

        tactical_threats = mistake.get(
            "tactical_threats"
        ) or []

        if tactical_threats:
            serious_threat = True

        # Если уже есть конкретные тактические reason-типы,
        # тоже считаем угрозу конкретной.
        serious_threat_types = {
            "mate_in_one",
            "mate_blunder",
            "forced_piece_loss",
            "material_pressure",
            "tempo_material_loss",
            "fork",
            "pin_material_loss",
            "apparent_piece_loss",
        }

        if any(
            r.get("type") in serious_threat_types
            for r in reasons
        ):
            serious_threat = True

        # --------------------------------------------------
        # 8. Проверяем, что лучший ход действительно лучше
        # сыгранного.
        #
        # loss >= 30 уже говорит об ухудшении позиции.
        # Дополнительно смотрим BEST SCORE / AFTER SCORE,
        # если они доступны.
        # --------------------------------------------------

        best_really_improves = True

        if (
            after is not None
            and mistake.get("best_score") is not None
        ):
            try:
                best_score_value = float(
                    mistake.get("best_score")
                )
                after_value = float(after)

                # Здесь оценки уже должны быть приведены
                # к одной перспективе пользователем.
                #
                # Если сыгранная позиция хуже лучшей,
                # разница должна соответствовать loss.
                if abs(after_value - best_score_value) < 20:
                    best_really_improves = False

            except Exception:
                pass

        # --------------------------------------------------
        # 9. Наличие близких хороших ходов.
        #
        # НЕ делаем это обязательным условием.
        #
        # Если есть несколько близких ходов — это особенно
        # хороший признак того, что позиция была просто
        # неточно сыграна, а не что существовал единственный
        # "спасающий" ход.
        # --------------------------------------------------

        close_good_moves = []

        for item in equivalent_best_moves:
            if not isinstance(item, dict):
                continue

            san_value = item.get("san") or ""

            if not san_value:
                continue

            if best and san_value == best:
                continue

            try:
                difference = float(
                    item.get("difference", 999)
                )
            except Exception:
                difference = 999

            if difference <= 20:
                close_good_moves.append(
                    san_value
                )

        has_close_good_moves = bool(
            close_good_moves
        )

        # --------------------------------------------------
        # 10. Финальное условие
        # --------------------------------------------------

        if (
            not played_is_capture
            and not played_gives_check
            and not same_as_best
            and not played_is_equivalent
            and not has_concrete_reason
            and not feature_has_fork
            and not feature_has_pin
            and not feature_has_sacrifice
            and not serious_threat
            and best_really_improves
        ):

            # Дополнительная проверка:
            # если есть близкие хорошие ходы — это идеальный
            # случай для inaccuracy_no_benefit.
            #
            # Но отсутствие таких ходов НЕ запрещает
            # детектору работать.
            #
            # Это важно: иначе мы будем пропускать обычные
            # позиционные неточности, где Stockfish нашёл
            # один наиболее точный ход.

            text = (
                f"Ход {played} был неточным: "
                f"он не даёт конкретной тактической выгоды "
                f"и позволяет сопернику улучшить свою позицию."
            )

            if best:
                if has_close_good_moves:
                    text += (
                        f" Сильнее было {best}, "
                        "но в позиции было несколько близких "
                        "хороших продолжений."
                    )
                else:
                    text += (
                        f" Сильнее было {best}, "
                        "но это не означает, что только этот "
                        "ход сохранял позицию."
                    )

            add_reason(
                "inaccuracy_no_benefit",
                68,
                text,
                {
                    "loss": loss,
                    "best_move": best,
                    "played_move": played,
                    "close_good_moves": close_good_moves,
                    "has_close_good_moves": has_close_good_moves,
                }
            )

            inaccuracy_no_benefit = True

            print(
                "=============================================="
            )
            print(
                "INACCURACY NO BENEFIT FOUND"
            )
            print(
                "LOSS =",
                loss
            )
            print(
                "PLAYED =",
                played
            )
            print(
                "BEST =",
                best
            )
            print(
                "CLOSE GOOD MOVES =",
                close_good_moves
            )
            print(
                "=============================================="
            )

    # ======================================================
    # 37. MATE AFTER MOVE PRIORITY
    # ======================================================

    if mate_blunder:

        for item in reasons:

            if item["type"] == "mate_blunder":

                item["priority"] = 120

            else:

                item["priority"] = min(
                    item["priority"],
                    40
                )

    # ======================================================
    # 38. DELAYED CAPTURE FILTER
    # ======================================================

    if any(
        item.get("type")
        == "delayed_capture"
        and item.get("priority", 0) > 0
        for item in reasons
    ):

        blocked_types = {
            "tempo_material_loss",
            "piece_attack",
            "piece_tempo_attack",
            "pawn_attack",
            "pawn_piece_attack",
            "queen_tempo",
            "best_move_idea",
            "delayed_capture"
        }

        reasons = [
            item
            for item in reasons
            if item.get("type")
            not in blocked_types
        ]

    # ======================================================
    # DEBUG REASONS
    # ======================================================

    print(
        "\nDEBUG ALL REASONS:"
    )

    for item in reasons:

        print(
            "  ",
            item.get("type"),
            "PRIORITY =",
            item.get("priority"),
            "TEXT =",
            item.get("text")
        )

    # ======================================================
    # INACCURACY NO BENEFIT — BELOW CONCRETE EXPLANATIONS
    # ======================================================

    if inaccuracy_no_benefit:

        for item in reasons:

            reason_type = item.get("type")

            if reason_type == "open_file_rook":
                item["priority"] = min(
                    item.get("priority", 0),
                    62
                )

            elif reason_type == "piece_tempo_attack":
                item["priority"] = min(
                    item.get("priority", 0),
                    60
                )

            elif reason_type == "piece_attack":
                item["priority"] = min(
                    item.get("priority", 0),
                    55
                )

            elif reason_type == "pawn_attack":
                item["priority"] = min(
                    item.get("priority", 0),
                    50
                )

            elif reason_type == "pawn_piece_attack":
                item["priority"] = min(
                    item.get("priority", 0),
                    50
                )

            elif reason_type == "queen_tempo":
                item["priority"] = min(
                    item.get("priority", 0),
                    60
                )

            

            elif reason_type == "center":
                item["priority"] = min(
                    item.get("priority", 0),
                    60
                )

            elif reason_type == "best_move_idea":
                item["priority"] = min(
                    item.get("priority", 0),
                    50
                )

    # ======================================================
    # УБИРАЕМ ДУБЛИРОВАНИЕ TEMPO-АТАКИ
    # ======================================================

    has_piece_tempo_attack = any(
        r.get("type") == "piece_tempo_attack"
        for r in reasons
    )

    if has_piece_tempo_attack:

        reasons = [
            r
            for r in reasons
            if r.get("type") != "pawn_attack"
        ]


    # ======================================================
    # PAWN LOSS PRIORITY
    #
    # Если обнаружена конкретная потеря пешки,
    # delayed_capture не должна становиться главной причиной.
    # ======================================================

    has_pawn_loss = any(
        item.get("type") == "pawn_loss"
        for item in reasons
    )

    if has_pawn_loss:
        for item in reasons:

            if item.get("type") == "delayed_capture":

                item["priority"] = min(
                    item.get("priority", 0),
                    96
                )

                print(
                    "DEBUG: delayed_capture lowered "
                    "because pawn_loss exists"
                )

    # ======================================================
    # PAWN LOSS vs FORCED PIECE LOSS
    #
    # Если конкретная потеря пешки обнаружена,
    # для объяснения ошибки предпочитаем pawn_loss.
    # ======================================================

    if has_pawn_loss:

        for item in reasons:

            if item.get("type") == "forced_piece_loss":

                item["priority"] = min(
                    item.get("priority", 0),
                    104
                )

                print(
                    "DEBUG: forced_piece_loss lowered "
                    "because pawn_loss exists"
                )

    # ======================================================
    # SORT
    # ======================================================

    reasons.sort(
        key=lambda x: x.get(
            "priority",
            0
        ),
        reverse=True
    )

    print(
        "DEBUG SORTED REASONS:"
    )

    for item in reasons:

        print(
            "  ",
            item.get("type"),
            "=>",
            item.get("priority")
        )

    # ======================================================
    # MAIN REASON
    # ======================================================

    reason = None
    reason_type = "general"

    if loss < 100:

        reason = {
            "type": "inaccuracy_no_benefit",
            "priority": 0,
            "text": (
                f"Можно было сыграть лучше: "
                f"{best} был более точным ходом."
            ),
        }

        reason_type = "inaccuracy_no_benefit"

        print(
            "DEBUG SMALL LOSS:",
            "LOSS =",
            loss,
            "MAIN REASON =",
            reason_type
        )

    elif reasons:

        reason = reasons[0]

        reason_type = reason.get(
            "type",
            "general"
        )

        print(
            "DEBUG SELECTED MAIN REASON:",
            reason_type,
            "PRIORITY =",
            reason.get("priority"),
            "TEXT =",
            reason.get("text")
        )
        
    # ======================================================
    # FALLBACK REASON
    # ======================================================

    if reason is None:

        if loss >= 500:

            reason_text = (
                "Ход вызвал значительное "
                "ухудшение позиции."
            )

        elif loss >= 300:

            reason_text = (
                "Ход заметно ухудшил вашу "
                "позицию."
            )

        elif loss >= 100:

            reason_text = (
                "Ход оказался менее точным, "
                "чем лучший вариант."
            )

        else:

            reason_text = (
                "Разница небольшая, но лучший "
                "ход сохранял более точную игру."
            )

        reason = {
            "type": "general",
            "priority": 0,
            "text": reason_text,
        }

    # ======================================================
    # MAIN OUTPUT
    # ======================================================

    parts = []

    if played and best:

        if equivalent_best_sans:

            parts.append(
                f"Вы сыграли {played}, "
                f"но сильнее было {best}. "
                f"Также практически ту же оценку "
                f"сохранял ход "
                f"{equivalent_best_sans[0]}."
            )

        else:

            parts.append(
                f"Вы сыграли {played}, "
                f"но сильнее было {best}."
            )

    elif played:

        parts.append(
            f"Вы сыграли {played}."
        )

    elif best:

        parts.append(
            f"Лучшим ходом было {best}."
        )

    parts.append(
        "\n\n**Почему это ошибка:** "
        + reason.get(
            "text",
            ""
        )
    )

   
    # ======================================================
    # SECONDARY IDEAS
    # ======================================================

    secondary_added = 0

    secondary_types = {
        "pawn_structure",
        "isolated_pawn",
        "equal_trade",
        "equivalent_trade_idea",
        "material",
        "material_pressure",
        "tempo_material_loss",
        "forced_piece_loss",
        "delayed_capture",
        "inaccuracy_no_benefit",
        "queen_tempo",
        "queen_activity",
        "piece_tempo_attack",
        "piece_attack",
        "pawn_piece_attack",
        "pawn_attack",
        "free_pawn",
        "bad_recapture",
        "king_safety",
        "center",
        "best_move_idea",
        "new_check_threat",
        "undefended_pawn",
        "check_response",
        "mate_in_one",
        "inaccuracy_no_benefit",
        "pawn_king_safety",
        "neutralized_plan",
    }

    # ======================================================
    # PAWN STRUCTURE SECONDARY
    # ======================================================

    if (
        pawn_structure_info
        and best
        and reason_type != "pawn_structure"
        and secondary_added < 2
    ):

        try:

            if isinstance(
                pawn_structure_info,
                str
            ):

                pawn_structure_text = (
                    pawn_structure_info
                )

            else:

                pawn_structure_text = (
                    pawn_structure_info.get(
                        "text",
                        ""
                    )
                )

            if pawn_structure_text:

                parts.append(
                    "\n\n**Ещё одна идея:** "
                    + pawn_structure_text
                )

                secondary_added += 1

        except Exception:
            pass

    # ======================================================
    # EQUAL TRADE SECONDARY
    # ======================================================

    if (
        equal_trade
        and secondary_added < 2
        and reason_type
        not in {
            "equal_trade",
            "apparent_piece_loss",
            "pin_material_loss",
            "material_pressure",
        }
    ):

        try:

            equal_trade_text = (
                get_equal_trade_text(
                    equal_trade_info
                )
            )

        except Exception:

            equal_trade_text = None

        if equal_trade_text:

            parts.append(
                "\n\n**Ещё одна идея:** "
                + equal_trade_text
            )

            secondary_added += 1

    # ======================================================
    # OTHER SECONDARY REASONS
    # ======================================================

    concrete_secondary_main = {
        "pin_material_loss",
        "material_pressure",
        "fork",
        "mate",
        "mate_blunder",
        "mate_in_one",
        "material",
        "check_response",
        "new_check_threat",
        "tempo_material_loss",
        "apparent_piece_loss",
        "forced_piece_loss",
    }

    for item in reasons[1:]:

        if secondary_added >= 2:
            break

        item_type = item.get(
            "type"
        )

        item_text = item.get(
            "text",
            ""
        )

        if not item_text:
            continue

        if item_type not in secondary_types:
            continue

        if item_type == reason_type:
            continue

        # --------------------------------------------------
        # Если мат — остальные идеи почти не нужны.
        # --------------------------------------------------

        if reason_type == "mate_blunder":

            if item_type in {
                "piece_attack",
                "piece_tempo_attack",
                "pawn_attack",
                "pawn_piece_attack",
                "queen_tempo",
                "center",
                "free_pawn",
                "bad_recapture",
                "best_move_idea",
                "inaccuracy_no_benefit",
            }:

                continue

        # --------------------------------------------------
        # Если mate in one — не перегружаем объяснение.
        # --------------------------------------------------

        if reason_type == "mate_in_one":

            if item_type in {
                "new_check_threat",
                "check",
                "queen_tempo",
                "center",
                "material_pressure",
            }:

                continue

        # --------------------------------------------------
        # Ответ на шах.
        # --------------------------------------------------

        if reason_type == "check_response":

            if item_type in {
                "new_check_threat",
                "check",
                "queen_tempo",
            }:

                continue

        # --------------------------------------------------
        # Конкретная материальная причина.
        # --------------------------------------------------

        if reason_type in concrete_secondary_main:

            if item_type in {
                "queen_tempo",
                "piece_tempo_attack",
                "piece_attack",
                "pawn_piece_attack",
                "pawn_attack",
                "new_check_threat",
                "check",
                "free_pawn",
                "center",
                "undefended_pawn",
                "isolated_pawn",
            }:

                continue

        # --------------------------------------------------
        # Если лучший ход просто является общей идеей,
        # не добавляем её второй раз.
        # --------------------------------------------------

        if (
            item_type == "best_move_idea"
            and len(reasons) > 1
        ):

            continue

        # --------------------------------------------------
        # Если новый детектор является главной причиной,
        # не добавляем generic piece_attack.
        # --------------------------------------------------

        if (
            reason_type
            == "inaccuracy_no_benefit"
            and item_type in {
                "piece_attack",
                "pawn_piece_attack",
                "pawn_attack",
            }
        ):

            continue

        parts.append(
            "\n\n**Ещё одна идея:** "
            + item_text
        )

        secondary_added += 1

    # ======================================================
    # BEST MOVE IDEA
    # ======================================================

    if (
        best_idea
        and reason_type
        not in {
            "best_move_idea",
            "apparent_piece_loss",
            "pin_material_loss",
            "material_pressure",
            "fork",
            "mate",
            "mate_blunder",
            "mate_in_one",
            "material",
            "check",
            "check_response",
            "inaccuracy_no_benefit",
        }
        and not equal_trade
        and not queen_trade_best_move
    ):

        parts.append(
            f"\n\n**Почему лучше было {best}:** "
            + best_idea
        )

    # ======================================================
    # TRAINING TIP
    # ======================================================

    training_tip = None

    if reason_type == "mate_blunder":

        training_tip = (
            "После каждого хода проверяйте все "
            "шахи соперника, особенно возможные "
            "матовые угрозы."
        )

    elif reason_type == "mate_in_one":

        training_tip = (
            "После своего хода всегда проверяйте, "
            "может ли соперник поставить мат "
            "следующим ходом."
        )

    elif reason_type == "mate":

        training_tip = (
            "Ищите форсированные ходы: сначала "
            "шахи, затем взятия и сильные угрозы."
        )

    elif reason_type == "material_pressure":

        training_tip = (
            "Если фигура связана или ограничена, "
            "не обязательно сразу забирать материал. "
            "Иногда сильнее сначала усилить давление "
            "и лишить соперника возможностей."
        )

    elif reason_type == "pin_material_loss":

        training_tip = (
            "Проверяйте, не становится ли ваша фигура "
            "связанной с королём и можно ли после "
            "этого выиграть её."
        )

    elif reason_type == "fork":

        training_tip = (
            "Ищите коневые вилки: особенно полезно "
            "проверять поля, с которых конь может "
            "одновременно атаковать ферзя и ладью "
            "или другие ценные фигуры."
        )

    elif reason_type == "isolated_pawn":

        training_tip = (
            "Следите, не создаёте ли вы изолированную "
            "пешку, особенно если её можно было "
            "сохранить или поддержать."
        )

    elif reason_type == "material":

        training_tip = (
            "Перед позиционным ходом сначала "
            "проверяйте доступные тактические "
            "взятия и угрозы."
        )

    elif reason_type == "check_response":

        training_tip = (
            "При шахе сначала рассмотрите все "
            "легальные способы защиты и только "
            "после этого выбирайте лучший по "
            "материалу и активности."
        )

    elif reason_type == "new_check_threat":

        training_tip = (
            "После своего хода проверяйте все шахи, "
            "которые соперник может получить "
            "следующим ходом."
        )

    elif reason_type == "check":

        training_tip = (
            "В тактических позициях сначала "
            "проверяйте шахи, затем взятия "
            "и только потом позиционные ходы."
        )

    elif reason_type == "delayed_capture":

        training_tip = (
            "Перед автоматическим взятием материала "
            "проверяйте, нет ли промежуточного хода, "
            "который даст дополнительный темп."
        )

    elif reason_type == "tempo_material_loss":

        training_tip = (
            "Не стоит автоматически забирать материал, "
            "если соперник получает за это темп, "
            "активность или инициативу."
        )

    elif reason_type == "forced_piece_loss":

        training_tip = (
            "Если фигура подвергается атаке пешкой, "
            "проверяйте не только первый отход, "
            "но и следующий ход соперника."
        )

    elif reason_type == "queen_tempo":

        training_tip = (
            "Проверяйте, не получает ли соперник "
            "темп за счёт нападения на вашего ферзя."
        )

    elif reason_type == "queen_activity":

        training_tip = (
            "После своего хода проверяйте, "
            "не открываете ли вы сопернику "
            "более активные поля для ферзя."
        )

    elif reason_type == "piece_attack":

        training_tip = (
            "После каждого хода проверяйте, "
            "какие ваши фигуры соперник сможет "
            "атаковать следующим ходом."
        )

    elif reason_type in {
        "pawn_piece_attack",
        "pawn_attack",
    }:

        training_tip = (
            "После своего хода проверяйте все "
            "новые нападения пешками."
        )

    elif reason_type == "undefended_pawn":

        training_tip = (
            "Следите, какие пешки остаются без "
            "защитников после перемещения фигур."
        )

    elif reason_type == "apparent_piece_loss":

        training_tip = (
            "Перед тем как считать фигуру потерянной, "
            "обязательно проверяйте, можно ли "
            "полноценно забрать атакующую фигуру."
        )

    elif reason_type == "equal_trade":

        try:

            training_tip = (
                get_equal_trade_text(
                    equal_trade_info
                )
            )

        except Exception:

            training_tip = (
                "Оценивайте не только сам размен, "
                "но и позицию, которая возникает "
                "после него."
            )

    elif reason_type == "bad_recapture":

        training_tip = (
            "После размена отдельно оценивайте "
            "позицию, которая получится после "
            "ответного взятия."
        )

    elif reason_type == "free_pawn":

        training_tip = (
            "Следите за пешками, которые соперник "
            "может выиграть без достаточной компенсации."
        )

    elif reason_type == "center":

        training_tip = (
            "Старайтесь вовремя бороться за центр "
            "и не отдавать сопернику лишнюю свободу."
        )

    elif reason_type == "pawn_king_safety":

        training_tip = (
            "Не передвигайте пешки вокруг короля "
            "без необходимости: они являются первой "
            "линией его защиты."
        )

    elif reason_type == "king_safety":

        training_tip = (
            "В спокойных позициях обращайте внимание "
            "на безопасность короля и возможность "
            "рокировки."
        )

    elif reason_type == "neutralized_plan":

        training_tip = (
            "Старайтесь замечать планы соперника "
            "заранее и ограничивать их до того, "
            "как они станут опасными."
        )

    elif reason_type == "inaccuracy_no_benefit":

        training_tip = (
            "Не каждая ошибка связана с потерей "
            "материала. В спокойных позициях "
            "сравнивайте несколько тихих ходов и "
            "спрашивайте себя, какой из них лучше "
            "улучшает активность фигур, контроль "
            "центра, безопасность короля или "
            "ограничивает соперника."
        )

    else:

        training_tip = (
            "После каждого хода спрашивайте себя: "
            "что именно изменилось в позиции и "
            "какой самый сильный ответ есть у соперника?"
        )

    if training_tip:

        parts.append(
            "\n\n**Запомните:** "
            + training_tip
        )

    # ======================================================
    # EVALUATION
    # ======================================================

    if (
        before is not None
        and after is not None
    ):

        parts.append(
            "\n\n**Оценка позиции:** "
            f"{before / 100:.2f} → "
            f"{after / 100:.2f}."
        )

        if loss >= 500:

            parts.append(
                " Это грубая ошибка, которая "
                "сильно ухудшает позицию."
            )

        elif loss >= 300:

            parts.append(
                " Это ошибка, которая заметно "
                "ухудшает вашу позицию."
            )

        elif loss >= 200:

            parts.append(
                " Это существенная неточность."
            )

        elif loss >= 100:

            parts.append(
                " Это небольшая, но заметная "
                "потеря качества."
            )

    # ======================================================
    # ALTERNATIVES
    # ======================================================

    other_alternatives = []

    for item in alternatives:

        if isinstance(
            item,
            dict
        ):

            san = (
                item.get("san")
                or ""
            ).strip()

        else:

            san = str(
                item
            ).strip()

        if not san:
            continue

        if best and san == best:
            continue

        if san in equivalent_best_sans:
            continue

        if san in other_alternatives:
            continue

        other_alternatives.append(
            san
        )

        if len(
            other_alternatives
        ) >= 2:

            break

    if other_alternatives:

        parts.append(
            "\n\n**Другие хорошие варианты:** "
            + ", ".join(
                other_alternatives
            )
            + "."
        )

    # ======================================================
    # EQUIVALENT BEST MOVES
    # ======================================================

    if equivalent_best_sans:

        if len(
            equivalent_best_sans
        ) == 1:

            parts.append(
                "\n\n**Практически равноценный "
                "вариант:** "
                + equivalent_best_sans[0]
                + "."
            )

        else:

            parts.append(
                "\n\n**Практически равноценные "
                "варианты:** "
                + ", ".join(
                    equivalent_best_sans
                )
                + "."
            )

    # ======================================================
    # FINAL DEBUG
    # ======================================================

    print(
        "\nDEBUG SELECTED REASON:"
    )

    print(
        "TYPE =",
        reason_type
    )

    print(
        "PRIORITY =",
        reason.get(
            "priority"
        )
    )

    print(
        "TEXT =",
        reason.get(
            "text"
        )
    )

    print(
        "QUEEN TRADE BEST MOVE =",
        queen_trade_best_move
    )

    print(
        "CHECK RESPONSE FOUND =",
        check_response_found
    )

    print(
        "INACCURACY NO BENEFIT =",
        bool(
            inaccuracy_no_benefit
        )
    )

    return "".join(
        parts
    ).strip()


# ==========================================================
# АНАЛИЗ SAN
# ==========================================================

def analyze_san(best_san):

    if not best_san:
        return []

    ideas = []

    if "#" in best_san:

        ideas.append(
            "Лучший ход сразу ставит мат."
        )

    elif "+" in best_san:

        ideas.append(
            "Лучший ход создаёт шах."
        )

    if "x" in best_san:

        ideas.append(
            "Лучший ход позволяет выиграть материал."
        )

    if "=" in best_san:

        ideas.append(
            "Пешка превращается в новую фигуру."
        )

    if best_san in (
        "O-O",
        "O-O-O"
    ):

        ideas.append(
            "Рокировка улучшает безопасность короля."
        )

    return ideas
