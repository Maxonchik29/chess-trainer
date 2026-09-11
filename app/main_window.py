import tkinter as tk

from app.tactics import open_tactics

from app.my_games import open_my_games

from app.history_window import open_history

from app.player_statistics_window import open_player_statistics

from app.personal_training import open_personal_training

from app.play_vs_computer import open_play_vs_computer


window = tk.Tk()

window.title("Chess Trainer")

window.geometry("900x600")


title = tk.Label(
    window,
    text="♟ Chess Trainer",
    font=("Arial", 22, "bold")
)

title.pack(
    pady=20
)


analysis_button = tk.Button(
    window,
    text="Анализ партии",
    font=("Arial", 14),
    width=20
)

analysis_button.pack(
    pady=10
)


openings_button = tk.Button(
    window,
    text="Мои дебюты",
    font=("Arial", 14),
    width=20
)

openings_button.pack(
    pady=10
)


tactics_button = tk.Button(
    window,
    text="Тактика",
    font=("Arial", 14),
    width=20,
    command=lambda: open_tactics(window)
)

tactics_button.pack(
    pady=10
)


# ============================================================
# ИГРА С КОМПЬЮТЕРОМ
# ============================================================

computer_button = tk.Button(
    window,
    text="♟ Играть с компьютером",
    font=("Arial", 14),
    width=20,
    command=lambda: open_play_vs_computer(window)
)

computer_button.pack(
    pady=10
)


my_games_button = tk.Button(
    window,
    text="📂 Мои партии",
    font=("Arial", 14),
    width=20,
    command=lambda: open_my_games(window)
)

my_games_button.pack(
    pady=10
)


history_button = tk.Button(
    window,
    text="📈 История анализов",
    font=("Arial", 14),
    width=20,
    command=lambda: open_history(window)
)

history_button.pack(
    pady=10
)


tk.Button(
    window,
    text="📊 Статистика игрока",
    width=25,
    command=lambda: open_player_statistics(window)
).pack(
    pady=5
)


tk.Button(
    window,
    text="🎯 Личная тренировка",
    font=("Arial", 14),
    width=20,
    command=lambda: open_personal_training(window)
).pack(
    pady=5
)


exit_button = tk.Button(
    window,
    text="Выход",
    font=("Arial", 14),
    width=20,
    command=window.destroy
)

exit_button.pack(
    pady=10
)


window.mainloop()