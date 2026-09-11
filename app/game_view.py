import tkinter as tk
import chess
import chess.pgn
import os

from app.analysis import analyze_game
from app.app.analysis_window import show_analysis
from app.opening_detector import detect_opening
from app.player_statistics import update_player_statistics
from app.history import update_history


def draw_board(window, board):

    board_frame = tk.Frame(window)
    board_frame.pack(pady=20)

    symbols = {
        "P": "♙",
        "N": "♘",
        "B": "♗",
        "R": "♖",
        "Q": "♕",
        "K": "♔",

        "p": "♟",
        "n": "♞",
        "b": "♝",
        "r": "♜",
        "q": "♛",
        "k": "♚"
    }

    cells = {}

    for row in range(8):
        for col in range(8):

            square = chess.square(col, 7 - row)

            piece = board.piece_at(square)

            text = ""

            if piece:
                text = symbols[piece.symbol()]

            color = "white" if (row + col) % 2 == 0 else "gray"

            cell = tk.Label(
                board_frame,
                text=text,
                width=3,
                height=1,
                font=("Arial", 24),
                bg=color,
                relief="solid"
            )

            cell.grid(row=row, column=col)

            cells[square] = cell

    return board_frame, cells


def open_game_view(window, filename):

    game_window = tk.Toplevel(window)
    game_window.title("Просмотр партии")
    game_window.geometry("900x800")

    filepath = os.path.join("games", filename)

    with open(filepath, encoding="utf-8") as pgn_file:
        game = chess.pgn.read_game(pgn_file)
        opening = detect_opening(game)

    board = game.board()
    moves = list(game.mainline_moves())
    current_move = {"index": 0}

    title2 = tk.Label(
        game_window,
        text=filename,
        font=("Arial", 14)
    )
    title2.pack(pady=5)

    title = tk.Label(
        game_window,
        text="Просмотр партии",
        font=("Arial", 20, "bold")
    )
    title.pack(pady=20)

    board_frame, cells = draw_board(game_window, board)

    move_label = tk.Label(
        game_window,
        text=f"Ход: {current_move['index']} из {len(moves)}",
        font=("Arial", 14)
    )
    move_label.pack(pady=5)

    symbols = {
        "P": "♙",
        "N": "♘",
        "B": "♗",
        "R": "♖",
        "Q": "♕",
        "K": "♔",
        "p": "♟",
        "n": "♞",
        "b": "♝",
        "r": "♜",
        "q": "♛",
        "k": "♚"
    }

    def refresh_board():

        for square, cell in cells.items():

            piece = board.piece_at(square)

            if piece:
                cell.config(
                    text=symbols[piece.symbol()]
                )
            else:
                cell.config(
                    text=""
                )

        move_label.config(
            text=f"Ход: {current_move['index']} из {len(moves)}"
        )

    def next_move():

        if current_move["index"] < len(moves):

            board.push(
                moves[current_move["index"]]
            )

            current_move["index"] += 1

            refresh_board()

    def previous_move():

        if current_move["index"] > 0:

            board.pop()

            current_move["index"] -= 1

            refresh_board()

    prev_button = tk.Button(
        game_window,
        text="◀ Предыдущий ход",
        width=20,
        command=previous_move
    )
    prev_button.pack(pady=5)

    next_button = tk.Button(
        game_window,
        text="Следующий ход ▶",
        width=20,
        command=next_move
    )
    next_button.pack(pady=5)

    # ============================================================
    # ДИАПАЗОН АНАЛИЗА
    # ============================================================

    range_frame = tk.LabelFrame(
        game_window,
        text="Диапазон анализа",
        font=("Arial", 11, "bold"),
        padx=10,
        pady=10
    )
    range_frame.pack(
        pady=10
    )

    # ------------------------------------------------------------
    # С хода
    # ------------------------------------------------------------

    start_label = tk.Label(
        range_frame,
        text="С хода:",
        font=("Arial", 11)
    )
    start_label.grid(
        row=0,
        column=0,
        padx=5,
        pady=5
    )

    start_move_entry = tk.Entry(
        range_frame,
        width=8,
        justify="center",
        font=("Arial", 11)
    )
    start_move_entry.grid(
        row=0,
        column=1,
        padx=5,
        pady=5
    )

    start_move_entry.insert(
        0,
        "1"
    )

    # ------------------------------------------------------------
    # По ход
    # ------------------------------------------------------------

    end_label = tk.Label(
        range_frame,
        text="По ход:",
        font=("Arial", 11)
    )
    end_label.grid(
        row=0,
        column=2,
        padx=5,
        pady=5
    )

    end_move_entry = tk.Entry(
        range_frame,
        width=8,
        justify="center",
        font=("Arial", 11)
    )
    end_move_entry.grid(
        row=0,
        column=3,
        padx=5,
        pady=5
    )

    # Пустое поле = анализ до конца партии

    end_hint = tk.Label(
        range_frame,
        text="(пусто = до конца)",
        font=("Arial", 9),
        fg="gray"
    )
    end_hint.grid(
        row=1,
        column=2,
        columnspan=2,
        padx=5,
        pady=2
    )

    # ------------------------------------------------------------
    # Подсказка
    # ------------------------------------------------------------

    range_hint = tk.Label(
        game_window,
        text=(
            "Например: 20 — 35\n"
            "Будут проанализированы только ходы с 20 по 35."
        ),
        font=("Arial", 10),
        fg="gray",
        justify="center"
    )
    range_hint.pack(
        pady=2
    )

    # ============================================================
    # ЗАПУСК АНАЛИЗА
    # ============================================================

    def start_analysis():

        # --------------------------------------------------------
        # Получаем начало диапазона
        # --------------------------------------------------------

        start_text = start_move_entry.get().strip()

        if not start_text:
            start_move = 1

        else:

            try:
                start_move = int(start_text)

            except ValueError:

                tk.messagebox.showerror(
                    "Ошибка",
                    "Поле «С хода» должно содержать целое число."
                )

                return

        # --------------------------------------------------------
        # Проверяем начало диапазона
        # --------------------------------------------------------

        if start_move < 1:

            tk.messagebox.showerror(
                "Ошибка",
                "Номер начального хода должен быть не меньше 1."
            )

            return

        # --------------------------------------------------------
        # Получаем конец диапазона
        # --------------------------------------------------------

        end_text = end_move_entry.get().strip()

        if not end_text:

            end_move = None

        else:

            try:
                end_move = int(end_text)

            except ValueError:

                tk.messagebox.showerror(
                    "Ошибка",
                    "Поле «По ход» должно содержать целое число."
                )

                return

        # --------------------------------------------------------
        # Проверяем конец диапазона
        # --------------------------------------------------------

        if end_move is not None:

            if end_move < 1:

                tk.messagebox.showerror(
                    "Ошибка",
                    "Номер конечного хода должен быть не меньше 1."
                )

                return

            if end_move < start_move:

                tk.messagebox.showerror(
                    "Ошибка",
                    "Конечный ход не может быть меньше начального."
                )

                return

        # --------------------------------------------------------
        # Проверяем, что диапазон вообще существует в партии
        # --------------------------------------------------------

        total_fullmoves = (
            game.end().board().fullmove_number
        )

        # Если партия закончилась после хода белых,
        # fullmove_number в конечной позиции может указывать
        # на следующий номер. Поэтому используем также количество
        # полуходов для более безопасной проверки.

        max_fullmove = max(
            1,
            (len(moves) + 1) // 2
        )

        if start_move > max_fullmove:

            tk.messagebox.showerror(
                "Ошибка",
                (
                    f"В этой партии нет хода {start_move}.\n"
                    f"Последний полный номер хода примерно: "
                    f"{max_fullmove}."
                )
            )

            return

        if (
            end_move is not None
            and end_move > max_fullmove
        ):

            # Не считаем это ошибкой.
            # Просто ограничиваем диапазон последним ходом партии.

            end_move = max_fullmove

            end_move_entry.delete(
                0,
                tk.END
            )

            end_move_entry.insert(
                0,
                str(end_move)
            )

        # --------------------------------------------------------
        # Показываем пользователю, что именно анализируем
        # --------------------------------------------------------

        if end_move is None:

            range_text = (
                f"С хода {start_move} до конца партии"
            )

        else:

            range_text = (
                f"Ходы {start_move}–{end_move}"
            )

        print("\n" + "=" * 60)
        print("ЗАПУСК АНАЛИЗА")
        print("Файл:", filename)
        print("Диапазон:", range_text)
        print("=" * 60)

        # --------------------------------------------------------
        # ВАЖНО:
        #
        # Передаём именно исходный game.
        #
        # Текущее положение доски game_window.board здесь
        # не имеет значения.
        # --------------------------------------------------------

        mistakes, scores, accuracy, statistics, phase_statistics, user_color = analyze_game(
            game,
            start_move=start_move,
            end_move=end_move
        )

        # ========================================================
        # DEBUG
        # ========================================================

        with open(
            "debug_mistakes.txt",
            "w",
            encoding="utf-8"
        ) as f:

            f.write("ПАРТИЯ:\n")
            f.write(
                f"White: {game.headers.get('White')}\n"
            )
            f.write(
                f"Black: {game.headers.get('Black')}\n"
            )
            f.write(
                f"Date: {game.headers.get('Date')}\n"
            )
            f.write(
                f"Result: {game.headers.get('Result')}\n"
            )

            f.write(
                f"\nДИАПАЗОН АНАЛИЗА: {range_text}\n"
            )

            f.write(
                f"\nКоличество ошибок: {len(mistakes)}\n\n"
            )

            for i, m in enumerate(
                mistakes,
                1
            ):

                f.write(
                    f"===== ОШИБКА #{i} =====\n"
                )

                f.write(
                    f"White: {m.get('game_white')}\n"
                )

                f.write(
                    f"Black: {m.get('game_black')}\n"
                )

                f.write(
                    f"Date: {m.get('game_date')}\n"
                )

                f.write(
                    f"Result: {m.get('game_result')}\n"
                )

                f.write(
                    f"Move: {m.get('move')}\n"
                )

                f.write(
                    f"Played: {m.get('played_san')}\n"
                )

                f.write(
                    f"Best: {m.get('best')}\n"
                )

                f.write(
                    f"FEN: {m.get('fen')}\n"
                )

                f.write(
                    f"Explanation: {m.get('explanation')}\n\n"
                )

        # ========================================================
        # DEBUG В КОНСОЛЬ
        # ========================================================

        print("\n" + "=" * 60)
        print("ПЕРЕД ОТКРЫТИЕМ ОКНА АНАЛИЗА")
        print("mistakes id =", id(mistakes))
        print("Количество =", len(mistakes))
        print("Диапазон =", range_text)

        for i, m in enumerate(
            mistakes,
            1
        ):

            print(
                i,
                "ход =", m.get("move"),
                "сыграно =", m.get("played_san"),
                "best =", m.get("best"),
                "FEN =", m.get("fen")
            )

        print("=" * 60)

        # ========================================================
        # ИСТОРИЯ
        # ========================================================

        update_history({
            "file": filename,
            "accuracy": accuracy,
            "opening": (
                opening["name"]
                if opening
                else "Неизвестный дебют"
            ),
            "statistics": statistics
        })

        # ========================================================
        # СТАТИСТИКА ИГРОКА
        # ========================================================

        update_player_statistics(
            statistics
        )

        # ========================================================
        # ОКНО РЕЗУЛЬТАТОВ
        # ========================================================

        show_analysis(
            window,
            mistakes,
            scores,
            accuracy,
            opening,
            statistics,
            phase_statistics,
            user_color
        )

    # ============================================================
    # КНОПКА АНАЛИЗА
    # ============================================================

    analyze_button = tk.Button(
        game_window,
        text="🔍 Анализировать",
        width=20,
        command=start_analysis
    )
    analyze_button.pack(
        pady=5
    )

    # ============================================================
    # КНОПКА НАЗАД
    # ============================================================

    back_button = tk.Button(
        game_window,
        text="Назад",
        width=20,
        command=game_window.destroy
    )
    back_button.pack(
        pady=20
    )