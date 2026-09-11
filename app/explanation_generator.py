import chess


def explain_best_move(board, best_move):

    explanations = []

    piece = board.piece_at(best_move.from_square)

    if piece is None:
        return []

    # Рокировка
    if board.is_castling(best_move):
        explanations.append("позволяет увести короля в безопасное место")

    # Взятие
    if board.is_capture(best_move):
        explanations.append("выигрывает материал или устраняет опасную фигуру")

    # Пешка
    if piece.piece_type == chess.PAWN:

        if chess.square_rank(best_move.to_square) > chess.square_rank(best_move.from_square):
            explanations.append("укрепляет пешечный центр")

    # Конь
    elif piece.piece_type == chess.KNIGHT:
        explanations.append("улучшает расположение коня")


    # Ладья
    elif piece.piece_type == chess.ROOK:
        explanations.append("улучшает активность ладьи")

    # Ферзь
    elif piece.piece_type == chess.QUEEN:
        explanations.append("усиливает давление ферзём")

    return explanations


def explain_position(mistake):

    text = []

    # ==========================================
    # ПРОДВИЖЕНИЕ ПЕШКИ → АТАКА НА КОРОЛЯ
    # ==========================================

    if mistake.get("pawn_king_attack"):

        text.append(
            "Продвижение этой пешки создаёт возможности "
            "для атаки на позицию короля."
        )


    # ==========================================
    # ЖЕРТВА КОНЯ → ТАКТИЧЕСКАЯ АТАКА
    # ==========================================

    if mistake.get("knight_sacrifice"):

        text.append(
            "Лучшим решением было пожертвовать коня "
            "ради тактической атаки."
        )

    if mistake["loss"] < 200:
        text.append("Ход немного ухудшает позицию.")

    elif mistake["loss"] < 500:
        text.append("После этого хода соперник получает заметное преимущество.")

    else:
        text.append("Ход резко ухудшает позицию.")

    theme = mistake.get("theme") or ""

    if theme == "Зевок фигуры":
        text.append("Вы оставили фигуру без защиты.")

    elif theme == "Вилка":
        text.append("После вашего хода возникает возможность вилки.")

    elif theme == "Связка":
        text.append(
            "После вашего хода возникла связка, которая ограничивает подвижность фигуры."
        )

    elif theme == "Пропущена вилка":
        text.append(
            "Лучший ход создавал вилку и одновременно атаковал две ценные фигуры."
        )


    elif theme and theme.startswith("Висит"):
        text.append("После хода одна из фигур остаётся под боем.")



    elif theme == "Пропущена связка":
        text.append(
            "Лучший ход создавал связку и ограничивал подвижность фигуры соперника."
        )

    elif theme == "Потеря ферзя":
        text.append("После этого хода вы теряете ферзя.")

    elif theme == "Потеря ладьи":
        text.append("После этого хода вы теряете ладью.")

    elif theme == "Потеря пешки":
        text.append(
            "После этого хода вы теряете пешку без достаточной компенсации."
        )

    elif theme == "Мат в 1":
        text.append("Вы пропустили форсированный мат в один ход.")

    best = mistake.get("best")

    board = chess.Board(mistake["fen"])
    move = chess.Move.from_uci(mistake["best_uci"])

    ideas = explain_best_move(board, move)

    for idea in ideas:
        text.append(idea)

    if best:
        text.append(f"Лучше было сыграть {best}.")

    return "\n\n".join(text)