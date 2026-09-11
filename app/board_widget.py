import tkinter as tk
import chess


class ChessBoard:

    def __init__(self, window, board):

        self.board = board

        self.size = 60

        self.canvas = tk.Canvas(
            window,
            width=480,
            height=480
        )

        self.canvas.pack(pady=10)

        self.colors = ["#f0d9b5", "#b58863"]

        self.pieces = {
            "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
            "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"
        }

        self.selected = None

        self.possible_moves = []

        self.draw()

    def draw(self):

        self.canvas.delete("all")

        for rank in range(8):
            for file in range(8):

                x1 = file * self.size
                y1 = rank * self.size
                x2 = x1 + self.size
                y2 = y1 + self.size

                color = self.colors[(rank + file) % 2]

                square = chess.square(file, 7 - rank)

                possible_move = square in self.possible_moves

                outline = ""
                width = 1

                if self.selected == square:
                    outline = "blue"
                    width = 4

                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline=outline,
                    width=width
                )

                if possible_move:

                    radius = 8

                    self.canvas.create_oval(
                        x1 + self.size / 2 - radius,
                        y1 + self.size / 2 - radius,
                        x1 + self.size / 2 + radius,
                        y1 + self.size / 2 + radius,
                        fill="#00cc66",
                        outline=""
                    )

                piece = self.board.piece_at(square)

                if piece:

                    self.canvas.create_text(
                        x1 + self.size / 2,
                        y1 + self.size / 2,
                        text=self.pieces[piece.symbol()],
                        font=("Arial", 34)
                    )

    def update_board(self, board):

        self.board = board
        self.draw()

    def set_selected(self, square):

        self.selected = square
        self.draw()

    def set_possible_moves(self, moves):
        self.possible_moves = moves
        self.draw()            


