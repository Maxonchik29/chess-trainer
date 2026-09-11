import tkinter as tk


def create_statistics(parent, statistics):
    frame = tk.LabelFrame(
        parent,
        text="📋 Статистика",
        font=("Arial", 11, "bold")
    )

    frame.pack(fill="x", padx=10, pady=10)

    tk.Label(
        frame,
        text=f"🟡 Неточностей: {statistics['inaccuracies']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    tk.Label(
        frame,
        text=f"🟠 Ошибок: {statistics['mistakes']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    tk.Label(
        frame,
        text=f"🔴 Грубых ошибок: {statistics['blunders']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)