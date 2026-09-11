import chess


PIECE_NAMES = {
    chess.PAWN: "пешка",
    chess.KNIGHT: "конь",
    chess.BISHOP: "слон",
    chess.ROOK: "ладья",
    chess.QUEEN: "ферзь",
    chess.KING: "король"
}


def detect_hanging_piece(board):

    side = board.turn

    for square, piece in board.piece_map().items():

        if piece.color != side:
            continue

        attackers = board.attackers(not side, square)
        defenders = board.attackers(side, square)

        if attackers and not defenders:

            attacker_square = next(iter(attackers))
            attacker_piece = board.piece_at(attacker_square)

            return {

                "piece": PIECE_NAMES[piece.piece_type],

                "square": chess.square_name(square),

                "attacker": PIECE_NAMES[attacker_piece.piece_type],

                "attacker_square": chess.square_name(attacker_square)

            }

    return None


def analyze_tactical_features(board, best_move):

    result = {

        "theme": None,

        "exchange_piece": None,
        "exchange_square": None,
        "exchange_target": None,
        "exchange_target_square": None,

        "captured_piece": None,
        "captured_value": None,

        "hanging_piece": None,
        "hanging_square": None,

        "attacker": None,
        "attacker_square": None,

        "fork_targets": [],

        "pawn_king_attack": False,
        "pawn_king_attack_explanation": None,

        "knight_sacrifice": False,
        "knight_sacrifice_attack": False,
        "knight_sacrifice_explanation": None,

        "pawn_threat": False,
        "pawn_threat_piece": None,
        "pawn_threat_square": None,
        "pawn_threat_attacker_square": None,
        "pawn_threat_move": None,
        "pawn_threat_explanation": None,

        "bishop_attack_reason": None
    }

    # ---------- Что выигрывает лучший ход ----------

    if board.is_capture(best_move):

        if board.is_en_passant(best_move):

            result["captured_piece"] = "пешку"
            result["captured_value"] = 1

        else:

            piece = board.piece_at(best_move.to_square)

            if piece:

                names = {
                    chess.PAWN: "пешку",
                    chess.KNIGHT: "коня",
                    chess.BISHOP: "слона",
                    chess.ROOK: "ладью",
                    chess.QUEEN: "ферзя",
                    chess.KING: "короля"
                }

                values = {
                    chess.PAWN: 1,
                    chess.KNIGHT: 3,
                    chess.BISHOP: 3,
                    chess.ROOK: 5,
                    chess.QUEEN: 9
                }

                result["captured_piece"] = names.get(piece.piece_type)
                result["captured_value"] = values.get(piece.piece_type)

    # ---------- Висящие фигуры ----------

    hanging = detect_hanging_piece(board)

    if hanging:

        result["hanging_piece"] = hanging["piece"]
        result["hanging_square"] = hanging["square"]

        result["attacker"] = hanging["attacker"]
        result["attacker_square"] = hanging["attacker_square"]


    # ==========================================================
    # ПРОДВИЖЕНИЕ ПЕШКИ → АТАКА НА КОРОЛЯ
    # ==========================================================

    moved_piece = board.piece_at(best_move.from_square)

    if moved_piece and moved_piece.piece_type == chess.PAWN:

        board_after_best = board.copy()
        board_after_best.push(best_move)

        enemy_king = board_after_best.king(
            not moved_piece.color
        )

        if enemy_king is not None:

            king_square = enemy_king

            pawn_attackers = board_after_best.attackers(
                moved_piece.color,
                king_square
            )

            if pawn_attackers:

                result["pawn_king_attack"] = True

                result["pawn_king_attack_explanation"] = (
                    "Продвижение этой пешки создаёт возможности "
                    "для атаки на позицию короля."
                )

                print(
                    "!!! НАЙДЕНА ПЕШЕЧНАЯ АТАКА НА КОРОЛЯ !!!"
                )


    # ---------- Вилка ----------

    if detect_fork(board, best_move):

        result["theme"] = "Вилка"

        board_copy = board.copy()
        board_copy.push(best_move)

        attacking_piece = board_copy.piece_at(best_move.to_square)

        if attacking_piece:

            for square, target in board_copy.piece_map().items():

                if target.color == attacking_piece.color:
                    continue

                if target.piece_type == chess.KING:
                    continue

                if board_copy.is_attacked_by(
                    attacking_piece.color,
                    square
                ):

                    result["fork_targets"].append({
                        "piece": PIECE_NAMES[target.piece_type],
                        "square": chess.square_name(square)
                    })


    # ---------- Связка ----------

    if result["theme"] is None:

        if detect_pin(board, best_move):

            result["theme"] = "Связка"


    # ---------- Определение темы ----------

    if result["theme"] is None:

        result["theme"] = detect_theme(result)


    return result


def detect_theme(features):

    # Потеря фигуры
    if features["captured_piece"]:
        return "Потеря фигуры"

    # Висящая фигура
    if features["hanging_piece"]:
        return "Висящая фигура"

    return "Не определено"


def detect_fork(board, best_move):

    board_copy = board.copy()
    board_copy.push(best_move)

    piece = board_copy.piece_at(best_move.to_square)

    if piece is None:
        return False

    attacked = []

    for square, target in board_copy.piece_map().items():

        if target.color == piece.color:
            continue

        if board_copy.is_attacked_by(piece.color, square):

            if target.piece_type != chess.KING:

                attacked.append(square)

    return len(attacked) >= 2


def detect_pin(board, best_move):

    board_copy = board.copy()
    board_copy.push(best_move)

    attacker = board_copy.piece_at(best_move.to_square)

    if attacker is None:
        return False

    if attacker.piece_type not in (
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN
    ):
        return False

    attacker_color = attacker.color

    directions = []

    if attacker.piece_type in (chess.ROOK, chess.QUEEN):

        directions.extend([
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1)
        ])

    if attacker.piece_type in (chess.BISHOP, chess.QUEEN):

        directions.extend([
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1)
        ])

    start_file = chess.square_file(best_move.to_square)
    start_rank = chess.square_rank(best_move.to_square)

    for df, dr in directions:

        file = start_file + df
        rank = start_rank + dr

        first_piece = None

        while 0 <= file < 8 and 0 <= rank < 8:

            sq = chess.square(file, rank)

            piece = board_copy.piece_at(sq)

            if piece:

                if first_piece is None:

                    if piece.color != attacker_color:
                        first_piece = piece
                    else:
                        break

                else:

                    if piece.color != attacker_color:
                        break

                    if piece.piece_type == chess.KING:
                        return True

                    values = {
                        chess.PAWN: 1,
                        chess.KNIGHT: 3,
                        chess.BISHOP: 3,
                        chess.ROOK: 5,
                        chess.QUEEN: 9,
                        chess.KING: 100
                    }

                    if values[piece.piece_type] > values[first_piece.piece_type]:
                        return True

                    break

            file += df
            rank += dr

    return False