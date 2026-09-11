import tkinter as tk

from app.history import load_history


def open_history(window):

    history = load_history()

    games = len(history)

    average_accuracy = 0

    for game in history:
        average_accuracy += game["accuracy"]

    if games:
        average_accuracy /= games

    history_window = tk.Toplevel(window)
    history_window.title("История анализов")
    history_window.geometry("700x500")

    title = tk.Label(
        history_window,
        text="📈 История анализов",
        font=("Arial", 18, "bold")
    )
    title.pack(pady=10)

    stats = tk.Label(
        history_window,
        text=(
            f"Партий: {games}\n"
            f"Средняя точность: {average_accuracy:.1f}%"
        ),
        font=("Arial", 13, "bold")
    )

    stats.pack(pady=10)


    if not history:

        tk.Label(
            history_window,
            text="История пока пуста",
            font=("Arial", 14)
        ).pack(pady=20)

        return

    for game in history:

        text = (
            f"{game['file']}\n"
            f"Точность: {game['accuracy']:.1f}%\n"
            f"Дебют: {game['opening']}\n"
        )

        tk.Label(
            history_window,
            text=text,
            justify="left",
            anchor="w",
            font=("Arial", 12)
        ).pack(fill="x", padx=15, pady=5)