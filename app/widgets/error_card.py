import tkinter as tk
from app.app.position_view import show_position

print("Загружен НОВЫЙ error_card.py")


def create_error_card(parent, mistake):

    print("Карточка создаётся")
    print(mistake)

    print("Показываем:", mistake["move"])

    frame = tk.Frame(parent)

    frame.pack(fill="x", padx=10, pady=5)

    # ==========================================================
    # ЦВЕТ ОШИБКИ
    # ==========================================================

    if "Неточность" in mistake["type"]:
        color = "#d4a017"

    elif "Ошибка" in mistake["type"]:
        color = "#ff8800"

    else:
        color = "#cc0000"

    # ==========================================================
    # ТЕКСТ КАРТОЧКИ
    # ==========================================================

    text = (
        f"{mistake['type']}\n"
        f"Ход {mistake['move']}\n"
        f"Сыграно: {mistake['played_san']}\n"
        f"До хода: {mistake['before_score']}\n"
        f"После хода: {mistake['after_score']}\n"
        f"Потеря: {mistake['loss']} cp\n"
        f"Лучший ход: {mistake['best']}\n"
        f"Другие хорошие ходы: "
        f"{', '.join(mistake['alternatives'][1:])}\n\n"
        f"{mistake['explanation']}"
    )

    label = tk.Label(
        frame,
        text=text,
        fg=color,
        font=("Arial", 12, "bold"),
        justify="left",
        anchor="w",
        wraplength=700
    )

    label.pack(side="left")

    frame.update_idletasks()

    print("Высота карточки:", frame.winfo_height())

    # ==========================================================
    # ПРОВЕРКА
    # ==========================================================

    print("=== ERROR CARD POSITION DATA ===")
    print("user_color =", mistake.get("user_color"))
    print("side =", mistake.get("side"))
    print("on_next =", mistake.get("on_next"))
    print("on_previous =", mistake.get("on_previous"))
    print("================================")

    # ==========================================================
    # КНОПКА «ПОПРОБОВАТЬ»
    # ==========================================================

    def open_position():

        print("Нажата кнопка Попробовать")

        # ------------------------------------------------------
        # Сторона пользователя
        # ------------------------------------------------------

        user_side = mistake.get("user_color")

        # На случай, если user_color отсутствует,
        # используем side ошибки.
        if user_side is None:
            user_side = mistake.get("side")

        print("USER SIDE =", user_side)

        # ------------------------------------------------------
        # Открываем позицию
        # ------------------------------------------------------

        show_position(
            mistake["fen"],
            mistake["best_uci"],

            on_next=mistake.get("on_next"),

            on_previous=mistake.get("on_previous"),

            on_success=mistake.get("on_success"),

            user_side=user_side,

            move_text=f"Ход {mistake['move']}",

            played_san=mistake.get("played_san"),

            explanation=mistake.get("explanation"),

            theme=mistake.get("theme"),

            captured_piece=mistake.get("captured_piece"),

            hanging_piece=mistake.get("hanging_piece"),

            hanging_square=mistake.get("hanging_square"),

            fork_targets=mistake.get("fork_targets"),

            pin_piece=mistake.get("pin_piece"),

            pin_square=mistake.get("pin_square"),

            mistake=mistake
        )

    tk.Button(
        frame,
        text="🎯 Попробовать",
        command=open_position
    ).pack(side="right", padx=5)

    return frame