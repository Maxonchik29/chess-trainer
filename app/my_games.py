import tkinter as tk
from tkinter import filedialog
import shutil
import os

from app.game_view import open_game_view


def choose_pgn():

    filename = filedialog.askopenfilename(
        title="Выберите PGN",
        filetypes=[("PGN files", "*.pgn")]
    )

    if not filename:
        return

    os.makedirs("games", exist_ok=True)

    new_file = os.path.join("games", os.path.basename(filename))

    shutil.copy(filename, new_file)

    print("Файл сохранён:", new_file)

def save_pgn(text_box):

    text = text_box.get("1.0", tk.END)

    if not text.strip():
        return

    os.makedirs("games", exist_ok=True)

    filename = filedialog.asksaveasfilename(
        defaultextension=".pgn",
        filetypes=[("PGN files", "*.pgn")],
        initialdir="games"
    )

    if not filename:
        return

    with open(filename, "w", encoding="utf-8") as file:
        file.write(text)

    print("PGN сохранён:", filename)

def open_pgn_editor():

    editor = tk.Toplevel()
    editor.title("Вставить PGN")
    editor.geometry("700x600")

    title = tk.Label(
        editor,
        text="Вставьте PGN партии",
        font=("Arial", 16, "bold")
    )
    title.pack(pady=10)

    text_box = tk.Text(
        editor,
        width=80,
        height=25
    )
    text_box.pack(pady=10)

    save_button = tk.Button(
        editor,
        text="💾 Сохранить",
        font=("Arial", 14),
        command=lambda: save_pgn(text_box)
    )
    save_button.pack(pady=10)

    close_button = tk.Button(
        editor,
        text="Закрыть",
        command=editor.destroy
    )
    close_button.pack(pady=10)


def get_pgn_files():

    os.makedirs("games", exist_ok=True)

    files = []

    for file in os.listdir("games"):
        if file.endswith(".pgn"):
            files.append(file)

    return files

def open_my_games(window):

    games_window = tk.Toplevel(window)
    games_window.title("Мои партии")
    games_window.geometry("700x500")

    title = tk.Label(
        games_window,
        text="📂 Мои партии",
        font=("Arial", 20, "bold")
    )
    title.pack(pady=15)

    upload_button = tk.Button(
        games_window,
        text="Загрузить PGN",
        font=("Arial", 14),
        width=20,
        command=choose_pgn
    )
    upload_button.pack(pady=5)

    paste_button = tk.Button(
        games_window,
        text="Вставить PGN",
        font=("Arial", 14),
        width=20,
        command=open_pgn_editor
    )
    paste_button.pack(pady=5)

    # ======================================================
    # ПРОКРУЧИВАЕМАЯ ОБЛАСТЬ СО СПИСКОМ ПАРТИЙ
    # ======================================================

    list_frame = tk.Frame(games_window)
    list_frame.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=10
    )

    canvas = tk.Canvas(
        list_frame,
        highlightthickness=0
    )

    scrollbar = tk.Scrollbar(
        list_frame,
        orient="vertical",
        command=canvas.yview
    )

    canvas.configure(
        yscrollcommand=scrollbar.set
    )

    scrollbar.pack(
        side="right",
        fill="y"
    )

    canvas.pack(
        side="left",
        fill="both",
        expand=True
    )

    games_frame = tk.Frame(canvas)

    canvas_window = canvas.create_window(
        (0, 0),
        window=games_frame,
        anchor="nw"
    )

    # ======================================================
    # ОБНОВЛЕНИЕ ОБЛАСТИ ПРОКРУТКИ
    # ======================================================

    def update_scrollregion(event=None):

        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    games_frame.bind(
        "<Configure>",
        update_scrollregion
    )

    # Растягиваем внутренний frame по ширине Canvas
    def update_frame_width(event):

        canvas.itemconfig(
            canvas_window,
            width=event.width
        )

    canvas.bind(
        "<Configure>",
        update_frame_width
    )

    # ======================================================
    # ПРОКРУТКА КОЛЁСИКОМ МЫШИ
    # ======================================================

    def on_mousewheel(event):

        canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    canvas.bind_all(
        "<MouseWheel>",
        on_mousewheel
    )

    # ======================================================
    # ЗАГРУЖАЕМ ВСЕ PGN
    # ======================================================

    files = get_pgn_files()

    if not files:

        info = tk.Label(
            games_frame,
            text="Пока партий нет.",
            font=("Arial", 14)
        )

        info.pack(
            pady=20
        )

    else:

        for file in files:

            button = tk.Button(
                games_frame,
                text="📄 " + file,
                font=("Arial", 12),
                width=45,
                command=lambda f=file: open_game_view(
                    games_window,
                    f
                )
            )

            button.pack(
                pady=3,
                padx=10
            )

    # ======================================================
    # КНОПКА НАЗАД
    # ======================================================

    def close_games_window():

        canvas.unbind_all(
            "<MouseWheel>"
        )

        games_window.destroy()

    back_button = tk.Button(
        games_window,
        text="Назад",
        font=("Arial", 14),
        width=20,
        command=close_games_window
    )

    back_button.pack(
        pady=10
    )