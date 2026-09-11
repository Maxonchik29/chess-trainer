import tkinter as tk
from tkinter import messagebox

import chess
import chess.pgn
import chess.engine
import os


# ============================================================
# НАСТРОЙКИ STOCKFISH
# ============================================================

ENGINE_PATH = os.path.join(
    "engine",
    "stockfish.exe"
)

ENGINE_DEPTH = 12


# ============================================================
# СИМВОЛЫ ШАХМАТНЫХ ФИГУР
# ============================================================

SYMBOLS = {
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
# ИГРА ПРОТИВ КОМПЬЮТЕРА
# ============================================================

def open_play_vs_computer(window):

    game_window = tk.Toplevel(window)

    game_window.title(
        "Игра с компьютером"
    )

    game_window.geometry(
        "1000x800"
    )

    game_window.resizable(
        False,
        False
    )

    # ========================================================
    # ПРОВЕРКА STOCKFISH
    # ========================================================

    if not os.path.exists(ENGINE_PATH):

        messagebox.showerror(
            "Ошибка",
            (
                "Stockfish не найден.\n\n"
                "Ожидаемый путь:\n"
                f"{ENGINE_PATH}"
            )
        )

        game_window.destroy()

        return

    # ========================================================
    # ЗАПУСК STOCKFISH
    # ========================================================

    try:

        engine = chess.engine.SimpleEngine.popen_uci(
            ENGINE_PATH
        )

    except Exception as e:

        messagebox.showerror(
            "Ошибка Stockfish",
            (
                "Не удалось запустить Stockfish.\n\n"
                f"{e}"
            )
        )

        game_window.destroy()

        return

    # ========================================================
    # СОСТОЯНИЕ
    # ========================================================

    board = chess.Board()

    selected_square = {
        "value": None
    }

    move_history = []

    game_finished = {
        "value": False
    }

    player_color = {
        "value": chess.WHITE
    }

    engine_depth = {
        "value": ENGINE_DEPTH
    }

    # ========================================================
    # ЗАГОЛОВОК
    # ========================================================

    title = tk.Label(
        game_window,
        text="♟ Игра с компьютером",
        font=("Arial", 22, "bold")
    )

    title.pack(
        pady=10
    )

    status_label = tk.Label(
        game_window,
        text="Ваш ход",
        font=("Arial", 14, "bold")
    )

    status_label.pack(
        pady=5
    )

    # ========================================================
    # ОСНОВНОЙ КОНТЕЙНЕР
    # ========================================================

    content_frame = tk.Frame(
        game_window
    )

    content_frame.pack(
        pady=10
    )

    # ========================================================
    # ДОСКА
    # ========================================================

    board_frame = tk.Frame(
        content_frame
    )

    board_frame.grid(
        row=0,
        column=0,
        padx=20
    )

    # ========================================================
    # ПАНЕЛЬ СПРАВА
    # ========================================================

    right_frame = tk.Frame(
        content_frame
    )

    right_frame.grid(
        row=0,
        column=1,
        sticky="n"
    )

    # ========================================================
    # СПИСОК ХОДОВ
    # ========================================================

    moves_title = tk.Label(
        right_frame,
        text="Ходы",
        font=("Arial", 14, "bold")
    )

    moves_title.pack(
        pady=5
    )

    moves_list = tk.Listbox(
        right_frame,
        width=25,
        height=18,
        font=("Arial", 12)
    )

    moves_list.pack(
        pady=5
    )

    # ========================================================
    # ОЦЕНКА
    # ========================================================

    evaluation_label = tk.Label(
        right_frame,
        text="Оценка: —",
        font=("Arial", 13, "bold")
    )

    evaluation_label.pack(
        pady=10
    )

    # ========================================================
    # ЦВЕТ КЛЕТКИ
    # ========================================================

    def get_square_color(
        row,
        col
    ):

        if (row + col) % 2 == 0:

            return "white"

        return "gray"

    # ========================================================
    # ОБНОВЛЕНИЕ ДОСКИ
    # ========================================================

    def refresh_board():

        for square, cell in cells.items():

            piece = board.piece_at(
                square
            )

            if piece:

                cell.config(
                    text=SYMBOLS[
                        piece.symbol()
                    ]
                )

            else:

                cell.config(
                    text=""
                )

            row = 7 - chess.square_rank(
                square
            )

            col = chess.square_file(
                square
            )

            cell.config(
                bg=get_square_color(
                    row,
                    col
                )
            )

        selected = selected_square["value"]

        if selected is not None:

            cells[selected].config(
                bg="yellow"
            )

    # ========================================================
    # СОЗДАНИЕ КЛЕТОК
    # ========================================================

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

                text = SYMBOLS[
                    piece.symbol()
                ]

            cell = tk.Label(
                board_frame,
                text=text,
                width=4,
                height=2,
                font=("Arial", 24),
                bg=get_square_color(
                    row,
                    col
                ),
                relief="solid",
                borderwidth=1
            )

            cell.grid(
                row=row,
                column=col
            )

            cells[square] = cell

    # ========================================================
    # ОБНОВЛЕНИЕ СПИСКА ХОДОВ
    # ========================================================

    def refresh_move_list():

        moves_list.delete(
            0,
            tk.END
        )

        for i in range(
            0,
            len(move_history),
            2
        ):

            move_number = (
                i // 2
            ) + 1

            white_move = (
                move_history[i]
            )

            if i + 1 < len(
                move_history
            ):

                black_move = (
                    move_history[i + 1]
                )

                text = (
                    f"{move_number}. "
                    f"{white_move} "
                    f"{black_move}"
                )

            else:

                text = (
                    f"{move_number}. "
                    f"{white_move}"
                )

            moves_list.insert(
                tk.END,
                text
            )

    # ========================================================
    # ПРОВЕРКА ОКОНЧАНИЯ
    # ========================================================

    def check_game_over():

        if not board.is_game_over():

            return False

        game_finished["value"] = True

        result = board.result()

        if board.is_checkmate():

            if board.turn == chess.WHITE:

                text = (
                    "Мат!\n\n"
                    "Компьютер победил."
                )

            else:

                text = (
                    "Мат!\n\n"
                    "Вы победили!"
                )

        elif board.is_stalemate():

            text = (
                "Пат!\n\n"
                "Ничья."
            )

        elif board.is_insufficient_material():

            text = (
                "Недостаточно материала.\n\n"
                "Ничья."
            )

        else:

            text = (
                "Партия окончена.\n\n"
                f"Результат: {result}"
            )

        status_label.config(
            text=text.replace(
                "\n\n",
                " "
            )
        )

        messagebox.showinfo(
            "Партия окончена",
            text
        )

        return True

    # ========================================================
    # ФОРМАТИРОВАНИЕ ОЦЕНКИ
    # ========================================================

    def format_score(score):

        if score is None:

            return "?"

        if score.is_mate():

            mate = score.mate()

            if mate is None:

                return "M?"

            if mate > 0:

                return f"M{mate}"

            return f"-M{abs(mate)}"

        cp = score.score(
            mate_score=100000
        )

        if cp is None:

            return "?"

        return f"{cp / 100:+.2f}"

    # ========================================================
    # ПЕРЕВОД SCORE В CP
    # ========================================================

    def score_to_cp(score):

        if score is None:

            return None

        return score.score(
            mate_score=100000
        )

    # ========================================================
    # ОЦЕНКА ПОЗИЦИИ
    # ========================================================

    def update_evaluation():

        if game_finished["value"]:

            return

        try:

            info = engine.analyse(
                board,
                chess.engine.Limit(
                    depth=engine_depth["value"]
                )
            )

            score = info["score"].pov(
                chess.WHITE
            )

            text = (
                f"Оценка: "
                f"{format_score(score)}"
            )

            evaluation_label.config(
                text=text
            )

        except Exception:

            evaluation_label.config(
                text="Оценка: —"
            )

    # ========================================================
    # ПОДСКАЗКА
    # ========================================================

    def show_hint():

        if game_finished["value"]:

            return

        if board.turn != player_color["value"]:

            messagebox.showinfo(
                "Подсказка",
                "Сейчас ход компьютера."
            )

            return

        try:

            result = engine.play(
                board,
                chess.engine.Limit(
                    depth=engine_depth["value"]
                )
            )

            best_move = result.move

            san = board.san(
                best_move
            )

            from_square = (
                chess.square_name(
                    best_move.from_square
                )
            )

            to_square = (
                chess.square_name(
                    best_move.to_square
                )
            )

            selected_square["value"] = (
                best_move.from_square
            )

            refresh_board()

            messagebox.showinfo(
                "💡 Подсказка",
                (
                    f"Лучший ход: {san}\n\n"
                    f"{from_square} → {to_square}"
                )
            )

            selected_square["value"] = None

            refresh_board()

        except Exception as e:

            messagebox.showerror(
                "Ошибка Stockfish",
                str(e)
            )

    # ========================================================
    # ОТМЕНА ХОДА
    # ========================================================

    def undo_move():

        if game_finished["value"]:

            return

        if len(board.move_stack) == 0:

            return

        if len(board.move_stack) >= 2:

            board.pop()
            board.pop()

            if len(move_history) >= 2:

                move_history.pop()
                move_history.pop()

        else:

            board.pop()

            if move_history:

                move_history.pop()

        selected_square["value"] = None

        refresh_board()

        refresh_move_list()

        status_label.config(
            text="Ваш ход"
        )

        evaluation_label.config(
            text="Оценка: —"
        )

    # ========================================================
    # ХОД КОМПЬЮТЕРА
    # ========================================================

    def computer_move():

        if game_finished["value"]:

            return

        if board.turn != player_color["value"]:

            status_label.config(
                text="Компьютер думает..."
            )

            game_window.update()

            try:

                result = engine.play(
                    board,
                    chess.engine.Limit(
                        depth=engine_depth["value"]
                    )
                )

                computer_move_obj = (
                    result.move
                )

                san = board.san(
                    computer_move_obj
                )

                board.push(
                    computer_move_obj
                )

                move_history.append(
                    san
                )

                refresh_board()

                refresh_move_list()

                if check_game_over():

                    return

                if board.is_check():

                    status_label.config(
                        text="Ваш ход — шах!"
                    )

                else:

                    status_label.config(
                        text="Ваш ход"
                    )

                update_evaluation()

            except Exception as e:

                status_label.config(
                    text="Ошибка компьютера"
                )

                messagebox.showerror(
                    "Ошибка Stockfish",
                    str(e)
                )

    # ========================================================
    # ХОД ИГРОКА
    # ========================================================

    def player_click(
        square
    ):

        if game_finished["value"]:

            return

        if board.turn != player_color["value"]:

            return

        if selected_square["value"] is None:

            piece = board.piece_at(
                square
            )

            if piece is None:

                return

            if piece.color != player_color["value"]:

                return

            selected_square["value"] = (
                square
            )

            refresh_board()

            return

        from_square = (
            selected_square["value"]
        )

        to_square = square

        if from_square == to_square:

            selected_square["value"] = None

            refresh_board()

            return

        piece = board.piece_at(
            to_square
        )

        if (
            piece is not None
            and piece.color == player_color["value"]
        ):

            selected_square["value"] = (
                to_square
            )

            refresh_board()

            return

        move = chess.Move(
            from_square,
            to_square
        )

        piece_from = board.piece_at(
            from_square
        )

        if (
            piece_from is not None
            and piece_from.piece_type
            == chess.PAWN
        ):

            to_rank = chess.square_rank(
                to_square
            )

            if (
                player_color["value"]
                == chess.WHITE
                and to_rank == 7
            ):

                move = chess.Move(
                    from_square,
                    to_square,
                    promotion=chess.QUEEN
                )

            elif (
                player_color["value"]
                == chess.BLACK
                and to_rank == 0
            ):

                move = chess.Move(
                    from_square,
                    to_square,
                    promotion=chess.QUEEN
                )

        if move not in board.legal_moves:

            status_label.config(
                text="Недопустимый ход"
            )

            return

        san = board.san(
            move
        )

        board.push(
            move
        )

        move_history.append(
            san
        )

        selected_square["value"] = None

        refresh_board()

        refresh_move_list()

        if check_game_over():

            return

        update_evaluation()

        game_window.after(
            100,
            computer_move
        )

    # ========================================================
    # ПРИВЯЗКА КЛИКОВ
    # ========================================================

    for square, cell in cells.items():

        cell.bind(
            "<Button-1>",
            lambda event, sq=square:
                player_click(sq)
        )

    # ========================================================
    # НОВАЯ ПАРТИЯ
    # ========================================================

    def new_game():

        nonlocal board

        board = chess.Board()

        selected_square["value"] = None

        move_history.clear()

        game_finished["value"] = False

        refresh_board()

        refresh_move_list()

        evaluation_label.config(
            text="Оценка: —"
        )

        if player_color["value"] == chess.BLACK:

            status_label.config(
                text="Компьютер начинает..."
            )

            game_window.after(
                100,
                computer_move
            )

        else:

            status_label.config(
                text="Ваш ход"
            )

    # ========================================================
    # СДАЧА
    # ========================================================

    def resign():

        if game_finished["value"]:

            return

        answer = messagebox.askyesno(
            "Сдаться",
            "Вы действительно хотите сдаться?"
        )

        if not answer:

            return

        game_finished["value"] = True

        status_label.config(
            text="Вы сдались. Компьютер победил."
        )

        messagebox.showinfo(
            "Партия окончена",
            "Вы сдались.\n\nКомпьютер победил."
        )

    # ========================================================
    # ЗАВЕРШИТЬ ПАРТИЮ
    # ========================================================

    def finish_game():

        if game_finished["value"]:

            return

        answer = messagebox.askyesno(
            "Завершить партию",
            "Завершить текущую партию?"
        )

        if not answer:

            return

        game_finished["value"] = True

        status_label.config(
            text="Партия завершена."
        )

    # ========================================================
    # НАСТРОЙКИ
    # ========================================================

    def open_settings():

        settings_window = tk.Toplevel(
            game_window
        )

        settings_window.title(
            "Настройки партии"
        )

        settings_window.geometry(
            "350x300"
        )

        settings_window.resizable(
            False,
            False
        )

        tk.Label(
            settings_window,
            text="Ваш цвет:",
            font=("Arial", 13, "bold")
        ).pack(
            pady=(20, 5)
        )

        color_var = tk.StringVar()

        if player_color["value"] == chess.WHITE:

            color_var.set(
                "Белые"
            )

        else:

            color_var.set(
                "Чёрные"
            )

        color_menu = tk.OptionMenu(
            settings_window,
            color_var,
            "Белые",
            "Чёрные"
        )

        color_menu.config(
            width=15
        )

        color_menu.pack(
            pady=5
        )

        tk.Label(
            settings_window,
            text="Сила компьютера:",
            font=("Arial", 13, "bold")
        ).pack(
            pady=(15, 5)
        )

        depth_var = tk.IntVar(
            value=engine_depth["value"]
        )

        depth_scale = tk.Scale(
            settings_window,
            from_=5,
            to=18,
            orient="horizontal",
            variable=depth_var,
            length=220
        )

        depth_scale.pack()

        depth_info = tk.Label(
            settings_window,
            text=(
                "Глубина Stockfish: "
                f"{engine_depth['value']}"
            )
        )

        depth_info.pack(
            pady=5
        )

        def update_depth_label(value):

            depth_info.config(
                text=(
                    "Глубина Stockfish: "
                    f"{int(float(value))}"
                )
            )

        depth_scale.config(
            command=update_depth_label
        )

        def apply_settings():

            if color_var.get() == "Белые":

                new_color = chess.WHITE

            else:

                new_color = chess.BLACK

            color_changed = (
                new_color
                != player_color["value"]
            )

            player_color["value"] = new_color

            engine_depth["value"] = (
                depth_var.get()
            )

            settings_window.destroy()

            if color_changed:

                new_game()

            else:

                status_label.config(
                    text=(
                        f"Настройки применены. "
                        f"Глубина: "
                        f"{engine_depth['value']}"
                    )
                )

        tk.Button(
            settings_window,
            text="Применить",
            width=18,
            command=apply_settings
        ).pack(
            pady=15
        )

    # ========================================================
    # КНОПКИ СПРАВА
    # ========================================================

    controls_frame = tk.Frame(
        right_frame
    )

    controls_frame.pack(
        pady=10
    )

    tk.Button(
        controls_frame,
        text="💡 Подсказка",
        width=22,
        command=show_hint
    ).pack(
        pady=3
    )

    tk.Button(
        controls_frame,
        text="↩ Отменить ход",
        width=22,
        command=undo_move
    ).pack(
        pady=3
    )

    tk.Button(
        controls_frame,
        text="📊 Оценка позиции",
        width=22,
        command=update_evaluation
    ).pack(
        pady=3
    )

    tk.Button(
        controls_frame,
        text="⚙ Настройки",
        width=22,
        command=open_settings
    ).pack(
        pady=3
    )

    # ========================================================
    # АНАЛИЗ ПАРТИИ
    # ========================================================

    def analyze_current_game():

        if len(board.move_stack) == 0:

            messagebox.showinfo(
                "Анализ партии",
                "Партия ещё не началась."
            )

            return

        # ----------------------------------------------------
        # Сохраняем ходы
        # ----------------------------------------------------

        game_moves = list(
            board.move_stack
        )

        # ----------------------------------------------------
        # Окно анализа
        # ----------------------------------------------------

        analysis_window = tk.Toplevel(
            game_window
        )

        analysis_window.title(
            "🔍 Анализ партии"
        )

        analysis_window.geometry(
            "760x800"
        )

        analysis_window.resizable(
            False,
            False
        )

        title = tk.Label(
            analysis_window,
            text="🔍 Анализ партии",
            font=("Arial", 20, "bold")
        )

        title.pack(
            pady=15
        )

        info_label = tk.Label(
            analysis_window,
            text="Stockfish анализирует ваши ходы...",
            font=("Arial", 12)
        )

        info_label.pack(
            pady=5
        )

        # ----------------------------------------------------
        # Прокручиваемая область
        # ----------------------------------------------------

        container = tk.Frame(
            analysis_window
        )

        container.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=10
        )

        scrollbar = tk.Scrollbar(
            container
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        results_list = tk.Text(
            container,
            width=78,
            height=32,
            font=("Arial", 11),
            yscrollcommand=scrollbar.set,
            wrap="word"
        )

        results_list.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.config(
            command=results_list.yview
        )

        close_button = tk.Button(
            analysis_window,
            text="Закрыть",
            width=20,
            command=analysis_window.destroy
        )

        close_button.pack(
            pady=10
        )

        analysis_window.update()

        # ====================================================
        # ФУНКЦИЯ ПОКАЗА ПОЗИЦИИ
        # ====================================================

        def show_position(error_data):

            position_board = (
                error_data["board"].copy()
            )

            best_move = error_data["best_move"]

            # ------------------------------------------------
            # ОКНО
            # ------------------------------------------------

            position_window = tk.Toplevel(
                analysis_window
            )

            position_window.title(
                f"Решение ошибки — ход "
                f"{error_data['move_number']}"
            )

            position_window.geometry(
                "700x800"
            )

            position_window.resizable(
                False,
                False
            )

            # ------------------------------------------------
            # СОСТОЯНИЕ ЗАДАЧИ
            # ------------------------------------------------

            selected_position_square = {
                "value": None
            }

            correct_answer_found = {
                "value": False
            }

            hint_shown = {
                "value": False
            }

            # =================================================
            # ЗАГОЛОВОК
            # =================================================

            tk.Label(
                position_window,
                text=(
                    f"Ход {error_data['move_number']}"
                ),
                font=("Arial", 20, "bold")
            ).pack(
                pady=(10, 3)
            )

            tk.Label(
                position_window,
                text=(
                    error_data["category_text"]
                ),
                font=("Arial", 14, "bold")
            ).pack(
                pady=2
            )

            # =================================================
            # ЗАДАНИЕ
            # =================================================

            instruction_label = tk.Label(
                position_window,
                text=(
                    "Найдите лучший ход в этой позиции."
                ),
                font=("Arial", 15, "bold")
            )

            instruction_label.pack(
                pady=5
            )

            # =================================================
            # ДОСКА
            # =================================================

            board_frame_position = tk.Frame(
                position_window
            )

            board_frame_position.pack(
                pady=3
            )

            position_cells = {}

            # =================================================
            # ЦВЕТ КЛЕТОК
            # =================================================

            def get_position_square_color(
                row,
                col
            ):

                if (
                    row + col
                ) % 2 == 0:

                    return "#F0D9B5"

                return "#B58863"

            # =================================================
            # ОБНОВЛЕНИЕ ДОСКИ
            # =================================================

            def refresh_position_board():

                for square, cell in position_cells.items():

                    piece = position_board.piece_at(
                        square
                    )

                    if piece:

                        cell.config(
                            text=SYMBOLS[
                                piece.symbol()
                            ]
                        )

                    else:

                        cell.config(
                            text=""
                        )

                    row = (
                        7
                        - chess.square_rank(
                            square
                        )
                    )

                    col = chess.square_file(
                        square
                    )

                    # -----------------------------------------
                    # Обычный цвет
                    # -----------------------------------------

                    cell.config(
                        bg=get_position_square_color(
                            row,
                            col
                        )
                    )

                # =================================================
                # ПОДСВЕТКА ЛУЧШЕГО ХОДА
                # =================================================

                if hint_shown["value"]:

                    position_cells[
                        best_move.from_square
                    ].config(
                        bg="#FFF176"
                    )

                    position_cells[
                        best_move.to_square
                    ].config(
                        bg="#81C784"
                    )

                # =================================================
                # ПОДСВЕТКА ВЫБРАННОЙ ФИГУРЫ
                # =================================================

                selected = (
                    selected_position_square["value"]
                )

                if (
                    selected is not None
                    and not correct_answer_found["value"]
                ):

                    position_cells[
                        selected
                    ].config(
                        bg="#FFD54F"
                    )

            # =================================================
            # ПОКАЗАТЬ ЛУЧШИЙ ХОД
            # =================================================

            def show_best_move():

                if correct_answer_found["value"]:

                    return

                hint_shown["value"] = True

                instruction_label.config(
                    text=(
                        "💡 Лучший ход подсвечен: "
                        "жёлтая клетка → зелёная клетка"
                    ),
                    font=("Arial", 14, "bold"),
                    fg="#B8860B"
                )

                refresh_position_board()

            # =================================================
            # ПРАВИЛЬНЫЙ ХОД
            # =================================================

            def correct_move():

                if correct_answer_found["value"]:

                    return

                correct_answer_found["value"] = True

                selected_position_square["value"] = None

                # ---------------------------------------------
                # Делаем лучший ход на доске
                # ---------------------------------------------

                position_board.push(
                    best_move
                )

                # ---------------------------------------------
                # Подсветку убираем
                # ---------------------------------------------

                hint_shown["value"] = False

                # ---------------------------------------------
                # Сообщение
                # ---------------------------------------------

                instruction_label.config(
                    text="✅ Правильно!",
                    font=("Arial", 17, "bold"),
                    fg="green"
                )

                refresh_position_board()

                # ---------------------------------------------
                # Показываем результат только после решения
                # ---------------------------------------------

                result_label.config(
                    text=(
                        f"Лучший ход: "
                        f"{error_data['best_san']}"
                    ),
                    font=("Arial", 13, "bold"),
                    fg="green"
                )

                # ---------------------------------------------
                # Отключаем кнопку подсказки
                # ---------------------------------------------

                show_best_button.config(
                    state="disabled"
                )

            # =================================================
            # ОБРАБОТКА КЛИКА ПО ДОСКЕ
            # =================================================

            def position_board_click(square):

                # ------------------------------------------------
                # После правильного ответа ходить больше нельзя
                # ------------------------------------------------

                if correct_answer_found["value"]:

                    return

                selected = (
                    selected_position_square["value"]
                )

                # =================================================
                # ВЫБОР ПЕРВОЙ КЛЕТКИ
                # =================================================

                if selected is None:

                    piece = (
                        position_board.piece_at(
                            square
                        )
                    )

                    if piece is None:

                        return

                    # Можно двигать только сторону,
                    # которой принадлежит ход

                    if (
                        piece.color
                        != position_board.turn
                    ):

                        return

                    selected_position_square[
                        "value"
                    ] = square

                    refresh_position_board()

                    return

                # =================================================
                # КЛИК ПО ТОЙ ЖЕ КЛЕТКЕ
                # =================================================

                if selected == square:

                    selected_position_square[
                        "value"
                    ] = None

                    refresh_position_board()

                    return

                # =================================================
                # ВЫБОР ДРУГОЙ СВОЕЙ ФИГУРЫ
                # =================================================

                piece = (
                    position_board.piece_at(
                        square
                    )
                )

                if (
                    piece is not None
                    and piece.color
                    == position_board.turn
                ):

                    selected_position_square[
                        "value"
                    ] = square

                    refresh_position_board()

                    return

                # =================================================
                # СОЗДАЁМ ХОД
                # =================================================

                move = chess.Move(
                    selected,
                    square
                )

                # =================================================
                # ПРОМОУШЕН
                # =================================================

                piece_from = (
                    position_board.piece_at(
                        selected
                    )
                )

                if (
                    piece_from is not None
                    and piece_from.piece_type
                    == chess.PAWN
                ):

                    to_rank = chess.square_rank(
                        square
                    )

                    if (
                        piece_from.color
                        == chess.WHITE
                        and to_rank == 7
                    ):

                        move = chess.Move(
                            selected,
                            square,
                            promotion=chess.QUEEN
                        )

                    elif (
                        piece_from.color
                        == chess.BLACK
                        and to_rank == 0
                    ):

                        move = chess.Move(
                            selected,
                            square,
                            promotion=chess.QUEEN
                        )

                # =================================================
                # ПРОВЕРКА ЛЕГАЛЬНОСТИ
                # =================================================

                if move not in position_board.legal_moves:

                    instruction_label.config(
                        text=(
                            "❌ Такой ход невозможен."
                        ),
                        font=("Arial", 14, "bold"),
                        fg="red"
                    )

                    selected_position_square[
                        "value"
                    ] = None

                    refresh_position_board()

                    return

                # =================================================
                # ПРОВЕРКА ЛУЧШЕГО ХОДА
                # =================================================

                if move == best_move:

                    correct_move()

                    return

                # =================================================
                # НЕПРАВИЛЬНЫЙ ХОД
                # =================================================

                instruction_label.config(
                    text=(
                        "❌ Не совсем. "
                        "Попробуйте ещё раз."
                    ),
                    font=("Arial", 14, "bold"),
                    fg="red"
                )

                selected_position_square[
                    "value"
                ] = None

                refresh_position_board()

            # =================================================
            # СОЗДАНИЕ КЛЕТОК ДОСКИ
            # =================================================

            for row in range(8):

                for col in range(8):

                    square = chess.square(
                        col,
                        7 - row
                    )

                    piece = (
                        position_board.piece_at(
                            square
                        )
                    )

                    text = ""

                    if piece:

                        text = SYMBOLS[
                            piece.symbol()
                        ]

                    cell = tk.Label(
                        board_frame_position,
                        text=text,
                        width=4,
                        height=2,
                        font=("Arial", 24),
                        bg=get_position_square_color(
                            row,
                            col
                        ),
                        relief="solid",
                        borderwidth=1
                    )

                    cell.grid(
                        row=row,
                        column=col
                    )

                    cell.bind(
                        "<Button-1>",
                        lambda event, sq=square:
                            position_board_click(sq)
                    )

                    position_cells[
                        square
                    ] = cell

            # =================================================
            # РЕЗУЛЬТАТ
            # =================================================

            result_label = tk.Label(
                position_window,
                text="",
                font=("Arial", 12)
            )

            result_label.pack(
                pady=3
            )

            # =================================================
            # КНОПКИ
            # =================================================

            buttons_position_frame = tk.Frame(
                position_window
            )

            buttons_position_frame.pack(
                pady=5
            )

            show_best_button = tk.Button(
                buttons_position_frame,
                text="💡 Показать лучший ход",
                width=25,
                font=("Arial", 11, "bold"),
                command=show_best_move
            )

            show_best_button.grid(
                row=0,
                column=0,
                padx=5
            )

            tk.Button(
                buttons_position_frame,
                text="Закрыть",
                width=18,
                font=("Arial", 11),
                command=position_window.destroy
            ).grid(
                row=0,
                column=1,
                padx=5
            )

            # =================================================
            # ПЕРВОНАЧАЛЬНОЕ ОБНОВЛЕНИЕ
            # =================================================

            refresh_position_board()

        # ====================================================
        # ЗАПУСК STOCKFISH ДЛЯ АНАЛИЗА
        # ====================================================

        analysis_engine = None

        try:

            analysis_engine = (
                chess.engine.SimpleEngine.popen_uci(
                    ENGINE_PATH
                )
            )

            analysis_board = chess.Board()

            user_move_number = 0

            total_user_moves = 0

            good_moves = 0

            inaccuracies = 0

            mistakes = 0

            blunders = 0

            total_loss_cp = 0

            # =================================================
            # ПРОХОДИМ ПО ВСЕЙ ПАРТИИ
            # =================================================

            for move in game_moves:

                current_side = (
                    analysis_board.turn
                )

                # =================================================
                # ХОД ПОЛЬЗОВАТЕЛЯ
                # =================================================

                if (
                    current_side
                    == player_color["value"]
                ):

                    total_user_moves += 1

                    user_move_number += 1

                    # -------------------------------------------------
                    # Позиция ДО хода
                    # -------------------------------------------------

                    position_before = (
                        analysis_board.copy()
                    )

                    # -------------------------------------------------
                    # SAN сыгранного хода
                    # -------------------------------------------------

                    played_san = (
                        analysis_board.san(
                            move
                        )
                    )

                    # -------------------------------------------------
                    # Анализ позиции ДО хода
                    # -------------------------------------------------

                    before_info = (
                        analysis_engine.analyse(
                            analysis_board,
                            chess.engine.Limit(
                                depth=engine_depth["value"]
                            )
                        )
                    )

                    pv = before_info.get(
                        "pv",
                        []
                    )

                    if not pv:

                        analysis_board.push(
                            move
                        )

                        continue

                    # -------------------------------------------------
                    # Лучший ход
                    # -------------------------------------------------

                    best_move = pv[0]

                    best_san = (
                        analysis_board.san(
                            best_move
                        )
                    )

                    # =================================================
                    # ПОЗИЦИЯ ПОСЛЕ ЛУЧШЕГО ХОДА
                    # =================================================

                    best_board = (
                        analysis_board.copy()
                    )

                    best_board.push(
                        best_move
                    )

                    best_info = (
                        analysis_engine.analyse(
                            best_board,
                            chess.engine.Limit(
                                depth=engine_depth["value"]
                            )
                        )
                    )

                    best_score = (
                        best_info["score"].pov(
                            player_color["value"]
                        )
                    )

                    # =================================================
                    # ПОЗИЦИЯ ПОСЛЕ РЕАЛЬНОГО ХОДА
                    # =================================================

                    played_board = (
                        analysis_board.copy()
                    )

                    played_board.push(
                        move
                    )

                    played_info = (
                        analysis_engine.analyse(
                            played_board,
                            chess.engine.Limit(
                                depth=engine_depth["value"]
                            )
                        )
                    )

                    played_score = (
                        played_info["score"].pov(
                            player_color["value"]
                        )
                    )

                    # =================================================
                    # CP
                    # =================================================

                    best_cp = score_to_cp(
                        best_score
                    )

                    played_cp = score_to_cp(
                        played_score
                    )

                    # =================================================
                    # ПОТЕРЯ
                    # =================================================

                    if (
                        best_cp is None
                        or played_cp is None
                    ):

                        loss_cp = 0

                    else:

                        loss_cp = (
                            best_cp
                            - played_cp
                        )

                        if loss_cp < 0:

                            loss_cp = 0

                    total_loss_cp += loss_cp

                    loss = (
                        loss_cp / 100
                    )

                    # =================================================
                    # КАТЕГОРИЯ
                    # =================================================

                    if loss_cp < 50:

                        category = (
                            "good"
                        )

                        category_text = (
                            "✅ Хороший ход"
                        )

                        good_moves += 1

                    elif loss_cp < 100:

                        category = (
                            "inaccuracy"
                        )

                        category_text = (
                            "🟡 Неточность"
                        )

                        inaccuracies += 1

                    elif loss_cp < 300:

                        category = (
                            "mistake"
                        )

                        category_text = (
                            "🟠 Ошибка"
                        )

                        mistakes += 1

                    else:

                        category = (
                            "blunder"
                        )

                        category_text = (
                            "🔴 Грубая ошибка"
                        )

                        blunders += 1

                    # =================================================
                    # ВЫВОДИМ ТОЛЬКО ОШИБКИ
                    # =================================================

                    if category != "good":

                        error_data = {
                            "move_number":
                                user_move_number,

                            "played_san":
                                played_san,

                            "best_san":
                                best_san,

                            "best_move":
                                best_move,

                            "best_score":
                                best_score,

                            "played_score":
                                played_score,

                            "loss":
                                loss,

                            "category":
                                category,

                            "category_text":
                                category_text,

                            "board":
                                position_before
                        }

                        results_list.insert(
                            tk.END,
                            (
                                f"{category_text}\n"
                                f"Ход "
                                f"{user_move_number}\n"
                                f"Сыграно: "
                                f"{played_san}\n"
                                f"Лучше: "
                                f"{best_san}\n"
                                f"Оценка лучшего: "
                                f"{format_score(best_score)}\n"
                                f"Оценка сыгранного: "
                                f"{format_score(played_score)}\n"
                                f"Потеря: "
                                f"{loss:.2f}\n"
                            )
                        )

                        # -------------------------------------------------
                        # КНОПКА ПОКАЗА ПОЗИЦИИ
                        # -------------------------------------------------

                        show_button = tk.Button(
                            results_list,
                            text="♟ Показать позицию",
                            font=("Arial", 10),
                            command=lambda data=error_data:
                                show_position(data)
                        )

                        results_list.window_create(
                            tk.END,
                            window=show_button,
                            padx=5,
                            pady=5
                        )

                        results_list.insert(
                            tk.END,
                            "\n\n"
                        )

                        results_list.see(
                            tk.END
                        )

                        analysis_window.update()

                # =================================================
                # ДЕЛАЕМ ХОД
                # =================================================

                analysis_board.push(
                    move
                )

            # ========================================================
            # ЕСЛИ ОШИБОК НЕТ
            # ========================================================

            if (
                inaccuracies == 0
                and mistakes == 0
                and blunders == 0
            ):

                results_list.insert(
                    tk.END,
                    (
                        "🎉 Отлично!\n\n"
                        "В партии не найдено "
                        "неточностей, ошибок "
                        "или грубых ошибок."
                    )
                )

            # ========================================================
            # ИТОГ
            # ========================================================

            if total_user_moves == 0:

                summary = (
                    "Ваших ходов для анализа нет."
                )

            else:

                average_loss = (
                    total_loss_cp
                    / total_user_moves
                    / 100
                )

                summary = (
                    f"Ваших ходов: "
                    f"{total_user_moves}    "
                    f"Хороших: "
                    f"{good_moves}    "
                    f"Неточностей: "
                    f"{inaccuracies}    "
                    f"Ошибок: "
                    f"{mistakes}    "
                    f"Грубых ошибок: "
                    f"{blunders}\n"
                    f"Средняя потеря: "
                    f"{average_loss:.2f}"
                )

            info_label.config(
                text=summary
            )

        except Exception as e:

            messagebox.showerror(
                "Ошибка анализа",
                str(e)
            )

            try:

                analysis_window.destroy()

            except Exception:

                pass

        finally:

            if analysis_engine is not None:

                try:

                    analysis_engine.quit()

                except Exception:

                    pass

    # ========================================================
    # НИЖНИЕ КНОПКИ
    # ========================================================

    buttons_frame = tk.Frame(
        game_window
    )

    buttons_frame.pack(
        pady=10
    )

    tk.Button(
        buttons_frame,
        text="🔄 Новая партия",
        width=20,
        command=new_game
    ).grid(
        row=0,
        column=0,
        padx=5
    )

    tk.Button(
        buttons_frame,
        text="🏳 Сдаться",
        width=20,
        command=resign
    ).grid(
        row=0,
        column=1,
        padx=5
    )

    tk.Button(
        buttons_frame,
        text="🏁 Завершить",
        width=20,
        command=finish_game
    ).grid(
        row=0,
        column=2,
        padx=5
    )

    tk.Button(
        buttons_frame,
        text="🔍 Анализ партии",
        width=20,
        command=analyze_current_game
    ).grid(
        row=1,
        column=0,
        columnspan=3,
        pady=8
    )

    # ========================================================
    # НАЗАД
    # ========================================================

    back_button = tk.Button(
        game_window,
        text="Назад",
        width=20,
        command=game_window.destroy
    )

    back_button.pack(
        pady=5
    )

    # ========================================================
    # КОРРЕКТНОЕ ЗАКРЫТИЕ STOCKFISH
    # ========================================================

    def close_window():

        try:

            engine.quit()

        except Exception:

            pass

        game_window.destroy()

    game_window.protocol(
        "WM_DELETE_WINDOW",
        close_window
    )

    # ========================================================
    # ПЕРВОНАЧАЛЬНОЕ ОБНОВЛЕНИЕ
    # ========================================================

    refresh_board()

    game_window.focus_set()