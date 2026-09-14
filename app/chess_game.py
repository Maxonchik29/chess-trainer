import os

import chess
import chess.engine


ENGINE_DEPTH = 12

if os.name == "nt":
    ENGINE_PATH = "engine/stockfish.exe"
else:
    ENGINE_PATH = "/usr/games/stockfish"

# ============================================================
# ДЕБЮТНЫЕ ЛИНИИ
# ============================================================

OPENING_LINES = {
    "none": [],

    "french": [
        "e2e4",
        "e7e6",
    ],

    "sicilian": [
        "e2e4",
        "c7c5",
    ],

    "old_indian": [
        "d2d4",
        "g8f6",
        "c2c4",
        "d7d6",
    ],

    "kings_indian": [
        "d2d4",
        "g8f6",
        "c2c4",
        "g7g6",
    ],
}


# ============================================================
# ШАХМАТНАЯ ИГРА
# ============================================================

class ChessGame:

    def __init__(
        self,
        player_color=chess.WHITE,
        depth=ENGINE_DEPTH,
        opening="none"
    ):
        self.player_color = player_color
        self.depth = depth

        if opening not in OPENING_LINES:
            opening = "none"

        self.opening = opening
        self.opening_line = OPENING_LINES[opening]
        self.opening_active = opening != "none"

        self.board = chess.Board()
        self.move_history = []

        self.engine = chess.engine.SimpleEngine.popen_uci(
            ENGINE_PATH
        )

    # ========================================================
    # СБРОС ПАРТИИ
    # ========================================================

    def reset(self):
        self.board = chess.Board()
        self.move_history = []

        self.opening_line = OPENING_LINES.get(
            self.opening,
            []
        )

        self.opening_active = (
            self.opening != "none"
        )

    # ========================================================
    # ЗАКРЫТИЕ STOCKFISH
    # ========================================================

    def close(self):
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass

            self.engine = None

    # ========================================================
    # FEN
    # ========================================================

    def get_fen(self):
        return self.board.fen()

    # ========================================================
    # ЛЕГАЛЬНЫЕ ХОДЫ
    # ========================================================

    def get_legal_moves(self):
        return [
            move.uci()
            for move in self.board.legal_moves
        ]

    # ========================================================
    # ЧЕЙ ХОД
    # ========================================================

    def is_player_turn(self):
        return (
            self.board.turn == self.player_color
        )

    # ========================================================
    # КОНЕЦ ПАРТИИ
    # ========================================================

    def is_game_over(self):
        return self.board.is_game_over()

    # ========================================================
    # СТАТУС
    # ========================================================

    def get_status(self):

        if self.board.is_checkmate():

            if self.board.turn == self.player_color:
                return "Вы проиграли"
            else:
                return "Вы победили"

        if self.board.is_stalemate():
            return "Пат"

        if self.board.is_insufficient_material():
            return "Ничья: недостаточно материала"

        if self.board.is_fifty_moves():
            return "Ничья: правило 50 ходов"

        if self.board.is_repetition():
            return "Ничья: троекратное повторение"

        if self.board.is_game_over():
            return "Партия закончена"

        return "Партия продолжается"

    # ========================================================
    # ПРОВЕРКА ДЕБЮТНОЙ ЛИНИИ
    # ========================================================

    def _get_opening_move(self):

        if not self.opening_active:
            return None

        move_number = len(self.move_history)

        # Вся линия уже закончилась
        if move_number >= len(self.opening_line):
            self.opening_active = False
            return None

        # Проверяем, что история партии полностью
        # совпадает с началом выбранной линии
        for index, played_move in enumerate(
            self.move_history
        ):
            if played_move != self.opening_line[index]:
                self.opening_active = False
                return None

        expected_uci = self.opening_line[move_number]

        try:
            move = chess.Move.from_uci(
                expected_uci
            )
        except ValueError:
            self.opening_active = False
            return None

        # Ход из дебютной линии должен быть легальным
        if move not in self.board.legal_moves:
            self.opening_active = False
            return None

        return move

    # ========================================================
    # ПРОВЕРКА ХОДА ИГРОКА ОТНОСИТЕЛЬНО ДЕБЮТА
    # ========================================================

    def _check_player_opening_move(self, move):

        if not self.opening_active:
            return

        move_number = len(self.move_history)

        if move_number >= len(self.opening_line):
            self.opening_active = False
            return

        expected_uci = self.opening_line[move_number]

        if move.uci() != expected_uci:
            # Игрок отклонился от дебютной линии.
            # Дальше компьютер играет обычным Stockfish.
            self.opening_active = False

    # ========================================================
    # ЛУЧШИЙ ХОД STOCKFISH
    # ========================================================

    def get_best_move(self):

        if self.engine is None:
            return None

        result = self.engine.analyse(
            self.board,
            chess.engine.Limit(
                depth=self.depth
            )
        )

        return result["pv"][0]

    # ========================================================
    # ХОД ИГРОКА
    # ========================================================

    def make_player_move(self, uci_move):

        if self.board.turn != self.player_color:
            return {
                "success": False,
                "error": "Сейчас ход компьютера."
            }

        try:
            move = chess.Move.from_uci(
                uci_move
            )
        except ValueError:
            return {
                "success": False,
                "error": "Некорректный ход."
            }

        if move not in self.board.legal_moves:
            return {
                "success": False,
                "error": "Так сходить нельзя."
            }

        # Проверяем, не отклонился ли игрок
        # от выбранной дебютной линии.
        self._check_player_opening_move(
            move
        )

        # Запоминаем SAN до изменения позиции
        san = self.board.san(move)

        # Оценка позиции до хода
        best_move = self.get_best_move()

        self.board.push(move)
        self.move_history.append(
            move.uci()
        )

        return {
            "success": True,

            "move": move.uci(),

            "played_move": move.uci(),

            "san": self.board.peek().uci()
            if False
            else None,

            "best_move": (
                best_move.uci()
                if best_move
                else None
            ),

            "fen": self.get_fen(),

            "legal_moves":
                self.get_legal_moves(),

            "player_turn":
                self.is_player_turn(),

            "game_over":
                self.is_game_over(),

            "status":
                self.get_status(),
        }

    # ========================================================
    # ХОД КОМПЬЮТЕРА
    # ========================================================

    def make_computer_move(self):

        if self.board.turn == self.player_color:
            return {
                "success": False,
                "error": "Сейчас ход игрока."
            }

        if self.board.is_game_over():
            return {
                "success": False,
                "error": "Партия уже закончена."
            }

        # ----------------------------------------------------
        # СНАЧАЛА ПРОБУЕМ ВЫБРАННЫЙ ДЕБЮТ
        # ----------------------------------------------------

        move = self._get_opening_move()

        opening_move = False

        if move is not None:
            opening_move = True

        # ----------------------------------------------------
        # ЕСЛИ ДЕБЮТ НЕ ПОДХОДИТ — STOCKFISH
        # ----------------------------------------------------

        if move is None:

            move = self.get_best_move()

            if move is None:
                return {
                    "success": False,
                    "error": "Stockfish не вернул ход."
                }

        # Запоминаем SAN до push
        san = self.board.san(move)

        self.board.push(move)
        self.move_history.append(
            move.uci()
        )

        # Если дебютная линия закончилась,
        # дальше будет играть Stockfish.
        if (
            self.opening_active
            and len(self.move_history)
            >= len(self.opening_line)
        ):
            self.opening_active = False

        return {
            "success": True,
            "move": move.uci(),
            "san": san,
            "opening_move": opening_move,
            "opening": self.opening,
            "opening_active": self.opening_active,
            "fen": self.get_fen(),
            "legal_moves": self.get_legal_moves(),
            "player_turn": self.is_player_turn(),
            "game_over": self.is_game_over(),
            "status": self.get_status(),
        }

