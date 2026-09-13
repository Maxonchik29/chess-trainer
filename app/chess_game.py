import os
import chess
import chess.engine
import chess.pgn
import io


# ============================================================
# НАСТРОЙКИ STOCKFISH
# ============================================================

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
        """

        self.board = chess.Board()

        self.player_color = player_color

        self.depth = depth

        self.engine = None

        # ====================================================
        # ИСТОРИЯ ХОДОВ
        # ====================================================

        self.move_history = []

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

        # ----------------------------------------------------
        # ОЧИЩАЕМ ИСТОРИЮ
        # ----------------------------------------------------

        self.move_history = []

    # ========================================================
    # ЛУЧШИЙ ХОД STOCKFISH
    # ========================================================

    def get_best_move(self):

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

        # ----------------------------------------------------
        # Проверяем очередь хода
        # ----------------------------------------------------

        if self.board.turn != self.player_color:
            raise ValueError(
                "Сейчас ход компьютера."
            )

        # ----------------------------------------------------
        # Проверяем конец партии
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
        # Преобразуем UCI
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
        # SAN ДО PUSH
        # ----------------------------------------------------

        played_san = self.board.san(
            move
        )

        # ----------------------------------------------------
        # Проверяем лучший ход
        # ----------------------------------------------------

        is_best = (
            move == best_move
        )

        # ----------------------------------------------------
        # Делаем ход
        # ----------------------------------------------------

        self.board.push(move)

        # ====================================================
        # СОХРАНЯЕМ ХОД В ИСТОРИЮ
        # ====================================================

        self.move_history.append(
            move.uci()
        )

        # ----------------------------------------------------
        # Результат
        # ----------------------------------------------------

        return {

            "played_move": move,

            "played_san": played_san,

            "best_move": best_move,

            "best_san": best_san,

            "is_best": is_best,

            "game_over":
                self.board.is_game_over()
        }

    # ========================================================
    # ХОД КОМПЬЮТЕРА
    # ========================================================

    def make_computer_move(self):

        # ----------------------------------------------------
        # Проверяем очередь
        # ----------------------------------------------------

        if self.board.turn == self.player_color:

            raise ValueError(
                "Сейчас ход игрока."
            )

        # ----------------------------------------------------
        # Проверяем конец
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
        # SAN ДО PUSH
        # ----------------------------------------------------

        san = self.board.san(
            move
        )

        # ----------------------------------------------------
        # Делаем ход
        # ----------------------------------------------------

        self.board.push(move)

        # ====================================================
        # СОХРАНЯЕМ ХОД В ИСТОРИЮ
        # ====================================================

        self.move_history.append(
            move.uci()
        )

        # ----------------------------------------------------
        # Результат
        # ----------------------------------------------------

        return {

            "move": move,

            "san": san,

            "game_over":
                self.board.is_game_over()
        }

    # ========================================================
    # PGN ТЕКУЩЕЙ ПАРТИИ
    # ========================================================

    def get_pgn(self):
        """
        Возвращает текущую партию в формате PGN.

        Игрок:
            Maximka2912

        Компьютер:
            Stockfish
        """

        game = chess.pgn.Game()

        # ----------------------------------------------------
        # Заголовки
        # ----------------------------------------------------

        game.headers["Event"] = "Chess Trainer"
        game.headers["Site"] = "Telegram Mini App"
        game.headers["White"] = "Maximka2912"
        game.headers["Black"] = "Stockfish"
        game.headers["Result"] = self.board.result()

        # ----------------------------------------------------
        # Воспроизводим историю
        # ----------------------------------------------------

        node = game

        replay_board = chess.Board()

        for uci in self.move_history:

            try:

                move = chess.Move.from_uci(
                    uci
                )

            except ValueError:

                continue

            if move not in replay_board.legal_moves:
                continue

            node = node.add_variation(
                move
            )

            replay_board.push(
                move
            )

        # ----------------------------------------------------
        # Принудительно ставим результат
        # ----------------------------------------------------

        game.headers["Result"] = (
            self.board.result()
        )

        # ----------------------------------------------------
        # Получаем PGN
        # ----------------------------------------------------

        output = io.StringIO()

        exporter = chess.pgn.StringExporter(
            headers=True,
            variations=False,
            comments=False
        )

        game.accept(
            exporter
        )

        return exporter.result()

    # ========================================================
    # FEN
    # ========================================================

    def get_fen(self):

        return self.board.fen()

    # ========================================================
    # ХОДЫ
    # ========================================================

    def get_legal_moves(self):

        return [
            move.uci()
            for move in self.board.legal_moves
        ]

    # ========================================================
    # ТЕКУЩИЙ ХОД
    # ========================================================

    def is_player_turn(self):

        return (
            self.board.turn
            == self.player_color
        )

    # ========================================================
    # КОНЕЦ ПАРТИИ
    # ========================================================

    def is_game_over(self):

        return self.board.is_game_over()

    # ========================================================
    # РЕЗУЛЬТАТ ПАРТИИ
    # ========================================================

    def get_result(self):

        return self.board.result()

    # ========================================================
    # СТАТУС ПАРТИИ
    # ========================================================

    def get_status(self):

        if self.board.is_checkmate():

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

        return self.board