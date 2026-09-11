import tkinter as tk
from tkinter import messagebox
from app.app.position_view import show_position
from app.training_result import show_training_result


class ErrorTrainer:

    def __init__(self, window, mistakes):

        self.window = window
        self.mistakes = mistakes
        self.index = 0

        self.first_try = 0
        self.after_mistakes = 0

        self.failed_mistakes = []

        self.frame = tk.Frame(window)
        self.frame.pack(fill="both", expand=True)

        self.counter = tk.Label(
            self.frame,
            font=("Arial", 14, "bold")
        )
        self.counter.pack(pady=10)

        self.info = tk.Label(
            self.frame,
            justify="left",
            anchor="w",
            font=("Arial", 12)
        )
        self.info.pack(fill="x", padx=20)

        self.button_frame = tk.Frame(self.frame)
        self.button_frame.pack(pady=10)

        self.show_button = tk.Button(
            self.button_frame,
            text="🎯 Попробовать",
            width=18,
            command=self.try_position
        )
        self.show_button.grid(row=0, column=1, padx=10)

        self.prev_button = tk.Button(
            self.button_frame,
            text="⬅ Предыдущая",
            width=15,
            command=self.previous
        )
        self.prev_button.grid(row=0, column=0)

        self.next_button = tk.Button(
            self.button_frame,
            text="Следующая ➡",
            width=15,
            command=self.next
        )
        self.next_button.grid(row=0, column=2)

        self.refresh()

    def refresh(self):

        mistake = self.mistakes[self.index]

        self.counter.config(
            text=f"Ошибка {self.index + 1} из {len(self.mistakes)}"
        )

        self.info.config(
            text=(
                f"{mistake['type']}\n\n"
                f"Ход: {mistake['move_text']} {mistake['played_san']} {mistake['symbol']}\n"
                f"До хода: {mistake['before_score']}\n"
                f"После хода: {mistake['after_score']}\n"
                f"Потеря: {mistake['loss']} cp\n\n"
                f"Тема: {mistake['theme']}\n\n"
                f"Лучший ход: {mistake['best']}\n\n"
                f"{mistake['explanation']}"
            )
        )

        self.prev_button.config(
            state="normal" if self.index > 0 else "disabled"
        )

        self.next_button.config(
            state="normal"
            if self.index < len(self.mistakes) - 1
            else "disabled"
        )

    def previous(self):

        if self.index > 0:
            self.index -= 1
            self.refresh()

    def next(self):

        if self.index < len(self.mistakes) - 1:
            self.index += 1
            self.refresh()

    def try_position(self):

        mistake = self.mistakes[self.index]

        show_position(
            mistake["fen"],
            mistake["best_uci"],
            on_success=self.save_result,
            on_next=self.next_position
        )

    def next_position(self):

        if self.index < len(self.mistakes) - 1:

            self.index += 1
            self.refresh()

            mistake = self.mistakes[self.index]

            show_position(
                mistake["fen"],
                mistake["best_uci"],
                on_success=self.save_result,
                on_next=self.next_position
            )

        else:

            self.show_statistics()

            self.window.lift()
            self.window.focus_force()

    def save_result(self, mistakes_before_success):

        if mistakes_before_success == 0:

            self.first_try += 1

        else:

            self.after_mistakes += 1

            self.failed_mistakes.append(
                self.mistakes[self.index]
            )


        print(
            "Первая попытка:",
            self.first_try,
            "| После ошибок:",
            self.after_mistakes
        )

    def show_statistics(self):

        total = self.first_try + self.after_mistakes

        if total == 0:
            accuracy = 0

        else:
            accuracy = round(self.first_try / total * 100)

        show_training_result(
            total,
            self.first_try,
            self.after_mistakes,
            accuracy,
            on_repeat=self.repeat_failed_positions
        )

    def repeat_failed_positions(self):

        if not self.failed_mistakes:
            return

        self.mistakes = self.failed_mistakes.copy()

        self.failed_mistakes = []

        self.index = 0
        self.first_try = 0
        self.after_mistakes = 0

        self.refresh()

        self.try_position()

   
    