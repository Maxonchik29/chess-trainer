import tkinter as tk

from app.player_statistics import load_statistics


def open_player_statistics(window):

    stats = load_statistics()

    stat_window = tk.Toplevel(window)
    stat_window.title("Статистика игрока")
    stat_window.geometry("500x500")

    tk.Label(
        stat_window,
        text="📊 Статистика игрока",
        font=("Arial", 20, "bold")
    ).pack(pady=15)

    total_games = stats["games"]

    if total_games == 0:
        avg = 0
    else:
        avg = round(
            (stats["mistakes"] +
             stats["inaccuracies"] +
             stats["blunders"]) / total_games,
            2
        )

    text = (
        f"🎮 Проанализировано партий: {stats['games']}\n\n"

        f"🟡 Неточностей: {stats['inaccuracies']}\n"
        f"🟠 Ошибок: {stats['mistakes']}\n"
        f"🔴 Грубых ошибок: {stats['blunders']}\n\n"

        f"📉 Среднее количество ошибок за партию: {avg}"
    )

    tk.Label(
        stat_window,
        text=text,
        font=("Arial", 13),
        justify="left"
    ).pack(pady=10)