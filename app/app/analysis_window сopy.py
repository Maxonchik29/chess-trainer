from app.app.position_view import show_position
from app.error_trainer import ErrorTrainer
import tkinter as tk
from app.training_session import TrainingSession


def show_analysis(window, mistakes, scores, accuracy, opening, statistics, phase_statistics, user_color):

    analysis_window = tk.Toplevel(window)
    analysis_window.title("Результаты анализа")
    analysis_window.geometry("600x500")

    training = TrainingSession()

    def save_training_result(mistakes_before_success):

        training.add_result(mistakes_before_success)

        print("Результаты тренировки:", training.results)

    title = tk.Label(
        analysis_window,
        text="Результаты анализа",
        font=("Arial", 18, "bold")
    )
    title.pack(pady=10)

    counter_label = tk.Label(
        analysis_window,
        text=f"Ошибок найдено: {len(mistakes)}",
        font=("Arial", 12)
    )


    opening_label = tk.Label(
        analysis_window,
        text=f"📚 Дебют: {opening}",
        font=("Arial", 13, "bold"),
        fg="blue"
    )
    opening_label.pack(pady=5)

    accuracy_label = tk.Label(
        analysis_window,
        text=f"🎯 Точность партии: {accuracy}%",
        font=("Arial", 15, "bold"),
        fg="darkgreen"
    )

    accuracy_label.pack(pady=5)
    phase_frame = tk.LabelFrame(
        analysis_window,
        text="📊 Анализ по фазам партии",
        font=("Arial", 11, "bold")
    )

    phase_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(
        phase_frame,
        text=f"♟ Дебют: {phase_statistics['opening']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    tk.Label(
        phase_frame,
        text=f"⚔ Миттельшпиль: {phase_statistics['middlegame']}",
        anchor="w",
        font=("Arial", 11)
    ).pack(fill="x", padx=10)

    tk.Label(
        phase_frame,
        text=f"👑 Эндшпиль: {phase_statistics['endgame']}",
        anchor="w",
         font=("Arial", 11)
    ).pack(fill="x", padx=10)

    worst_phase = min(
        phase_statistics,
        key=phase_statistics.get
    )

    names = {
        "opening": "♟ Дебют",
        "middlegame": "⚔ Миттельшпиль",
        "endgame": "👑 Эндшпиль"
    }

    tk.Label(
        phase_frame,
        text=f"\nСамая слабая часть: {names[worst_phase]}",
        fg="red",
        font=("Arial", 11, "bold")
    ).pack(pady=5)

    stats_label = tk.Label(
        analysis_window,
        text=(
        f"🟡 Неточностей: {statistics['inaccuracies']}\n"
        f"🟠 Ошибок: {statistics['mistakes']}\n"
        f"🔴 Грубых ошибок: {statistics['blunders']}"
        ),
        font=("Arial", 12),
        justify="left"
    )

    stats_label.pack(pady=5)

#    trainer = ErrorTrainer(analysis_window, mistakes)

    choice_frame = tk.Frame(analysis_window) 

    choice_frame.pack(pady=15)

    tk.Label( 
        choice_frame, 
        text="Какие ошибки разобрать?", 
        font=("Arial", 12, "bold") 
    ).pack(pady=5)

    def start_training(mode):

        if mode == "mine":
            selected = [m for m in mistakes if m["side"] == user_color]

        elif mode == "opponent":
            opposite = "black" if user_color == "white" else "white"
            selected = [m for m in mistakes if m["side"] == opposite]

        else:
            selected = mistakes

        choice_frame.destroy()

        analysis_window.trainer = ErrorTrainer(analysis_window, selected)

    button_frame = tk.Frame(choice_frame)
    button_frame.pack()

    tk.Button(
        button_frame,
        text="🎯 Мои ошибки",
        width=16,
        command=lambda: start_training("mine")
    ).grid(row=0, column=0, padx=5)

    tk.Button(
        button_frame,
        text="👤 Ошибки соперника",
        width=18,
        command=lambda: start_training("opponent")
    ).grid(row=0, column=1, padx=5)

    tk.Button(
        button_frame,
        text="📋 Все ошибки",
        width=16,
        command=lambda: start_training("all")
    ).grid(row=0, column=2, padx=5)


    current = tk.IntVar(value=0)

    graph = tk.Canvas(
        analysis_window,
        width=550,
        height=180,
        bg="white"
    )

    graph.pack(pady=10)

    graph.create_line(40, 20, 40, 160, width=2)

    graph.create_line(40, 90, 530, 90, width=2)

    if len(scores) > 1:

        step = 480 / (len(scores) - 1)

        points = []

        for i, score in enumerate(scores):

            score = max(-500, min(500, score))

            x = 40 + i * step
            y = 90 - score / 10

            points.extend([x, y])

        graph.create_line(points, fill="blue", width=2)
    
    if not mistakes:
        tk.Label(
            analysis_window,
            text="Ошибок не найдено 🎉",
            font=("Arial", 14)
        ).pack(pady=20)
        return




    for index, mistake in enumerate(mistakes, start=1):

        frame = tk.Frame(analysis_window)
        frame.pack(fill="x", padx=10, pady=5)

        if "Неточность" in mistake["type"]:
            color = "#d4a017"   

        elif "Ошибка" in mistake["type"]:
            color = "#ff8800"

        else:
            color = "#cc0000"

        text = (
            f"{mistake['type']}\n"
            f"Ход {mistake['move']}\n"
            f"До хода: {mistake['before_score']}\n"
            f"После хода: {mistake['after_score']}\n"
            f"Потеря: {mistake['loss']} cp\n"
            f"Лучший ход: {mistake['best']}\n\n"
            f"{mistake['explanation']}"

        )

        tk.Label(
            frame,
            text=text,
            fg=color,
            font=("Arial", 12, "bold"),
            justify="left",
            anchor="w"
        ).pack(side="left")

        tk.Button(
            frame,
            text="🎯 Попробовать",
            command=lambda fen=mistake["fen"], best=mistake["best_uci"]: show_position(
                fen,
                best,
                on_success=save_training_result
            )
        
        ).pack(side="right", padx=5)