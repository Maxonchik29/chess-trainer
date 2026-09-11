import tkinter as tk
from app.chess_logic import find_piece


def open_mate_in_one(window):

    mate_window = tk.Toplevel(window)
    mate_window.title("Мат в 1 ход")
    mate_window.geometry("800x800")


    title = tk.Label(
        mate_window,
        text="Тренажёр: Мат в 1 ход",
        font=("Arial", 20, "bold")
    )
    title.pack(pady=20)


    info = tk.Label(
        mate_window,
        text="Белые ходят. Сделайте мат",
        font=("Arial", 16)
    )
    info.pack(pady=10)


    board_frame = tk.Frame(mate_window)
    board_frame.pack()




            # Позиция фигур
    pieces = {
        (7, 6): "♔",
        (3, 7): "♕",

        (0, 6): "♚",
        (1, 6): "♟",
        (1, 7): "♟"
    }

    

    def queen_attacks(square):

        queen = find_piece(pieces, "♕")

        if queen is None:
            return False

        q_row, q_col = queen
        s_row, s_col = square

        if q_row == s_row:
            return True

        if q_col == s_col:
            return True

        if abs(q_row - s_row) == abs(q_col - s_col):
            return True

        return False

    buttons = {}

    selected = {"pos": None}


    info = tk.Label(
        mate_window,
        text="Белые ходят. Сделайте мат",
        font=("Arial", 16)
    )
    info.pack(pady=20)



    def click_cell(row, col):

        pos = (row, col)


        # если выбрана фигура
        if selected["pos"]:

            old = selected["pos"]

            piece = pieces.pop(old)


            # правильный ход ферзя h5-h7
            if piece == "♕" and pos == (1,7):

                pieces[pos] = piece

                buttons[old]["text"] = ""
                buttons[pos]["text"] = piece

                info.config(
                    text="♕ Мат! Правильно!"
                )

                buttons[old]["bg"] = "white" if (old[0] + old[1]) % 2 == 0 else "gray"
                selected["pos"] = None


            else:

                # вернуть фигуру назад
                pieces[old] = piece

                info.config(
                    text="Ошибка. Попробуй ещё"
                )

                buttons[old]["bg"] = "white" if (old[0] + old[1]) % 2 == 0 else "gray"
                selected["pos"] = None


        # выбираем фигуру
        elif pos in pieces:

            if pieces[pos] == "♕":

                selected["pos"] = pos

                buttons[pos]["bg"] = "yellow"

                info.config(
                    text="Ферзь выбран. Куда ходить?"
                )



    # создаём доску

    for row in range(8):
        for col in range(8):

            color = "white" if (row + col) % 2 == 0 else "gray"

            text = pieces.get((row, col), "")


            button = tk.Button(
                board_frame,
                text=text,
                font=("Arial", 25),
                width=2,
                height=1,
                bg=color,
                command=lambda r=row, c=col: click_cell(r,c)
            )


            button.grid(row=row, column=col)

            buttons[(row,col)] = button



    back_button = tk.Button(
        mate_window,
        text="Назад",
        font=("Arial",14),
        width=20,
        command=mate_window.destroy
    )

    back_button.pack(pady=20)