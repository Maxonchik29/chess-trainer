import tkinter as tk


def show_training_result(
    total,
    first_try,
    after_mistakes,
    accuracy,
    on_repeat=None
):

    window = tk.Toplevel()

    window.title("Тренировка завершена")
    window.geometry("420x330")
    window.resizable(False, False)

    tk.Label(
        window,
        text="🏆 Тренировка завершена",
        font=("Arial", 18, "bold")
    ).pack(pady=15)

    tk.Label(
        window,
        text=(
            f"Всего позиций: {total}\n\n"
            f"✅ С первой попытки: {first_try}\n"
            f"🟡 После ошибок: {after_mistakes}\n\n"
            f"🎯 Точность: {accuracy}%"
        ),
        justify="left",
        font=("Arial", 13)
    ).pack(pady=10)

    button_frame = tk.Frame(window)
    button_frame.pack(pady=20)

 #    tk.Button(
 #        button_frame,
 #        text="🔄 Повторить",
 #        width=14,
 #        command=lambda: (
 #            window.destroy(),
 #            on_repeat() if on_repeat is not None else None
 #        )
 #    ).grid(row=0, column=0, padx=5)

    tk.Button(
        button_frame,
        text="📊 Назад",
        width=14,
        command=window.destroy
    ).grid(row=0, column=0, padx=5)