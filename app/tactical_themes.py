import chess


class ThemeDetector:

    VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 100
    }

    def detect(self, mistake):

        board = mistake["position_before"]
        best_move = mistake["best_move"]
        played_move = mistake["played"]

        """
        Последовательно проверяет все типы ошибок.
        """

        theme = self.detect_lost_piece(board, played_move)
        if theme:
            return theme

        theme = self.detect_mate(board, best_move)
        if theme:
            return theme

        theme = self.detect_fork(board, played_move)
        if theme:
            return theme

        theme = self.detect_missed_fork(mistake)
        if theme:
            return theme

        theme = self.detect_missed_pin(mistake)
        if theme:
            return theme

        theme = self.detect_lost_queen(board, played_move)
        if theme:
            return theme

        theme = self.detect_lost_rook(board, played_move)
        if theme:
            return theme

        theme = self.detect_lost_pawn(board, played_move)
        if theme:
            return theme

        theme = self.detect_mate_in_one(board, best_move)
        if theme:
            return theme

        theme = self.detect_pin(board, played_move)
        if theme:
            return theme

        theme = self.detect_hanging_piece(board, played_move)
        if theme:
            return theme

        # Здесь позже будут:
        # theme = self.detect_pin(...)
        # theme = self.detect_skewer(...)
        # theme = self.detect_mate(...)
        # ...

        theme = self.detect_hanging_piece(board, played_move)
        if theme:
            return theme

        return "Не определено"

    def valuable_piece(self, piece):

        if piece is None:
            return False

        return piece.piece_type in (
            chess.KNIGHT,
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN,
            chess.KING
        )

    def detect_lost_piece(self, board, played_move):

        before = board.copy()

        after = board.copy()
        after.push(played_move)

        side = not after.turn

        values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }

        before_pieces = {}

        for square, piece in before.piece_map().items():

            if piece.color == side:
                before_pieces[square] = piece

        after_pieces = {}

        for square, piece in after.piece_map().items():

            if piece.color == side:
                 after_pieces[square] = piece

        before_value = sum(values.get(p.piece_type, 0) for p in before_pieces.values())
        after_value = sum(values.get(p.piece_type, 0) for p in after_pieces.values())

        if before_value - after_value >= 3:
            return "Зевок фигуры"
        
        return None

    def detect_mate(self, board, best_move):

        test = board.copy()
        test.push(best_move)

        if test.is_checkmate():
            return "Мат в 1"

        return None

    def detect_hanging_piece(self, board, played_move):

        test_board = board.copy()

        # Теперь board — это позиция ДО хода,
        # поэтому этот push будет корректным.
        test_board.push(played_move)

        side_that_moved = not test_board.turn

        for square, piece in test_board.piece_map().items():

            if piece.color != side_that_moved:
                continue

            attackers = test_board.attackers(not piece.color, square)
            defenders = test_board.attackers(piece.color, square)

            if attackers and not defenders:
                return f"Висит {piece.symbol().upper()}"

        return None

    def detect_fork(self, board, played_move):

        after = board.copy()
        after.push(played_move)

        side = after.turn          # ходить теперь сопернику

        values = {
            chess.QUEEN: 9,
            chess.ROOK: 5,
            chess.BISHOP: 3,
            chess.KNIGHT: 3,
            chess.KING: 100
        }

        for move in after.legal_moves:

            piece = after.piece_at(move.from_square)

            if piece is None:
                continue

            if piece.color != side:
                continue

            attacked = []

            temp = after.copy()
            temp.push(move)

            for square, p in temp.piece_map().items():

                if p.color == side:
                    continue

                if p.piece_type not in values:
                    continue

                if temp.is_attacked_by(side, square):
                    attacked.append(square)

            if len(attacked) >= 2:
                return "Вилка"

        return None

    def detect_pin(self, board, played_move):

        test = board.copy()
        test.push(played_move)
        enemy = test.turn
        our = not enemy

        for square, piece in test.piece_map().items():

            if piece.color != enemy:
                continue

            if piece.piece_type == chess.KING:
                continue

            attackers = test.attackers(our, square)

            if not attackers:
                continue

            original_piece = test.remove_piece_at(square)

            king_in_check = test.is_check()

            test.set_piece_at(square, original_piece)

            if king_in_check:
                return "Связка"

        return None

    def detect_lost_queen(self, board, played_move):

        before = board.copy()

        after = board.copy()
        after.push(played_move)

        side = not after.turn

        before_queen = 0
        after_queen = 0

        for piece in before.piece_map().values():
            if piece.color == side and piece.piece_type == chess.QUEEN:
                before_queen += 1

        for piece in after.piece_map().values():
            if piece.color == side and piece.piece_type == chess.QUEEN:
                after_queen += 1

        if before_queen > after_queen:
            return "Потеря ферзя"

        return None

    def detect_lost_rook(self, board, played_move):

        before = board.copy()

        after = board.copy()
        after.push(played_move)

        side = not after.turn

        before_rooks = 0
        after_rooks = 0

        for piece in before.piece_map().values():
            if piece.color == side and piece.piece_type == chess.ROOK:
                before_rooks += 1

        for piece in after.piece_map().values():
            if piece.color == side and piece.piece_type == chess.ROOK:
                after_rooks += 1

        if before_rooks > after_rooks:
            return "Потеря ладьи"

        return None

    def detect_mate_in_one(self, board, best_move):

        test = board.copy()

        test.push(best_move)

        if test.is_checkmate():
            return "Мат в 1"

        return None

    def detect_missed_fork(self, mistake):

        board = mistake["position_before"]
        best_move = mistake["best_move"]

        test = board.copy()
        test.push(best_move)

        side = not test.turn

        attacked = []

        for square, piece in test.piece_map().items():

            if piece.color == side:
                continue

            if test.is_attacked_by(side, square):
                attacked.append(piece)

        valuable = [
            p for p in attacked
            if p.piece_type in (
                chess.QUEEN,
                chess.ROOK,
                chess.KING
            )
        ]

        if len(valuable) >= 2:
            return "Пропущена вилка"

        return None

    def detect_missed_pin(self, mistake):

        board = mistake["position_before"]
        best_move = mistake["best_move"]

        test = board.copy()
        test.push(best_move)

        side = not test.turn

        for square, piece in test.piece_map().items():

            if piece.color == side:
                continue

            attackers = test.attackers(side, square)

            if not attackers:
                continue

            # Берём первую атакующую фигуру
            attacker_square = list(attackers)[0]

            # Если после неё по одной линии стоит более ценная фигура —
            # считаем это связкой.
            for target in chess.SQUARES:

                target_piece = test.piece_at(target)

                if target_piece is None:
                    continue

                if target_piece.color != piece.color:
                    continue

                if target_piece.piece_type <= piece.piece_type:
                    continue

                if chess.square_file(attacker_square) == chess.square_file(square) == chess.square_file(target):
                    return "Пропущена связка"

                if chess.square_rank(attacker_square) == chess.square_rank(square) == chess.square_rank(target):
                    return "Пропущена связка"

        return None

    def detect_lost_pawn(self, board, played_move):

        before = board.copy()

        after = board.copy()
        after.push(played_move)

        side = not after.turn

        before_pawns = 0
        after_pawns = 0

        for piece in before.piece_map().values():
            if piece.color == side and piece.piece_type == chess.PAWN:
                before_pawns += 1

        for piece in after.piece_map().values():
            if piece.color == side and piece.piece_type == chess.PAWN:
                after_pawns += 1

        if before_pawns - after_pawns >= 1:
            return "Потеря пешки"

        return None

detector = ThemeDetector()


def detect_theme(mistake):
    return detector.detect(mistake)

