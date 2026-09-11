import os
import chess
import chess.engine


# ============================================================
# НАСТРОЙКИ STOCKFISH
# ============================================================

# Windows:
#     используем локальный stockfish.exe
#
# Linux / Render:
#     используем Stockfish, установленный в Docker
#
if os.name == "nt":
    ENGINE_PATH = os.path.join(
        "engine",
        "stockfish.exe"
    )
else:
    ENGINE_PATH = "/usr/games/stockfish"


ENGINE_DEPTH = 12


# ============================================================
# ИГРОВАЯ ЛОГИКА
# ============================================================

class ChessGame:

    def __init__(
        self,
        player_color=chess.WHITE,
        depth=ENGINE_DEPTH
    ):
        """
        Создаёт новую шахматную партию.

        player_color:
            chess.WHITE
            или
            chess.BLACK

        depth:
            глубина анализа Stockfish
        """

        self.board = chess.Board()

        self.player_color = player_color

        self.depth = depth

        self.engine = None

        # ----------------------------------------------------
        # Проверяем наличие Stockfish
        # ----------------------------------------------------

        if not os.path.exists(ENGINE_PATH):
            raise FileNotFoundError(
                f"Stockfish не найден:\n{ENGINE_PATH}"
            )

        # ----------------------------------------------------
        # Запускаем Stockfish
        # ----------------------------------------------------

        self.engine = chess.engine.SimpleEngine.popen_uci(
            ENGINE_PATH
        )

    # ========================================================
    # ЗАКРЫТИЕ STOCKFISH
    # ========================================================

    def close(self):
        """
        Закрывает Stockfish.
        """

        if self.engine is not None:

            try:
                self.engine.quit()

            except Exception:
                pass

            self.engine = None

    # ========================================================
    # НОВАЯ ПАРТИЯ
    # ========================================================

    def reset(self):
        """
        Начинает новую партию.
        """

        self.board.reset()

    # ========================================================
    # ЛУЧШИЙ ХОД STOCKFISH
    # ========================================================

    def get_best_move(self):
        """
        Возвращает лучший ход Stockfish
        для текущей позиции.

        Результат:

            {
                "move": chess.Move,
                "san": "Nf3"
            }

        Если ход найти невозможно:
            None
        """

        if self.board.is_game_over():
            return None

        result = self.engine.analyse(
            self.board,
            chess.engine.Limit(
                depth=self.depth
            )
        )

        pv = result.get("pv")

        if not pv:
            return None

        best_move = pv[0]

        best_san = self.board.san(
            best_move
        )

        return {
            "move": best_move,
            "san": best_san
        }

    # ========================================================
    # ХОД ИГРОКА
    # ========================================================

    def make_player_move(self, uci_move):
        """
        Выполняет ход игрока.

        uci_move например:

            e2e4
            g1f3
            e1g1

        Перед выполнением хода определяется
        лучший ход Stockfish.

        Возвращает:

            {
                "played_move": chess.Move,
                "played_san": "e4",

                "best_move": chess.Move,
                "best_san": "Nf3",

                "is_best": False,

                "game_over": False
            }
        """

        # ----------------------------------------------------
        # Проверяем, действительно ли сейчас ход игрока
        # ----------------------------------------------------

        if self.board.turn != self.player_color:
            raise ValueError(
                "Сейчас ход компьютера."
            )

        # ----------------------------------------------------
        # Проверяем, не закончилась ли партия
        # ----------------------------------------------------

        if self.board.is_game_over():
            raise ValueError(
                "Партия уже закончена."
            )

        # ----------------------------------------------------
        # Получаем лучший ход ДО хода игрока
        # ----------------------------------------------------

        best_result = self.get_best_move()

        if best_result is None:
            raise ValueError(
                "Stockfish не смог определить лучший ход."
            )

        best_move = best_result["move"]
        best_san = best_result["san"]

        # ----------------------------------------------------
        # Преобразуем UCI в chess.Move
        # ----------------------------------------------------

        try:
            move = chess.Move.from_uci(
                uci_move
            )

        except ValueError:
            raise ValueError(
                f"Некорректный ход: {uci_move}"
            )

        # ----------------------------------------------------
        # Проверяем легальность
        # ----------------------------------------------------

        if move not in self.board.legal_moves:
            raise ValueError(
                f"Недопустимый ход: {uci_move}"
            )

        # ----------------------------------------------------
        # Получаем SAN ДО push()
        # ----------------------------------------------------

        played_san = self.board.san(
            move
        )

        # ----------------------------------------------------
        # Проверяем, совпадает ли ход с лучшим
        # ----------------------------------------------------

        is_best = (
            move == best_move
        )

        # ----------------------------------------------------
        # Делаем ход игрока
        # ----------------------------------------------------

        self.board.push(move)

        # ----------------------------------------------------
        # Возвращаем результат
        # ----------------------------------------------------

        return {
            "played_move": move,
            "played_san": played_san,

            "best_move": best_move,
            "best_san": best_san,

            "is_best": is_best,

            "game_over": self.board.is_game_over()
        }

    # ========================================================
    # ХОД КОМПЬЮТЕРА
    # ========================================================

    def make_computer_move(self):
        """
        Делает ход компьютера.

        Возвращает:

            {
                "move": chess.Move,
                "san": "e5",
                "game_over": False
            }
        """

        # ----------------------------------------------------
        # Проверяем очередь хода
        # ----------------------------------------------------

        if self.board.turn == self.player_color:
            raise ValueError(
                "Сейчас ход игрока."
            )

        # ----------------------------------------------------
        # Проверяем конец партии
        # ----------------------------------------------------

        if self.board.is_game_over():
            return None

        # ----------------------------------------------------
        # Получаем ход Stockfish
        # ----------------------------------------------------

        result = self.engine.play(
            self.board,
            chess.engine.Limit(
                depth=self.depth
            )
        )

        move = result.move

        if move is None:
            return None

        # ----------------------------------------------------
        # SAN до push()
        # ----------------------------------------------------

        san = self.board.san(
            move
        )

        # ----------------------------------------------------
        # Делаем ход
        # ----------------------------------------------------

        self.board.push(move)

        # ----------------------------------------------------
        # Возвращаем результат
        # ----------------------------------------------------

        return {
            "move": move,
            "san": san,

            "game_over": self.board.is_game_over()
        }

    # ========================================================
    # FEN
    # ========================================================

    def get_fen(self):
        """
        Возвращает текущую позицию в FEN.
        """

        return self.board.fen()

    # ========================================================
    # ХОДЫ
    # ========================================================

    def get_legal_moves(self):
        """
        Возвращает список легальных ходов
        в UCI-формате.
        """

        return [
            move.uci()
            for move in self.board.legal_moves
        ]

    # ========================================================
    # ТЕКУЩИЙ ХОД
    # ========================================================

    def is_player_turn(self):
        """
        Проверяет, ход игрока или нет.
        """

        return (
            self.board.turn
            == self.player_color
        )

    # ========================================================
    # КОНЕЦ ПАРТИИ
    # ========================================================

    def is_game_over(self):
        """
        Проверяет, закончилась ли партия.
        """

        return self.board.is_game_over()

    # ========================================================
    # РЕЗУЛЬТАТ ПАРТИИ
    # ========================================================

    def get_result(self):
        """
        Возвращает результат партии:

            "1-0"
            "0-1"
            "1/2-1/2"
            "*"
        """

        return self.board.result()

    # ========================================================
    # СТАТУС ПАРТИИ
    # ========================================================

    def get_status(self):
        """
        Возвращает понятный статус партии.
        """

        if self.board.is_checkmate():

            # Если мат поставлен стороне,
            # которая сейчас должна ходить,
            # значит предыдущий игрок победил.

            if self.board.turn == chess.WHITE:
                return "checkmate_black"

            return "checkmate_white"

        if self.board.is_stalemate():
            return "stalemate"

        if self.board.is_insufficient_material():
            return "draw_insufficient_material"

        if self.board.is_fifty_moves():
            return "draw_fifty_moves"

        if self.board.is_repetition():
            return "draw_repetition"

        if self.board.is_check():
            return "check"

        return "playing"

    # ========================================================
    # ТЕКУЩАЯ ПОЗИЦИЯ
    # ========================================================

    def get_board(self):
        """
        Возвращает объект chess.Board.

        Это понадобится позже для Telegram-доски.
        """

        return self.board