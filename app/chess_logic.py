def find_piece(pieces, piece_symbol):
    for pos, piece in pieces.items():
        if piece == piece_symbol:
            return pos
    return None