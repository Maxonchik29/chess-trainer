import tkinter as tk

from app.mistake_storage import load_mistakes, get_visible_mistakes
from app.app.position_view import show_position


def open_personal_training(window):

    training_window = tk.Toplevel(window)
    training_window.title("Личная тренировка")
    training_window.geometry("700x700")

    all_mistakes = load_mistakes()

    visible_mistakes = get_visible_mistakes(all_mistakes)

    mistakes = [
        m for m in visible_mistakes
        if m.get("side") == m.get("user_side")
    ]

    if not mistakes:

        tk.Label(
            training_window,
            text="Ошибок пока нет.",
            font=("Arial", 14)
        ).pack()

        return
    
    tk.Label(
        training_window,
        text="🎯 Личная тренировка",
        font=("Arial", 20, "bold")
    ).pack(pady=20)

    tk.Label(
        training_window,
        text=f"Всего ошибок: {len(mistakes)}",
        font=("Arial", 14)
    ).pack(pady=10)

    current = 0
    training_position_window = None

    def open_current():
        nonlocal current
        nonlocal training_position_window

        mistake = mistakes[current]

        def next_error():
            nonlocal current

            if current < len(mistakes) - 1:
                current += 1
                open_current()
            else:
                print("Все ошибки пройдены!")

        print(mistake)

        print("THEME DIRECT =", mistake.get("theme"))
        print("FEATURES =", mistake.get("features"))
        print("HANGING DIRECT =", mistake.get("hanging_piece"))
        print("HANGING FROM FEATURES =", mistake.get("features", {}).get("hanging_piece"))
        print("SQUARE DIRECT =", mistake.get("hanging_square"))
        print("SQUARE FROM FEATURES =", mistake.get("features", {}).get("hanging_square"))

        print("FEATURES =", mistake.get("features"))
        print("THEME =", mistake.get("theme"))
        print("HANGING =", mistake.get("hanging_piece"))
        print("HANGING FEATURES =", mistake.get("features", {}).get("hanging_piece"))

        print("EXPLANATION =", mistake.get("explanation"))

        print("=== ПЕРЕД SHOW_POSITION ===")
        print("THEME =", mistake.get("theme"))
        print("FEATURES =", mistake.get("features"))
        print("PIN PIECE =", mistake.get("features", {}).get("pin_piece"))
        print("PIN SQUARE =", mistake.get("features", {}).get("pin_square"))
        print("============================")

        training_position_window = show_position(
            mistake["fen"],
            mistake["best_uci"],
            on_next=next_error,
            user_side=mistake["user_side"],
            move_text=mistake["move_text"],
            played_san=mistake["played_san"],
            explanation=mistake.get("explanation"),
            theme=mistake["theme"],
            captured_piece=mistake.get("captured_piece"),
            hanging_piece=mistake.get("features", {}).get("hanging_piece"),
            hanging_square=mistake.get("features", {}).get("hanging_square"),
            fork_targets=mistake.get("features", {}).get("fork_targets", []),
            pin_piece=mistake.get("features", {}).get("pin_piece"),
            pin_square=mistake.get("features", {}).get("pin_square"),
            existing_window=training_position_window,
            mistake=mistake
        )

    tk.Button(
        training_window,
        text="▶ Начать тренировку",
        font=("Arial", 14),
        command=open_current
    ).pack(pady=20)

