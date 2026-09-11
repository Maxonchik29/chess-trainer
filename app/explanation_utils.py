import chess


PIECE_NAMES = {
    chess.PAWN: "пешку",
    chess.KNIGHT: "коня",
    chess.BISHOP: "слона",
    chess.ROOK: "ладью",
    chess.QUEEN: "ферзя",
    chess.KING: "короля",
}


PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}

CENTER_SQUARES = {
    chess.D4,
    chess.E4,
    chess.D5,
    chess.E5,
}

def piece_value(piece):
    if not piece:
        return 0

    return PIECE_VALUES.get(piece.piece_type, 0)


def piece_name(piece):
    if not piece:
        return "фигуру"

    return PIECE_NAMES.get(piece.piece_type, "фигуру")

def get_move_piece(board, move):

    if not board or not move:
        return None

    try:

        return board.piece_at(
            move.from_square
        )

    except Exception:

        return None

def get_captured_piece(board, move):

    if not board or not move:
        return None

    try:

        if not board.is_capture(move):
            return None

        captured_square = move.to_square

        if board.is_en_passant(move):

            captured_square += (
                -8
                if board.turn == chess.WHITE
                else 8
            )

        return board.piece_at(
            captured_square
        )

    except Exception:

        return None

def make_position_after(board, move):

    if not board or not move:
        return None

    try:

        if move not in board.legal_moves:
            return None

        result = board.copy()

        result.push(move)

        return result

    except Exception:

        return None

def get_best_move(mistake, board):

    if not mistake or not board:
        return None

    move = mistake.get(
        "best_move"
    )

    if move and isinstance(
        move,
        chess.Move
    ):

        try:

            if move in board.legal_moves:
                return move

        except Exception:
            pass

    best_uci = mistake.get(
        "best_uci"
    )

    if best_uci:

        try:

            move = chess.Move.from_uci(
                best_uci
            )

            if move in board.legal_moves:
                return move

        except Exception:
            pass

    best_san = mistake.get(
        "best",
        ""
    )

    if best_san:

        try:

            return board.parse_san(
                best_san
            )

        except Exception:
            pass

    return None






