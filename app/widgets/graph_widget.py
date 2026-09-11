import tkinter as tk


def create_graph(parent, scores):

    graph = tk.Canvas(
        parent,
        width=550,
        height=180,
        bg="white"
    )

    graph.pack(pady=10)

    graph.create_line(40, 20, 40, 160, width=2)
    graph.create_line(40, 90, 530, 90, width=2)

    if len(scores) <= 1:
        return

    step = 480 / (len(scores) - 1)

    points = []

    for i, score in enumerate(scores):

        score = max(-500, min(500, score))

        x = 40 + i * step
        y = 90 - score / 10

        points.extend([x, y])

    graph.create_line(points, fill="blue", width=2)