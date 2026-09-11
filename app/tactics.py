import tkinter as tk
from app.mate_in_one import open_mate_in_one


def open_tactics(window):
    tactics_window = tk.Toplevel(window)
    tactics_window.title("Тактика")
    tactics_window.geometry("600x400")

    label = tk.Label(
        tactics_window,
        text="Здесь будут тактические задачи",
        font=("Arial", 16)
    )
    label.pack(pady=20)

    mate1_button = tk.Button(
        tactics_window,
        text="Мат в 1 ход",
        font=("Arial", 14),
        width=20,
        command=lambda: open_mate_in_one(tactics_window)
    )
    mate1_button.pack(pady=10)

    mate2_button = tk.Button(
        tactics_window,
        text="Мат в 2 хода",
        font=("Arial", 14),
        width=20
    )
    mate2_button.pack(pady=10)

    back_button = tk.Button(
        tactics_window,
        text="Назад",
        font=("Arial", 14),
        width=20,
        command=tactics_window.destroy
    )
    back_button.pack(pady=10)