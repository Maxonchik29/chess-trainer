import chess

from app.explanation_engine import generate_explanation
from app.pv_explainer import generate_explanation_v2

# True  — объяснения строит новый движок (app/pv_explainer.py)
# False — старый движок (app/explanation_engine.py), запасной вариант
USE_NEW_EXPLAINER = True


def build_mistake(
    board,
    loss,
    mistake_type,
    side,
    user_color,
    position_before,
    position_after,
    best_move,
    best_move_san,
    best_score_obj,
    best_lines,
    alternatives,
    move,
    played_move_san,
    fen,
    before_score,
    after_score,
    captured_piece=None,
    captured_value=None,
    hanging_piece=None,
    hanging_square=None,
    fork_targets=None,
    theme=None,
    best_piece=None,
    best_square=None,
    target_piece=None,
    target_square=None,
    features=None,
    move_reasons=None,
    bishop_attack_reason=None,
    tactical_threats=None,
    pawn_tempo_explanation=None,
    played_results=None,
    equivalent_best_moves=None,
):

    mistake = {

        "move": board.fullmove_number,

        "move_text": (
            f"{board.fullmove_number}."
            if board.turn == chess.WHITE
            else f"{board.fullmove_number}..."
        ),

        "played_san": played_move_san,

        "symbol": (
            "❓"
            if loss < 200
            else "?"
            if loss < 500
            else "??"
        ),

        "position_before": position_before,
        "position_after": position_after,

        "best_move": best_move,
        "played": played_move_san,

        "best": best_move_san,
        "best_uci": best_move.uci(),

        "best_score_obj": best_score_obj,
        "pv": best_lines[0]["pv"],
        "alternatives": alternatives,

        "loss": loss,
        "type": mistake_type,

        "side": side,
        "user_side": user_color,

        "fen": fen,

        "before_score": before_score,
        "after_score": after_score,

        "captured_piece": captured_piece,
        "captured_value": captured_value,

        "hanging_piece": hanging_piece,
        "hanging_square": hanging_square,
        "fork_targets": fork_targets,

        "explanation": "",
        "move_reasons": move_reasons or [],
        "bishop_attack_reason": bishop_attack_reason,
        "theme": theme,
        "best_piece": best_piece,
        "best_square": best_square,
        "target_piece": target_piece,
        "target_square": target_square,
        "equivalent_best_moves": (
            equivalent_best_moves
            if equivalent_best_moves is not None
            else []
        ),

        "pawn_attack_piece": (
            features.get("pawn_attack_piece")
            if features else None
        ),

        "pawn_attack_square": (
            features.get("pawn_attack_square")
            if features else None
        ),

        "pawn_attacker_square": (
            features.get("pawn_attacker_square")
            if features else None
        ),

        "pawn_king_attack": (
            features.get("pawn_king_attack", False)
            if features else False
        ),

        "knight_sacrifice_attack": (
            features.get("knight_sacrifice_attack", False)
            if features else False
        ),

        "knight_sacrifice": (
            features.get("knight_sacrifice", False)
            or features.get("knight_sacrifice_attack", False)
            if features
            else False
        ),

        "knight_sacrifice_explanation": (
            features.get("knight_sacrifice_explanation")
            if features else None
        ),

        "pawn_king_attack_explanation": (
            features.get("pawn_king_attack_explanation")
            if features else None
        ),

        "features": features,

        "pawn_threat_explanation": (
            features.get("pawn_threat_explanation")
            if features else None
        ),

        "tactical_threats": (
            tactical_threats or []
        ),

        "pawn_tempo_explanation": (
            pawn_tempo_explanation
        ),

        # ==================================================
        # АНАЛИЗ ПОСЛЕ СЫГРАННОГО ХОДА
        #
        # played_results — линии движка ПОСЛЕ сыгранного хода.
        # [0]["pv"] начинается с ответа соперника.
        # Новый движок (pv_explainer.py) проигрывает эту линию
        # на доске и по ней находит причину ошибки.
        # ==================================================

        "played_results": (
            played_results or []
        ),

    }

    mistake["explanation"] = (
        generate_explanation_v2(mistake)
        if USE_NEW_EXPLAINER
        else generate_explanation(mistake)
    )

    return mistake