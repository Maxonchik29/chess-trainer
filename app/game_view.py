import tkinter as tk
from tkinter import messagebox
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

    board_frame.pack(
        pady=20
    )

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

            square = chess.square(
                col,
                7 - row
            )

            piece = board.piece_at(
                square
            )

            text = ""

            if piece:

                text = symbols[
                    piece.symbol()
                ]

            color = (
                "white"
                if (row + col) % 2 == 0
                else "gray"
            )

            cell = tk.Label(
                board_frame,
                text=text,
                width=3,
                height=1,
                font=("Arial", 24),
                bg=color,
                relief="solid"
            )

            cell.grid(
                row=row,
                column=col
            )

            cells[square] = cell

    return board_frame, cells


def open_game_view(window, filename):

    # ============================================================
    # ОКНО ПРОСМОТРА ПАРТИИ
    # ============================================================

    game_window = tk.Toplevel(window)

    game_window.title(
        "Просмотр партии"
    )

    game_window.geometry(
        "900x800"
    )

    # ============================================================
    # ГЛАВНЫЙ КОНТЕЙНЕР
    # ============================================================

    container = tk.Frame(
        game_window
    )

    container.pack(
        fill="both",
        expand=True
    )

    # ============================================================
    # CANVAS
    # ============================================================

    canvas = tk.Canvas(
        container,
        highlightthickness=0
    )

    scrollbar = tk.Scrollbar(
        container,
        orient="vertical",
        command=canvas.yview
    )

    canvas.configure(
        yscrollcommand=scrollbar.set
    )

    scrollbar.pack(
        side="right",
        fill="y"
    )

    canvas.pack(
        side="left",
        fill="both",
        expand=True
    )

    # ============================================================
    # ПРОКРУЧИВАЕМЫЙ FRAME
    # ============================================================

    scrollable_frame = tk.Frame(
        canvas
    )

    canvas_window = canvas.create_window(
        (0, 0),
        window=scrollable_frame,
        anchor="nw"
    )

    # ============================================================
    # ОБНОВЛЕНИЕ ОБЛАСТИ ПРОКРУТКИ
    # ============================================================

    def update_scrollregion(event=None):

        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    scrollable_frame.bind(
        "<Configure>",
        update_scrollregion
    )

    # ============================================================
    # РАСТЯГИВАЕМ FRAME ПО ШИРИНЕ CANVAS
    # ============================================================

    def update_frame_width(event):

        canvas.itemconfig(
            canvas_window,
            width=event.width
        )

    canvas.bind(
        "<Configure>",
        update_frame_width
    )

    # ============================================================
    # ПРОКРУТКА КОЛЁСИКОМ
    # ============================================================

    def on_mousewheel(event):

        canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    def bind_mousewheel(event):

        canvas.bind_all(
            "<MouseWheel>",
            on_mousewheel
        )

    def unbind_mousewheel(event):

        canvas.unbind_all(
            "<MouseWheel>"
        )

    scrollable_frame.bind(
        "<Enter>",
        bind_mousewheel
    )

    scrollable_frame.bind(
        "<Leave>",
        unbind_mousewheel
    )

    # ============================================================
    # ЗАКРЫТИЕ ОКНА
    # ============================================================

    def close_game_window():

        canvas.unbind_all(
            "<MouseWheel>"
        )

        game_window.destroy()

    game_window.protocol(
        "WM_DELETE_WINDOW",
        close_game_window
    )

    # ============================================================
    # ЗАГРУЗКА PGN
    # ============================================================

    filepath = os.path.join(
        "games",
        filename
    )

    with open(
        filepath,
        encoding="utf-8"
    ) as pgn_file:

        game = chess.pgn.read_game(
            pgn_file
        )

        opening = detect_opening(
            game
        )

    # ============================================================
    # ДОСКА
    # ============================================================

    board = game.board()

    moves = list(
        game.mainline_moves()
    )

    current_move = {
        "index": 0
    }

    # ============================================================
    # НАЗВАНИЕ ФАЙЛА
    # ============================================================

    title2 = tk.Label(
        scrollable_frame,
        text=filename,
        font=("Arial", 14)
    )

    title2.pack(
        pady=5
    )

    # ============================================================
    # ЗАГОЛОВОК
    # ============================================================

    title = tk.Label(
        scrollable_frame,
        text="Просмотр партии",
        font=("Arial", 20, "bold")
    )

    title.pack(
        pady=20
    )

    # ============================================================
    # ДОСКА
    # ============================================================

    board_frame, cells = draw_board(
        scrollable_frame,
        board
    )

    # ============================================================
    # НОМЕР ХОДА
    # ============================================================

    move_label = tk.Label(
        scrollable_frame,
        text=(
            f"Ход: {current_move['index']} "
            f"из {len(moves)}"
        ),
        font=("Arial", 14)
    )

    move_label.pack(
        pady=5
    )

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

    # ============================================================
    # ОБНОВЛЕНИЕ ДОСКИ
    # ============================================================

    def refresh_board():

        for square, cell in cells.items():

            piece = board.piece_at(
                square
            )

            if piece:

                cell.config(
                    text=symbols[
                        piece.symbol()
                    ]
                )

            else:

                cell.config(
                    text=""
                )

        move_label.config(
            text=(
                f"Ход: {current_move['index']} "
                f"из {len(moves)}"
            )
        )

    # ============================================================
    # СЛЕДУЮЩИЙ ХОД
    # ============================================================

    def next_move():

        if current_move["index"] < len(moves):

            board.push(
                moves[
                    current_move["index"]
                ]
            )

            current_move["index"] += 1

            refresh_board()

    # ============================================================
    # ПРЕДЫДУЩИЙ ХОД
    # ============================================================

    def previous_move():

        if current_move["index"] > 0:

            board.pop()

            current_move["index"] -= 1

            refresh_board()

    # ============================================================
    # КНОПКА ПРЕДЫДУЩЕГО ХОДА
    # ============================================================

    prev_button = tk.Button(
        scrollable_frame,
        text="◀ Предыдущий ход",
        width=20,
        command=previous_move
    )

    prev_button.pack(
        pady=5
    )

    # ============================================================
    # КНОПКА СЛЕДУЮЩЕГО ХОДА
    # ============================================================

    next_button = tk.Button(
        scrollable_frame,
        text="Следующий ход ▶",
        width=20,
        command=next_move
    )

    next_button.pack(
        pady=5
    )

    # ============================================================
    # РЕЖИМ АНАЛИЗА
    # ============================================================

    mode_frame = tk.LabelFrame(
        scrollable_frame,
        text="Режим анализа",
        font=("Arial", 11, "bold"),
        padx=10,
        pady=8
    )

    mode_frame.pack(
        pady=10
    )

    analysis_mode = tk.StringVar(
        value="my"
    )

    tk.Radiobutton(
        mode_frame,
        text="Мои ошибки",
        variable=analysis_mode,
        value="my",
        font=("Arial", 11)
    ).grid(
        row=0,
        column=0,
        padx=8,
        pady=3
    )

    tk.Radiobutton(
        mode_frame,
        text="Оба игрока",
        variable=analysis_mode,
        value="both",
        font=("Arial", 11)
    ).grid(
        row=0,
        column=1,
        padx=8,
        pady=3
    )

    tk.Radiobutton(
        mode_frame,
        text="Только белые",
        variable=analysis_mode,
        value="white",
        font=("Arial", 11)
    ).grid(
        row=0,
        column=2,
        padx=8,
        pady=3
    )

    tk.Radiobutton(
        mode_frame,
        text="Только чёрные",
        variable=analysis_mode,
        value="black",
        font=("Arial", 11)
    ).grid(
        row=0,
        column=3,
        padx=8,
        pady=3
    )

    # ============================================================
    # ДИАПАЗОН АНАЛИЗА
    # ============================================================

    range_frame = tk.LabelFrame(
        scrollable_frame,
        text="Диапазон анализа",
        font=("Arial", 11, "bold"),
        padx=10,
        pady=10
    )

    range_frame.pack(
        pady=10
    )

    # ============================================================
    # С ХОДА
    # ============================================================

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

    # ============================================================
    # ПО ХОД
    # ============================================================

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

    # ============================================================
    # ПОДСКАЗКА ДЛЯ КОНЦА
    # ============================================================

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

    # ============================================================
    # ОБЩАЯ ПОДСКАЗКА
    # ============================================================

    range_hint = tk.Label(
        scrollable_frame,
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

        # ========================================================
        # ПОЛУЧАЕМ РЕЖИМ
        # ========================================================

        selected_analysis_mode = analysis_mode.get()

        # ========================================================
        # ПОЛУЧАЕМ НАЧАЛО ДИАПАЗОНА
        # ========================================================

        start_text = start_move_entry.get().strip()

        if not start_text:

            start_move = 1

        else:

            try:

                start_move = int(
                    start_text
                )

            except ValueError:

                messagebox.showerror(
                    "Ошибка",
                    (
                        "Поле «С хода» должно "
                        "содержать целое число."
                    )
                )

                return

        # ========================================================
        # ПРОВЕРЯЕМ НАЧАЛО
        # ========================================================

        if start_move < 1:

            messagebox.showerror(
                "Ошибка",
                (
                    "Номер начального хода "
                    "должен быть не меньше 1."
                )
            )

            return

        # ========================================================
        # ПОЛУЧАЕМ КОНЕЦ ДИАПАЗОНА
        # ========================================================

        end_text = end_move_entry.get().strip()

        if not end_text:

            end_move = None

        else:

            try:

                end_move = int(
                    end_text
                )

            except ValueError:

                messagebox.showerror(
                    "Ошибка",
                    (
                        "Поле «По ход» должно "
                        "содержать целое число."
                    )
                )

                return

        # ========================================================
        # ПРОВЕРЯЕМ КОНЕЦ
        # ========================================================

        if end_move is not None:

            if end_move < 1:

                messagebox.showerror(
                    "Ошибка",
                    (
                        "Номер конечного хода "
                        "должен быть не меньше 1."
                    )
                )

                return

            if end_move < start_move:

                messagebox.showerror(
                    "Ошибка",
                    (
                        "Конечный ход не может "
                        "быть меньше начального."
                    )
                )

                return

        # ========================================================
        # ПРОВЕРЯЕМ ДИАПАЗОН ПАРТИИ
        # ========================================================

        total_fullmoves = (
            game.end().board().fullmove_number
        )

        max_fullmove = max(
            1,
            (len(moves) + 1) // 2
        )

        if start_move > max_fullmove:

            messagebox.showerror(
                "Ошибка",
                (
                    f"В этой партии нет хода "
                    f"{start_move}.\n"
                    f"Последний полный номер хода "
                    f"примерно: {max_fullmove}."
                )
            )

            return

        if (
            end_move is not None
            and end_move > max_fullmove
        ):

            end_move = max_fullmove

            end_move_entry.delete(
                0,
                tk.END
            )

            end_move_entry.insert(
                0,
                str(end_move)
            )

        # ========================================================
        # ТЕКСТ ДИАПАЗОНА
        # ========================================================

        if end_move is None:

            range_text = (
                f"С хода {start_move} "
                f"до конца партии"
            )

        else:

            range_text = (
                f"Ходы {start_move}–{end_move}"
            )

        # ========================================================
        # DEBUG
        # ========================================================

        print(
            "\n" + "=" * 60
        )

        print(
            "ЗАПУСК АНАЛИЗА"
        )

        print(
            "Файл:",
            filename
        )

        print(
            "Режим:",
            selected_analysis_mode
        )

        print(
            "Диапазон:",
            range_text
        )

        print(
            "=" * 60
        )

        # ========================================================
        # АНАЛИЗ
        # ========================================================

        mistakes, scores, accuracy, statistics, phase_statistics, user_color = analyze_game(
            game,
            start_move=start_move,
            end_move=end_move,
            analysis_mode=selected_analysis_mode
        )

        # ========================================================
        # DEBUG-ФАЙЛ
        # ========================================================

        with open(
            "debug_mistakes.txt",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ПАРТИЯ:\n"
            )

            f.write(
                f"White: "
                f"{game.headers.get('White')}\n"
            )

            f.write(
                f"Black: "
                f"{game.headers.get('Black')}\n"
            )

            f.write(
                f"Date: "
                f"{game.headers.get('Date')}\n"
            )

            f.write(
                f"Result: "
                f"{game.headers.get('Result')}\n"
            )

            f.write(
                f"РЕЖИМ АНАЛИЗА: "
                f"{selected_analysis_mode}\n"
            )

            f.write(
                f"\nКоличество ошибок: "
                f"{len(mistakes)}\n\n"
            )

            for i, m in enumerate(
                mistakes,
                1
            ):

                f.write(
                    f"===== ОШИБКА #{i} =====\n"
                )

                f.write(
                    f"White: "
                    f"{m.get('game_white')}\n"
                )

                f.write(
                    f"Black: "
                    f"{m.get('game_black')}\n"
                )

                f.write(
                    f"Date: "
                    f"{m.get('game_date')}\n"
                )

                f.write(
                    f"Result: "
                    f"{m.get('game_result')}\n"
                )

                f.write(
                    f"Move: "
                    f"{m.get('move')}\n"
                )

                f.write(
                    f"Played: "
                    f"{m.get('played_san')}\n"
                )

                f.write(
                    f"Best: "
                    f"{m.get('best')}\n"
                )

                f.write(
                    f"FEN: "
                    f"{m.get('fen')}\n"
                )

                f.write(
                    f"Explanation: "
                    f"{m.get('explanation')}\n\n"
                )

        # ========================================================
        # DEBUG В КОНСОЛЬ
        # ========================================================

        print(
            "\n" + "=" * 60
        )

        print(
            "ПЕРЕД ОТКРЫТИЕМ ОКНА АНАЛИЗА"
        )

        print(
            "mistakes id =",
            id(mistakes)
        )

        print(
            "Количество =",
            len(mistakes)
        )

        print(
            "Диапазон =",
            range_text
        )

        for i, m in enumerate(
            mistakes,
            1
        ):

            print(
                i,
                "ход =",
                m.get("move"),
                "сыграно =",
                m.get("played_san"),
                "best =",
                m.get("best"),
                "FEN =",
                m.get("fen")
            )

        print(
            "=" * 60
        )

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
        #
        # Только режим "Мои ошибки".
        # Анализ чужой партии или обеих сторон
        # не должен менять личную статистику.
        # ========================================================

        if selected_analysis_mode == "my":

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
        scrollable_frame,
        text="🔍 Анализировать",
        width=20,
        font=("Arial", 11),
        command=start_analysis
    )

    analyze_button.pack(
        pady=5
    )

    # ============================================================
    # КНОПКА НАЗАД
    # ============================================================

    back_button = tk.Button(
        scrollable_frame,
        text="Назад",
        width=20,
        command=close_game_window
    )

    back_button.pack(
        pady=20
    )

    # ============================================================
    # ОБНОВЛЯЕМ SCROLLREGION ПОСЛЕ СОЗДАНИЯ ВСЕХ WIDGETS
    # ============================================================

    game_window.update_idletasks()

    canvas.configure(
        scrollregion=canvas.bbox("all")
    )

    canvas.yview_moveto(
        0
    )