
import tkinter as tk
import chess

from app.mistake_storage import postpone_mistake, delete_mistake


def show_position(
    fen,
    best_move=None,
    on_success=None,
    on_next=None,
    on_previous=None,
    user_side=None,
    move_text=None,
    played_san=None,
    explanation=None,
    theme=None,
    captured_piece=None,
    hanging_piece=None,
    hanging_square=None,
    fork_targets=None,
    pin_piece=None,
    pin_square=None,
    existing_window=None,
    mistake=None
):
    print("=== SHOW_POSITION ===")
    print("existing_window =", existing_window)
    print("existing_window id =", id(existing_window))

    print("=== SHOW_POSITION ИЗ position_view.py ===")
    print("on_next =", on_next)
    print("on_previous =", on_previous)
    print("user_side =", user_side)
    print("id(show_position) =", id(show_position))

    board = chess.Board(fen)

    if fork_targets is None:
        fork_targets = []

    highlight_fork_targets = {"value": False}
    highlight_hanging_piece = {"value": False}
    highlight_pin_piece = {"value": False}

    # ==========================================================
    # ОПРЕДЕЛЕНИЕ ТЕКСТА ХОДА
    # ==========================================================

    if user_side is None:

        if board.turn == chess.WHITE:
            turn_text = "⚪ Ход белых"
            turn_color = "#1f4e79"
        else:
            turn_text = "⚫ Ход чёрных"
            turn_color = "#1f1f1f"

    else:

        user_is_white = (user_side == "white")

        if user_is_white:

            if board.turn == chess.WHITE:
                turn_text = "⚪ Ваш ход (белые)"
                turn_color = "#0b7d0b"
            else:
                turn_text = "⚫ Ход соперника (чёрные)"
                turn_color = "#b00020"

        else:

            if board.turn == chess.BLACK:
                turn_text = "⚫ Ваш ход (чёрные)"
                turn_color = "#0b7d0b"
            else:
                turn_text = "⚪ Ход соперника (белые)"
                turn_color = "#b00020"

    attempts = {"count": 0}

    last_move = None

    from_square = None
    to_square = None

    if best_move is not None:

        move = chess.Move.from_uci(best_move)

        from_square = move.from_square
        to_square = move.to_square

        print("=== PIN DATA IN SHOW_POSITION ===")
        print("pin_piece =", pin_piece)
        print("pin_square =", pin_square)
        print("theme =", theme)
        print("=================================")

    # ==========================================================
    # СОЗДАНИЕ / ПЕРЕИСПОЛЬЗОВАНИЕ ОКНА
    # ==========================================================

    if existing_window is None:

        window = tk.Toplevel()
        window.title("Позиция")
        window.geometry("600x850")

    else:

        window = existing_window

        if window.winfo_exists():

            for widget in window.winfo_children():
                widget.destroy()

        else:

            window = tk.Toplevel()
            window.title("Позиция")
            window.geometry("600x850")

    # ==========================================================
    # ИНДИКАТОР ХОДА
    # ==========================================================

    turn_label = tk.Label(
        window,
        text=turn_text,
        font=("Arial", 15, "bold"),
        fg=turn_color
    )

    turn_label.pack(pady=(8, 5))

    # ==========================================================
    # БЛОК ИНФОРМАЦИИ ОБ ОШИБКЕ
    # ==========================================================

    if move_text is not None and played_san is not None:

        info_frame = tk.Frame(window)
        info_frame.pack()

        tk.Label(
            info_frame,
            text="🎯 Ошибка на ходе",
            font=("Arial", 13, "bold")
        ).pack(side="left")

        tooltip = None

        def show_tooltip(event):

            print("EXPLANATION =", explanation)
            print(type(explanation))

            nonlocal tooltip

            if tooltip is not None:
                return

            tooltip = tk.Toplevel(window)
            tooltip.wm_overrideredirect(True)

            x = event.x_root + 15
            y = event.y_root + 15

            tooltip.geometry(f"+{x}+{y}")

            tk.Label(
                tooltip,
                text=explanation,
                justify="left",
                bg="#ffffdd",
                relief="solid",
                borderwidth=1,
                padx=8,
                pady=6,
                wraplength=360,
                font=("Arial", 11)
            ).pack()

        def hide_tooltip(event):

            nonlocal tooltip

            if tooltip is not None:
                tooltip.destroy()
                tooltip = None

        info_icon = tk.Label(
            info_frame,
            text=" 💡",
            fg="orange",
            cursor="hand2",
            font=("Arial", 13, "bold")
        )

        info_icon.pack(side="left")

        info_icon.bind("<Enter>", show_tooltip)
        info_icon.bind("<Leave>", hide_tooltip)

        tk.Label(
            window,
            text=f"{move_text} {played_san}",
            font=("Arial", 14)
        ).pack(pady=(2, 8))

    # ==========================================================
    # СЕТКА ДОСКИ
    # ==========================================================

    show_answer = {"value": False}

    canvas = tk.Canvas(
        window,
        width=520,
        height=520
    )

    canvas.pack(pady=10)

    # ==========================================================
    # ПЕРЕМЕННЫЕ ДОСКИ
    # ==========================================================

    selected_square = {"value": None}

    size = 60

    colors = [
        "#f0d9b5",
        "#b58863"
    ]

    pieces = {
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

    # ==========================================================
    # ОТРИСОВКА ДОСКИ
    # ==========================================================

    def draw_board():

        canvas.delete("all")

        for rank in range(8):

            for file in range(8):

                x1 = file * size + 20
                y1 = rank * size + 20
                x2 = x1 + size
                y2 = y1 + size

                color = colors[(rank + file) % 2]

                # --------------------------------------------------
                # ПЕРЕВОРОТ ДОСКИ ДЛЯ ЧЁРНЫХ
                # --------------------------------------------------

                if user_side == "black":

                    square = chess.square(
                        7 - file,
                        rank
                    )

                else:

                    square = chess.square(
                        file,
                        7 - rank
                    )

                # --------------------------------------------------
                # ПОСЛЕДНИЙ ХОД
                # --------------------------------------------------

                last_move_square = False

                if last_move is not None:

                    if square == last_move.from_square:
                        last_move_square = True

                    if square == last_move.to_square:
                        last_move_square = True

                # --------------------------------------------------
                # ВОЗМОЖНЫЙ ХОД
                # --------------------------------------------------

                possible_move = False

                if selected_square["value"] is not None:

                    move = chess.Move(
                        selected_square["value"],
                        square
                    )

                    if move in board.legal_moves:
                        possible_move = True

                # --------------------------------------------------
                # ВЫДЕЛЕНИЕ ПОЛЯ
                # --------------------------------------------------

                outline = ""
                width = 1

                if selected_square["value"] == square:

                    outline = "blue"
                    width = 4

                # --------------------------------------------------
                # ПРАВИЛЬНЫЙ ОТВЕТ
                # --------------------------------------------------

                if show_answer["value"]:

                    if square == from_square:

                        outline = "green"
                        width = 4

                    if square == to_square:

                        outline = "green"
                        width = 4

                # --------------------------------------------------
                # ВИЛКА
                # --------------------------------------------------

                if highlight_fork_targets["value"]:

                    for target in fork_targets:

                        target_square = chess.parse_square(
                            target["square"]
                        )

                        if square == target_square:

                            outline = "orange"
                            width = 4

                # --------------------------------------------------
                # ВИСЯЩАЯ ФИГУРА
                # --------------------------------------------------

                if highlight_hanging_piece["value"]:

                    if hanging_square is not None:

                        target_square = chess.parse_square(
                            hanging_square
                        )

                        if square == target_square:

                            outline = "red"
                            width = 4

                # --------------------------------------------------
                # СВЯЗКА
                # --------------------------------------------------

                if highlight_pin_piece["value"]:

                    if pin_square is not None:

                        target_square = chess.parse_square(
                            pin_square
                        )

                        if square == target_square:

                            outline = "purple"
                            width = 4

                # --------------------------------------------------
                # ПОСЛЕДНИЙ ХОД
                # --------------------------------------------------

                if last_move_square:

                    color = "#f7ec6e"

                # --------------------------------------------------
                # КВАДРАТ
                # --------------------------------------------------

                canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline=outline,
                    width=width
                )

                # --------------------------------------------------
                # ТОЧКА ВОЗМОЖНОГО ХОДА
                # --------------------------------------------------

                if possible_move:

                    radius = 8

                    canvas.create_oval(
                        x1 + size / 2 - radius,
                        y1 + size / 2 - radius,
                        x1 + size / 2 + radius,
                        y1 + size / 2 + radius,
                        fill="#00cc66",
                        outline=""
                    )

                # --------------------------------------------------
                # ФИГУРА
                # --------------------------------------------------

                piece = board.piece_at(square)

                if piece:

                    canvas.create_text(
                        x1 + size / 2,
                        y1 + size / 2,
                        text=pieces[piece.symbol()],
                        font=("Arial", 34)
                    )

        # ==========================================================
        # КООРДИНАТЫ
        # ==========================================================

        if user_side == "black":

            letters = "hgfedcba"
            ranks = "12345678"

        else:

            letters = "abcdefgh"
            ranks = "87654321"

        for i in range(8):

            canvas.create_text(
                20 + i * size + size / 2,
                505,
                text=letters[i],
                font=("Arial", 10, "bold")
            )

            canvas.create_text(
                10,
                20 + i * size + size / 2,
                text=ranks[i],
                font=("Arial", 10, "bold")
            )

    # ==========================================================
    # ПОКАЗАТЬ ОТВЕТ
    # ==========================================================

    def show_answer_click():

        show_answer["value"] = True

        answer_button.config(
            state="disabled"
        )

        draw_board()

    answer_button = tk.Button(
        window,
        text="👁 Показать ответ",
        font=("Arial", 12),
        command=show_answer_click
    )

    answer_button.pack(
        pady=(5, 2)
    )

    # ==========================================================
    # РЕЗУЛЬТАТ
    # ==========================================================

    result_label = tk.Label(
        window,
        text="",
        font=("Arial", 14, "bold")
    )

    result_label.pack()

    # ==========================================================
    # НАВИГАЦИЯ ПО ОШИБКАМ
    # ==========================================================

    navigation_frame = tk.Frame(window)

    navigation_frame.pack(
        pady=(5, 5)
    )

    # ----------------------------------------------------------
    # ПРЕДЫДУЩАЯ ОШИБКА
    # ----------------------------------------------------------

    previous_button = tk.Button(
        navigation_frame,
        text="⬅ Предыдущая ошибка",
        font=("Arial", 12)
    )

    previous_button.pack(
        side="left",
        padx=5
    )

    if on_previous is not None:

        def previous_click():

            print("PREVIOUS_CLICK")
            print("on_previous =", on_previous)

            on_previous()

        previous_button.config(
            command=previous_click
        )

    else:

        previous_button.config(
            state="disabled"
        )

    # ----------------------------------------------------------
    # СЛЕДУЮЩАЯ ОШИБКА
    # ----------------------------------------------------------

    next_button = tk.Button(
        navigation_frame,
        text="Следующая ошибка ➡",
        font=("Arial", 12)
    )

    next_button.pack(
        side="left",
        padx=5
    )

    if on_next is not None:

        def next_click():

            print("NEXT_CLICK")
            print("on_next =", on_next)

            on_next()

        next_button.config(
            command=next_click
        )

    else:

        next_button.config(
            state="disabled"
        )

    # ==========================================================
    # КНОПКИ УПРАВЛЕНИЯ ОШИБКОЙ
    # ==========================================================

    postpone_frame = tk.Frame(window)

    postpone_frame.pack(
        pady=5
    )

    # ----------------------------------------------------------
    # ОТЛОЖИТЬ НА 1 ДЕНЬ
    # ----------------------------------------------------------

    def postpone_one_day():

        if mistake is not None:

            print("Откладываем ошибку на 1 день")

            postpone_mistake(
                mistake,
                1
            )

        if on_next is not None:

            on_next()

    # ----------------------------------------------------------
    # ОТЛОЖИТЬ НА 2 ДНЯ
    # ----------------------------------------------------------

    def postpone_two_days():

        if mistake is not None:

            print("Откладываем ошибку на 2 дня")

            postpone_mistake(
                mistake,
                2
            )

        if on_next is not None:

            on_next()

    # ----------------------------------------------------------
    # УДАЛИТЬ
    # ----------------------------------------------------------

    def delete_current_mistake():

        if mistake is not None:

            print("Удаляем ошибку")

            delete_mistake(
                mistake
            )

        if on_next is not None:

            on_next()

    # ----------------------------------------------------------
    # КНОПКА 1 ДЕНЬ
    # ----------------------------------------------------------

    postpone_one_button = tk.Button(
        postpone_frame,
        text="⏭️ Не показывать 1 день",
        font=("Arial", 11),
        command=postpone_one_day
    )

    postpone_one_button.pack(
        side="left",
        padx=5
    )

    # ----------------------------------------------------------
    # КНОПКА 2 ДНЯ
    # ----------------------------------------------------------

    postpone_two_button = tk.Button(
        postpone_frame,
        text="⏭️ Не показывать 2 дня",
        font=("Arial", 11),
        command=postpone_two_days
    )

    postpone_two_button.pack(
        side="left",
        padx=5
    )

    # ----------------------------------------------------------
    # УДАЛИТЬ ОШИБКУ
    # ----------------------------------------------------------

    delete_button = tk.Button(
        postpone_frame,
        text="🗑️ Удалить ошибку",
        font=("Arial", 11),
        command=delete_current_mistake
    )

    delete_button.pack(
        side="left",
        padx=5
    )

    # ==========================================================
    # МИНИМАЛЬНЫЙ РАЗМЕР ОКНА
    # ==========================================================

    window.minsize(
        600,
        850
    )

    # ==========================================================
    # ОБРАБОТКА КЛИКА ПО ДОСКЕ
    # ==========================================================

    def on_click(event):

        display_file = event.x // size
        display_rank = event.y // size

        # ------------------------------------------------------
        # ПРЕОБРАЗОВАНИЕ КООРДИНАТ ДЛЯ ЧЁРНЫХ
        # ------------------------------------------------------

        if user_side == "black":

            file = 7 - display_file
            rank = display_rank

        else:

            file = display_file
            rank = 7 - display_rank

        # ------------------------------------------------------
        # ЗАЩИТА ОТ КЛИКА ВНЕ ДОСКИ
        # ------------------------------------------------------

        if not (
            0 <= file <= 7
            and
            0 <= rank <= 7
        ):

            return

        square = chess.square(
            file,
            rank
        )

        # ------------------------------------------------------
        # ВЫБОР ПЕРВОЙ КЛЕТКИ
        # ------------------------------------------------------

        if selected_square["value"] is None:

            selected_square["value"] = square

            draw_board()

            print(
                "Выбрана:",
                chess.square_name(square)
            )

            return

        # ------------------------------------------------------
        # ФОРМИРУЕМ ХОД
        # ------------------------------------------------------

        move = chess.Move(
            selected_square["value"],
            square
        )

        # ======================================================
        # ПРАВИЛЬНЫЙ ХОД
        # ======================================================

        if (
            best_move is not None
            and
            move == chess.Move.from_uci(best_move)
        ):

            board.push(move)

            last_move = move

            draw_board()

            answer_button.config(
                state="disabled"
            )

            if attempts["count"] == 0:

                text = (
                    "✅ Правильно с первой попытки!"
                )

            else:

                text = (
                    f"✅ Правильно! Ошибок перед этим: "
                    f"{attempts['count']}"
                )

            result_label.config(
                text=text,
                fg="green"
            )

            next_button.config(
                state="normal"
            )

            print(
                ">>> on_success =",
                on_success
            )

            if on_success is not None:

                print(
                    ">>> Вызываю on_success"
                )

                on_success(
                    attempts["count"]
                )

        # ======================================================
        # НЕПРАВИЛЬНЫЙ ХОД
        # ======================================================

        else:

            attempts["count"] += 1

            # --------------------------------------------------
            # ВИЛКА
            # --------------------------------------------------

            if (
                attempts["count"] >= 3
                and
                theme == "Вилка"
            ):

                highlight_fork_targets["value"] = True

            # --------------------------------------------------
            # ВИСЯЩАЯ ФИГУРА
            # --------------------------------------------------

            print(
                "HANGING HIGHLIGHT:",
                "attempts =",
                attempts["count"],
                "theme =",
                theme,
                "hanging_piece =",
                hanging_piece,
                "hanging_square =",
                hanging_square,
                "highlight =",
                highlight_hanging_piece["value"]
            )

            if (
                attempts["count"] >= 3
                and
                theme == "Висящая фигура"
            ):

                highlight_hanging_piece["value"] = True

            # --------------------------------------------------
            # СВЯЗКА
            # --------------------------------------------------

            if (
                attempts["count"] >= 3
                and
                theme == "Связка"
            ):

                highlight_pin_piece["value"] = True

            print(
                "PIN TEST:",
                pin_piece,
                pin_square,
                highlight_pin_piece["value"]
            )

            # ==================================================
            # ПЕРВАЯ ПОПЫТКА
            # ==================================================

            if attempts["count"] == 1:

                text = (
                    "❌ Неправильно.\n\n"
                    "Попробуй ещё раз."
                )

            # ==================================================
            # ВТОРАЯ ПОПЫТКА
            # ==================================================

            elif attempts["count"] == 2:

                # ----------------------------------------------
                # ВИЛКА
                # ----------------------------------------------

                if theme == "Вилка":

                    targets_text = ""

                    if fork_targets:

                        names = [
                            target["piece"]
                            for target in fork_targets
                        ]

                        if len(names) >= 2:

                            targets_text = (
                                "\nПопробуй найти ход, "
                                "который одновременно "
                                f"атакует {names[0]} и "
                                f"{names[1]}."
                            )

                    text = (
                        "💡 Подсказка:\n\n"
                        "Ищи ход, который атакует "
                        "две фигуры одновременно."
                        + targets_text
                    )

                # ----------------------------------------------
                # ВИСЯЩАЯ ФИГУРА
                # ----------------------------------------------

                elif theme == "Висящая фигура":

                    text = (
                        "💡 Подсказка:\n\n"
                        f"Обрати внимание на "
                        f"{hanging_piece} "
                        f"на поле {hanging_square}."
                    )

                # ----------------------------------------------
                # СВЯЗКА
                # ----------------------------------------------

                elif theme == "Связка":

                    text = (
                        "💡 Подсказка:\n\n"
                        "Проверь фигуру, которая "
                        "связана с более важной фигурой."
                    )

                # ----------------------------------------------
                # ПОТЕРЯ ФИГУРЫ
                # ----------------------------------------------

                elif theme == "Потеря фигуры":

                    text = (
                        "💡 Подсказка:\n\n"
                        "Проверь, не отдаёшь ли ты "
                        "фигуру без достаточной компенсации."
                    )

                # ----------------------------------------------
                # ОБЩАЯ ПОДСКАЗКА
                # ----------------------------------------------

                else:

                    text = (
                        "💡 Подсказка:\n\n"
                        "Посмотри на угрозы соперника "
                        "и незащищённые фигуры."
                    )

            # ==================================================
            # ТРЕТЬЯ И ПОСЛЕДУЮЩИЕ ПОПЫТКИ
            # ==================================================

            else:

                if (
                    theme == "Висящая фигура"
                    and
                    hanging_piece
                ):

                    text = (
                        "💡 Смотри на фигуру, которая "
                        f"сейчас стоит на поле "
                        f"{hanging_square}.\n\n"
                        f"Это {hanging_piece}, "
                        "и она не защищена."
                    )

                elif captured_piece:

                    text = (
                        "💡 Лучший ход связан "
                        "с выигрышем "
                        f"{captured_piece}."
                    )

                else:

                    text = (
                        "💡 Попробуй ещё раз.\n\n"
                        "Если не получается, "
                        "используй кнопку "
                        "«Показать ответ»."
                    )

            # --------------------------------------------------
            # ПОКАЗЫВАЕМ ТЕКСТ
            # --------------------------------------------------

            result_label.config(
                text=text,
                fg="red"
            )

            selected_square["value"] = None

            draw_board()

            return

        # ======================================================
        # СБРОС ВЫБРАННОЙ КЛЕТКИ
        # ======================================================

        selected_square["value"] = None

        draw_board()

    # ==========================================================
    # ПЕРВОНАЧАЛЬНАЯ ОТРИСОВКА
    # ==========================================================

    draw_board()

    canvas.bind(
        "<Button-1>",
        on_click
    )

    return window

