import tkinter as tk
from app.error_training_window import open_error_training


def create_theme_widget(parent, mistakes):

    frame = tk.LabelFrame(
        parent,
        text="🎯 Темы ошибок",
        font=("Arial", 11, "bold")
    )

    frame.pack(fill="x", padx=10, pady=10)

    themes = {}

    for mistake in mistakes:

        theme = mistake["theme"]

        themes[theme] = themes.get(theme, 0) + 1

    if not themes:

        tk.Label(
            frame,
            text="Темы не определены."
        ).pack()

        return

    sorted_themes = sorted(
        themes.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for theme, count in sorted_themes:

        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=2)

        tk.Label(
            row,
            text=f"{theme}: {count}",
            anchor="w",
            font=("Arial", 11)
        ).pack(side="left")

        tk.Button(
            row,
            text="🎯 Тренировать",
            command=lambda t=theme: open_error_training(
                [m for m in mistakes if m["theme"] == t]
            )
        ).pack(side="right")

    return frame