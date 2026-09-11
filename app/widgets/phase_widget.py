import tkinter as tk


def create_phase_widget(parent, phase_statistics):

    frame = tk.LabelFrame(
        parent,
        text="📊 Анализ по фазам партии",
        font=("Arial", 11, "bold")
    )

    frame.pack(fill="x", padx=10, pady=10)

    tk.Label(
        frame,
        text=f"♟ Дебют: {phase_statistics['opening']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    tk.Label(
        frame,
        text=f"⚔ Миттельшпиль: {phase_statistics['middlegame']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    tk.Label(
        frame,
        text=f"👑 Эндшпиль: {phase_statistics['endgame']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    weakest = min(
        phase_statistics,
        key=phase_statistics.get
    )

    names = {
        "opening": "♟ Дебют",
        "middlegame": "⚔ Миттельшпиль",
        "endgame": "👑 Эндшпиль"
    }

    tk.Label(
        frame,
        text=f"\nСамая слабая часть: {names[weakest]}",
        fg="red",
        font=("Arial", 11, "bold")
    ).pack(pady=5)