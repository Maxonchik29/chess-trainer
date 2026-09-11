
import logging
import os

import chess

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from app.chess_game import ChessGame


# ============================================================
# ТОКЕН БОТА
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")


# ============================================================
# TELEGRAM MINI APP
# ============================================================

WEB_APP_URL = "https://ТВОЙ-АДРЕС-MINI-APP"


# ============================================================
# ЛОГИ
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# ============================================================
# ИГРЫ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================

games = {}

# Выбранная пользователем фигура.
# user_id -> chess square


# ============================================================
# ОСНОВНАЯ КЛАВИАТУРА
# ============================================================

main_keyboard = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton(
                "♟ Играть с компьютером",
                web_app=WebAppInfo(
                    url=WEB_APP_URL
                )
            ),
        ],
    ],
    resize_keyboard=True,
)


# ============================================================
# СИМВОЛЫ ШАХМАТНЫХ ФИГУР
# ============================================================

PIECE_SYMBOLS = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",

    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}


# ============================================================
# СОЗДАНИЕ ШАХМАТНОЙ ДОСКИ
# ============================================================

def create_board_keyboard(game, selected_square=None):

    board = game.get_board()

    keyboard = []

    # Верхние координаты

    keyboard.append([
        InlineKeyboardButton(
            " ",
            callback_data="noop"
        ),
        *[
            InlineKeyboardButton(
                chr(ord("a") + file),
                callback_data="noop"
            )
            for file in range(8)
        ],
        InlineKeyboardButton(
            " ",
            callback_data="noop"
        ),
    ])

    # Доска

    for rank in range(7, -1, -1):

        row = [
            InlineKeyboardButton(
                str(rank + 1),
                callback_data="noop"
            )
        ]

        for file in range(8):

            square = chess.square(
                file,
                rank
            )

            square_name = chess.square_name(
                square
            )

            piece = board.piece_at(
                square
            )

            if piece is None:

                text = "·"

            else:

                text = PIECE_SYMBOLS[
                    piece.symbol()
                ]

            # Выбранная клетка

            if selected_square == square:

                text = "🟨" + text

            # Callback

            if selected_square is not None:

                callback_data = (
                    f"move:"
                    f"{chess.square_name(selected_square)}:"
                    f"{square_name}"
                )

            else:

                callback_data = (
                    f"select:{square_name}"
                )

            row.append(
                InlineKeyboardButton(
                    text,
                    callback_data=callback_data
                )
            )

        # Номер горизонтали справа

        row.append(
            InlineKeyboardButton(
                str(rank + 1),
                callback_data="noop"
            )
        )

        keyboard.append(row)

    # Нижние координаты

    keyboard.append([
        InlineKeyboardButton(
            " ",
            callback_data="noop"
        ),
        *[
            InlineKeyboardButton(
                chr(ord("a") + file),
                callback_data="noop"
            )
            for file in range(8)
        ],
        InlineKeyboardButton(
            " ",
            callback_data="noop"
        ),
    ])

    # Новая партия

    keyboard.append([
        InlineKeyboardButton(
            "🔄 Новая партия",
            callback_data="new_game"
        )
    ])

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# ТЕКСТ НАД ДОСКОЙ
# ============================================================

def board_message(
    game,
    extra_text=""
):

    text = "♟ Chess Trainer\n\n"

    if extra_text:

        text += extra_text
        text += "\n\n"

    if game.is_player_turn():

        text += "Ваш ход."

    else:

        text += "🤖 Ход компьютера."

    return text


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "♟ Chess Trainer\n\n"
        "Добро пожаловать!\n\n"
        "Нажми «♟ Играть с компьютером», "
        "чтобы начать партию.",
        reply_markup=main_keyboard,
    )


# ============================================================
# НОВАЯ ИГРА
# ============================================================

async def new_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    # --------------------------------------------------------
    # Закрываем старую игру
    # --------------------------------------------------------

    old_game = games.get(user_id)

    if old_game is not None:

        old_game.close()

    # --------------------------------------------------------
    # Создаём новую игру
    # --------------------------------------------------------

    game = ChessGame(
        player_color=chess.WHITE
    )

    games[user_id] = game

    # Сбрасываем выбранную фигуру

    context.user_data.pop(
        "selected_square",
        None
    )

    # --------------------------------------------------------
    # Показываем доску
    # --------------------------------------------------------

    await update.message.reply_text(
        board_message(game),
        reply_markup=create_board_keyboard(game)
    )


# ============================================================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    # --------------------------------------------------------
    # Новая игра
    # --------------------------------------------------------

    if text == "♟ Играть с компьютером":

        await new_game(
            update,
            context
        )

        return

    # --------------------------------------------------------
    # Если пользователь пишет обычный текст
    # --------------------------------------------------------

    await update.message.reply_text(
        "Используй шахматную доску.\n\n"
        "Нажми сначала на свою фигуру, "
        "затем нажми на клетку назначения."
    )


# ============================================================
# ОБРАБОТКА НАЖАТИЯ НА КЛЕТКУ
# ============================================================

async def handle_square(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    user_id = query.from_user.id

    game = games.get(
        user_id
    )

    if game is None:

        await query.answer(
            "Сначала начните новую игру.",
            show_alert=True
        )

        return

    # ========================================================
    # НОВАЯ ПАРТИЯ
    # ========================================================

    if query.data == "new_game":

        await query.answer()

        old_game = games.get(
            user_id
        )

        if old_game is not None:

            old_game.close()

        game = ChessGame(
            player_color=chess.WHITE
        )

        games[user_id] = game

        await query.edit_message_text(
            board_message(game),
            reply_markup=create_board_keyboard(game)
        )

        return

    # ========================================================
    # ПЕРВЫЙ КЛИК — SELECT
    # ========================================================

    if query.data.startswith("select:"):

        square_name = query.data.split(
            ":",
            1
        )[1]

        square = chess.parse_square(
            square_name
        )

        board = game.get_board()

        # Проверяем ход игрока

        if not game.is_player_turn():

            await query.answer(
                "Сейчас ход компьютера.",
                show_alert=True
            )

            return

        # Проверяем фигуру

        piece = board.piece_at(
            square
        )

        if piece is None:

            await query.answer(
                "Здесь нет фигуры."
            )

            return

        if piece.color != chess.WHITE:

            await query.answer(
                "Это фигура компьютера.",
                show_alert=True
            )

            return

        # Показываем выбранную клетку

        await query.answer(
            f"Выбрана клетка {square_name}.\n"
            "Теперь выбери клетку назначения."
        )

        await query.edit_message_text(
            board_message(
                game,
                f"Выбрана: {square_name}\n"
                "Выбери клетку назначения."
            ),
            reply_markup=create_board_keyboard(
                game,
                selected_square=square
            )
        )

        return

    # ========================================================
    # ВТОРОЙ КЛИК — MOVE
    # ========================================================

    if query.data.startswith("move:"):

        parts = query.data.split(":")

        if len(parts) != 3:

            await query.answer(
                "Ошибка данных хода.",
                show_alert=True
            )

            return

        from_square_name = parts[1]

        to_square_name = parts[2]

        print(
            "TELEGRAM MOVE:",
            from_square_name,
            "->",
            to_square_name
        )

        from_square = chess.parse_square(
            from_square_name
        )

        to_square = chess.parse_square(
            to_square_name
        )

        board = game.get_board()

        # ====================================================
        # Проверяем ход игрока
        # ====================================================

        if not game.is_player_turn():

            await query.answer(
                "Сейчас ход компьютера.",
                show_alert=True
            )

            return

        # ====================================================
        # Та же клетка
        # ====================================================

        if from_square == to_square:

            await query.answer(
                "Выбор отменён."
            )

            await query.edit_message_text(
                board_message(game),
                reply_markup=create_board_keyboard(game)
            )

            return

        # ====================================================
        # Создаём ход
        # ====================================================

        uci_move = (
            from_square_name
            +
            to_square_name
        )

        try:

            move = chess.Move.from_uci(
                uci_move
            )

        except ValueError:

            await query.answer(
                "Некорректный ход.",
                show_alert=True
            )

            return

        # ====================================================
        # Проверяем легальность
        # ====================================================

        if move not in board.legal_moves:

            await query.answer(
                "Так сходить нельзя.",
                show_alert=True
            )

            return

        await query.answer(
            "Ход принят."
        )

        # ====================================================
        # АНАЛИЗ
        # ====================================================

        await query.edit_message_text(
            board_message(
                game,
                "⏳ Анализирую ваш ход..."
            ),
            reply_markup=create_board_keyboard(game)
        )

        # ====================================================
        # ХОД ИГРОКА
        # ====================================================

        try:

            result = game.make_player_move(
                uci_move
            )

        except ValueError as error:

            await query.edit_message_text(
                board_message(
                    game,
                    f"❌ {error}"
                ),
                reply_markup=create_board_keyboard(game)
            )

            return

        played_san = result[
            "played_san"
        ]

        best_san = result[
            "best_san"
        ]

        is_best = result[
            "is_best"
        ]

        message = (
            f"Ваш ход: {played_san}\n"
            f"Лучше было: {best_san}"
        )

        if is_best:

            message += (
                "\n✓ Лучший ход!"
            )

        # ====================================================
        # ИГРА ЗАКОНЧИЛАСЬ
        # ====================================================

        if result["game_over"]:

            message += (
                "\n\n🏁 Партия закончена.\n"
                f"Результат: {game.get_result()}"
            )

            await query.edit_message_text(
                board_message(
                    game,
                    message
                ),
                reply_markup=create_board_keyboard(game)
            )

            game.close()

            del games[
                user_id
            ]

            return

        # ====================================================
        # ХОД КОМПЬЮТЕРА
        # ====================================================

        message += (
            "\n\n⏳ Ход компьютера..."
        )

        await query.edit_message_text(
            board_message(
                game,
                message
            ),
            reply_markup=create_board_keyboard(game)
        )

        computer_result = (
            game.make_computer_move()
        )

        if computer_result is not None:

            computer_san = (
                computer_result["san"]
            )

            message = (
                f"Ваш ход: {played_san}\n"
                f"Лучше было: {best_san}"
            )

            if is_best:

                message += (
                    "\n✓ Лучший ход!"
                )

            message += (
                f"\n\n🤖 Компьютер: "
                f"{computer_san}"
            )

        # ====================================================
        # ИГРА ЗАКОНЧИЛАСЬ ПОСЛЕ ХОДА КОМПЬЮТЕРА
        # ====================================================

        if game.is_game_over():

            message += (
                "\n\n🏁 Партия закончена.\n"
                f"Результат: {game.get_result()}"
            )

            await query.edit_message_text(
                board_message(
                    game,
                    message
                ),
                reply_markup=create_board_keyboard(game)
            )

            game.close()

            del games[
                user_id
            ]

            return

        # ====================================================
        # СЛЕДУЮЩИЙ ХОД
        # ====================================================

        message += "\n\nВаш ход."

        await query.edit_message_text(
            board_message(
                game,
                message
            ),
            reply_markup=create_board_keyboard(game)
        )

        return

    # ========================================================
    # НЕИЗВЕСТНАЯ КОМАНДА
    # ========================================================

    await query.answer()


# ============================================================
# ЗАПУСК БОТА
# ============================================================

def main():

    if not BOT_TOKEN:

        print(
            "ОШИБКА: переменная окружения "
            "BOT_TOKEN не задана."
        )

        return

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # Команда /start
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # --------------------------------------------------------
    # Нажатия на клетки доски
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            handle_square
        )
    )

    # --------------------------------------------------------
    # Текстовые сообщения
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text
        )
    )

    # --------------------------------------------------------
    # Запуск
    # --------------------------------------------------------

    print(
        "Telegram-бот запущен..."
    )

    application.run_polling()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()

