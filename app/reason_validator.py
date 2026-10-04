# app/reason_validator.py

"""
Единый валидатор причин шахматных ошибок.

Задача:
    detector может предложить причину,
    но причина не должна автоматически попадать
    в финальное объяснение.

На первом этапе здесь валидируются только
конкретные материальные причины.

Архитектура:

    detector
        ↓
    candidate reason
        ↓
    validate_reason()
        ↓
    True / False
"""

CONCRETE_MATERIAL_REASONS = {
    "causal_material_loss",
    "forced_piece_loss",
    "forced_piece_loss_after_pawn_tempo",
    "material_pressure",
    "pawn_loss",
    "add_defender_and_delayed_capture",
    "add_defender_to_vulnerable_pawn",
    "delayed_capture",
    "tempo_material_loss",
    "apparent_piece_loss",
    "pin_material_loss",
    "newly_pinned_pawn",
    "fork",
    "material",
    "undefended_pawn",
    "trapped_piece",
}


def validate_reason(
    reason,
    mistake,
    counterfactual_ctx=None,
    causal_material_consequence=None,
):
    """
    Проверяет candidate reason перед попаданием
    в финальный список reasons.

    Возвращает:
        True  — причина разрешена
        False — причина отбрасывается
    """

    if not isinstance(reason, dict):
        return False

    reason_type = reason.get("type")

    if not reason_type:
        return False

    # --------------------------------------------------
    # 1. CAUSAL MATERIAL LOSS
    # --------------------------------------------------
    #
    # Это самый надёжный источник материальной причины.
    #
    # Если counterfactual уже доказал причинную
    # материальную последовательность, разрешаем.
    #
    # Если detector добавил causal_material_loss,
    # но доказательства нет — запрещаем.
    # --------------------------------------------------

    if reason_type == "causal_material_loss":

        if causal_material_consequence is None:
            print(
                "REASON VALIDATOR: "
                "reject causal_material_loss — "
                "no counterfactual consequence"
            )
            return False

        reason_type_cf = (
            causal_material_consequence.get("reason_type")
        )

        if reason_type_cf not in {
            "direct_capture_of_played_piece",
            "played_move_removed_defender",
        }:
            print(
                "REASON VALIDATOR: "
                "reject causal_material_loss — "
                "unknown counterfactual reason"
            )
            return False

        print(
            "REASON VALIDATOR: "
            "accept causal_material_loss",
            reason_type_cf,
        )

        return True

    # --------------------------------------------------
    # 2. ОСТАЛЬНЫЕ КОНКРЕТНЫЕ МАТЕРИАЛЬНЫЕ ПРИЧИНЫ
    # --------------------------------------------------
    #
    # Пока НЕ запрещаем их автоматически.
    #
    # Это важно:
    # старые detector'ы ещё не переведены полностью
    # на counterfactual-проверку.
    #
    # Поэтому на первом этапе validator действует
    # консервативно.
    # --------------------------------------------------

    if reason_type in CONCRETE_MATERIAL_REASONS:

        print(
            "REASON VALIDATOR: "
            "legacy concrete reason allowed:",
            reason_type,
        )

        return True

    # --------------------------------------------------
    # 3. НЕ МАТЕРИАЛЬНЫЕ ПРИЧИНЫ
    # --------------------------------------------------
    #
    # Пока пропускаем без дополнительной проверки.
    #
    # Их будем переводить на validator следующим этапом.
    # --------------------------------------------------

    print(
        "REASON VALIDATOR: "
        "non-material reason allowed:",
        reason_type,
    )

    return True