
from app.chess_game import ChessGame


def main():

    print("=" * 50)
    print("ТЕСТ CHESS GAME")
    print("=" * 50)

    game = ChessGame()

    try:

        print("\nНачальная позиция:")
        print(game.get_board())

        print("\nХод игрока: e2e4")

        result = game.make_player_move("e2e4")

        print("Сыграно:", result["played_san"])
        print("Лучше было:", result["best_san"])
        print("Это лучший ход:", result["is_best"])

        print("\nПозиция после хода игрока:")
        print(game.get_board())

        print("\nХод компьютера...")

        computer_result = game.make_computer_move()

        if computer_result:

            print(
                "Компьютер сыграл:",
                computer_result["san"]
            )

        print("\nПозиция после хода компьютера:")
        print(game.get_board())

        print("\nFEN:")
        print(game.get_fen())

        print("\nСтатус:")
        print(game.get_status())

        print("\nТест успешно завершён.")

    finally:

        game.close()

        print("\nStockfish закрыт.")


if __name__ == "__main__":
    main()
