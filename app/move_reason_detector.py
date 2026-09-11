import chess


def detect_move_reason(
    position_before,
    position_after,
    played_move
):

    reasons = []

    # ==========================================================
    # НАША ФИГУРА ДО ХОДА
    # ==========================================================

    moved_piece_before = position_before.piece_at(
        played_move.from_square
    )

    if moved_piece_before is None:
        return reasons

    # ==========================================================
    # НАША ФИГУРА ПОСЛЕ ХОДА
    # ==========================================================

    moved_piece_after = position_after.piece_at(
        played_move.to_square
    )

    if moved_piece_after is None:
        return reasons

    # Проверяем, что после хода на новой клетке
    # действительно находится наша фигура того же типа
    if (
        moved_piece_after.color != moved_piece_before.color
        or moved_piece_after.piece_type != moved_piece_before.piece_type
    ):
        return reasons

    # Короля здесь не рассматриваем
    if moved_piece_before.piece_type == chess.KING:
        return reasons

    opponent_color = not moved_piece_before.color

    # ==========================================================
    # АТАКИ НА ФИГУРУ ДО ХОДА
    # ==========================================================

    attackers_before = set(
        position_before.attackers(
            opponent_color,
            played_move.from_square
        )
    )

    # ==========================================================
    # АТАКИ НА ФИГУРУ ПОСЛЕ ХОДА
    # ==========================================================

    attackers_after = set(
        position_after.attackers(
            opponent_color,
            played_move.to_square
        )
    )

    # ==========================================================
    # ТОЛЬКО НОВЫЕ АТАКУЮЩИЕ
    # ==========================================================

    new_attackers = (
        attackers_after - attackers_before
    )

    if not new_attackers:
        return reasons

    # ==========================================================
    # ФОРМИРУЕМ ПРИЧИНУ
    # ==========================================================

    target_name = chess.piece_name(
        moved_piece_after.piece_type
    )

    target_square = chess.square_name(
        played_move.to_square
    )

    for attacker_square in new_attackers:

        attacker = position_after.piece_at(
            attacker_square
        )

        if attacker is None:
            continue

        attacker_square_name = chess.square_name(
            attacker_square
        )

        attacker_name = chess.piece_name(
            attacker.piece_type
        )

        reasons.append(
            f"После вашего хода соперник начал "
            f"атаковать {target_name} на "
            f"{target_square} {attacker_name}ом "
            f"с {attacker_square_name}."
        )

    return reasons