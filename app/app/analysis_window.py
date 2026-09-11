import tkinter as tk
from app.widgets.graph_widget import create_graph
from app.widgets.error_card import create_error_card
from app.error_training_window import open_error_training
from app.widgets.theme_widget import create_theme_widget

print("Загружен НОВЫЙ analysis_window.py")


def show_analysis(
    window,
    mistakes,
    scores,
    accuracy,
    opening,
    statistics,
    phase_statistics,
    user_color
):

    analysis_window = tk.Toplevel(window)
    analysis_window.title("Результаты анализа")
    analysis_window.geometry("900x900")

    canvas = tk.Canvas(analysis_window)

    scrollbar = tk.Scrollbar(
            analysis_window,
        orient="vertical",
        command=canvas.yview
    )

    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window(
        (0, 0),
        window=scrollable_frame,
        anchor="nw"
    )

    canvas.configure(
        yscrollcommand=scrollbar.set
    )

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    tk.Label(
        scrollable_frame,
        text="Результаты анализа",
        font=("Arial", 20, "bold")
    ).pack(pady=15)

    tk.Label(
        scrollable_frame,
        text=f"📚 Дебют: {opening}",
        fg="blue",
        font=("Arial", 14, "bold")
    ).pack()

    tk.Label(
        scrollable_frame,
        text=f"🎯 Точность партии: {accuracy}%",
        fg="darkgreen",
        font=("Arial", 16, "bold")
    ).pack(pady=10)

    phase_frame = tk.LabelFrame(
        scrollable_frame,
        text="📊 Анализ по фазам партии"
    )
    phase_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(
        phase_frame,
        text=f"♟ Дебют: {phase_statistics['opening']}"
    ).pack(anchor="w")

    tk.Label(
        phase_frame,
        text=f"⚔ Миттельшпиль: {phase_statistics['middlegame']}"
    ).pack(anchor="w")

    tk.Label(
        phase_frame,
        text=f"👑 Эндшпиль: {phase_statistics['endgame']}"
    ).pack(anchor="w")

    stats_frame = tk.LabelFrame(
        scrollable_frame,
        text="📈 Статистика"
    )
    stats_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(
        stats_frame,
        text=f"🟡 Неточностей: {statistics['inaccuracies']}"
    ).pack(anchor="w")

    tk.Label(
        stats_frame,
        text=f"🟠 Ошибок: {statistics['mistakes']}"
    ).pack(anchor="w")

    tk.Label(
        stats_frame,
        text=f"🔴 Грубых ошибок: {statistics['blunders']}"
    ).pack(anchor="w")

    create_graph(scrollable_frame, scores)

    current_index = tk.IntVar(value=0)

    card_container = tk.Frame(scrollable_frame)
    card_container.pack(fill="x", pady=10)

    create_theme_widget(
        scrollable_frame,
        mistakes
    )

    tk.Label(
        scrollable_frame,
        text="🎯 Тренировка по ошибкам",
        font=("Arial", 13, "bold")
    ).pack(pady=(15, 5))

    my_mistakes = [
        m for m in mistakes
        if m["side"] == user_color
    ]

    opponent_color = (
        "black"
        if user_color == "white"
        else "white"
    )

    opponent_mistakes = [
        m for m in mistakes
        if m["side"] == opponent_color
    ]

    training_frame = tk.Frame(scrollable_frame)
    training_frame.pack(pady=10)

    tk.Button(
        training_frame,
        text="👤 Мои ошибки",
        width=20,
        command=lambda: open_error_training(my_mistakes)
    ).grid(row=0, column=0, padx=5, pady=5)

    tk.Button(
        training_frame,
        text="🤖 Ошибки соперника",
        width=20,
        command=lambda: open_error_training(opponent_mistakes)
    ).grid(row=0, column=1, padx=5, pady=5)

    tk.Button(
        training_frame,
        text="📋 Все ошибки",
        width=20,
        command=lambda: open_error_training(mistakes)
    ).grid(row=1, column=0, columnspan=2, pady=5)

    def show_current():

        for widget in card_container.winfo_children():
            widget.destroy()

        mistake = mistakes[current_index.get()]

        mistake["on_next"] = next_error
        mistake["on_previous"] = previous


        create_error_card(
            card_container,
            mistake
        )

        # ==========================================================
        # ОБЪЯСНЕНИЕ ПРИЧИНЫ ОШИБКИ
        # ==========================================================

        move_reasons = mistake.get(
            "move_reasons",
            []
        )

        if move_reasons:

            reason_frame = tk.LabelFrame(
                card_container,
                text="💡 Почему этот ход оказался ошибкой",
                padx=10,
                pady=10
            )

            reason_frame.pack(
                fill="x",
                padx=10,
                pady=10
            )

            for reason in move_reasons:

                tk.Label(
                    reason_frame,
                    text=reason,
                    font=("Arial", 12),
                    wraplength=750,
                    justify="left",
                    anchor="w"
                ).pack(
                    fill="x",
                    pady=3
                )

    buttons_frame = tk.Frame(scrollable_frame)
    buttons_frame.pack(pady=10)

    def previous():

        if current_index.get() > 0:
            current_index.set(current_index.get() - 1)
            print("Предыдущая ошибка:", current_index.get())
            show_current()

    def next_error():

        if current_index.get() < len(mistakes) - 1:
            current_index.set(current_index.get() + 1)
            print("Следующая ошибка:", current_index.get())
            show_current()


    show_current()

    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))


