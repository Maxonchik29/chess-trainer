import tkinter as tk
from app.app.position_view import show_position

import os

print("=== ЗАГРУЖЕН error_training_window.py ===")


def open_error_training(mistakes):

    if not mistakes:
        return

    current = 0

    # СОЗДАЁМ ОДНО ОКНО НА ВСЮ ТРЕНИРОВКУ
    training_window = tk.Toplevel()
    training_window.title("Позиция")
    training_window.geometry("520x700")

    def open_current():

        nonlocal current

        print("OPEN_CURRENT")
        print("Текущий индекс:", current)
        print("Всего ошибок:", len(mistakes))

        mistake = mistakes[current]

        def next_error():

            nonlocal current

            print("Нажали Следующая ошибка")
            print("Текущий индекс:", current)

            if current < len(mistakes) - 1:

                current += 1

                print("Переходим к ошибке:", current)

                open_current()

            else:

                print("Ошибок больше нет")
                training_window.destroy()

        print("=== ПЕРЕД SHOW_POSITION ===")
        print("training_window =", training_window)
        print("training_window id =", id(training_window))

        show_position(
            mistake["fen"],
            mistake["best_uci"],
            on_next=next_error,
            user_side=mistake.get("user_side"),
            move_text=mistake.get("move_text"),
            played_san=mistake.get("played_san"),
            explanation=mistake.get("explanation"),
            theme=mistake.get("theme"),
            captured_piece=mistake.get("captured_piece"),
             hanging_piece=mistake.get("features", {}).get("hanging_piece"),
            hanging_square=mistake.get("features", {}).get("hanging_square"),
            fork_targets=mistake.get("features", {}).get("fork_targets", []),

            pin_piece=mistake.get("features", {}).get("pin_piece"),
            pin_square=mistake.get("features", {}).get("pin_square"),
            existing_window=training_window
        )

    open_current()