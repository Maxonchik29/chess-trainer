
import logging
import os

import chess
import psycopg2

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

WEB_APP_URL = "https://chess-trainer-3cni.onrender.com"


# ============================================================
# АДМИНИСТРАТОР
# ============================================================

# В Render нужно будет добавить:
#
# ADMIN_TELEGRAM_ID = твой Telegram ID
#
# Например:
#
# ADMIN_TELEGRAM_ID=123456789
#
# Если переменная не задана, /stats будет недоступна.

ADMIN_TELEGRAM_ID = os.environ.get(
    "ADMIN_TELEGRAM_ID"
)


# ============================================================
# БАЗА ДАННЫХ
# ============================================================

def get_db_connection():

    database_url = os.environ.get(
        "DATABASE_URL"
    )

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL не задан."
        )

    return psycopg2.connect(
        database_url
    )


# ============================================================
# БЕЗОПАСНОЕ ПРЕОБРАЗОВАНИЕ В INT
# ============================================================

def safe_int(value):

    if value is None:

        return None

    try:

        return int(value)

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# СТАТИСТИКА TELEGRAM-ПОЛЬЗОВАТЕЛЯ
# ============================================================

def update_bot_user(
    telegram_user,
    count_start=False,
    count_game=False
):
    if not telegram_user:
        return False

    telegram_id = telegram_user.get("id")
    if not telegram_id:
        return False

    telegram_id = safe_int(telegram_id)
    if telegram_id is None:
        return False

    username = telegram_user.get("username")
    first_name = telegram_user.get("first_name")

    conn = None

    try:
        conn = get_db_connection()

        with conn:
            with conn.cursor() as cur:

                # =====================================================
                # СОЗДАЁМ ПОЛЬЗОВАТЕЛЯ, ЕСЛИ ЕГО ЕЩЁ НЕТ
                # =====================================================

                cur.execute(
                    """
                    INSERT INTO public.bot_users (
                        telegram_id,
                        username,
                        first_name
                    )
                    VALUES (
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (telegram_id)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_seen = NOW()
                    """,
                    (
                        telegram_id,
                        username,
                        first_name
                    )
                )

                # =====================================================
                # УВЕЛИЧИВАЕМ СЧЁТЧИКИ
                # =====================================================

                updates = [
                    "last_seen = NOW()"
                ]

                if count_start:
                    updates.append(
                        "start_count = start_count + 1"
                    )

                if count_game:
                    updates.append(
                        "games_count = games_count + 1"
                    )

                cur.execute(
                    f"""
                    UPDATE public.bot_users
                    SET
                        {", ".join(updates)}
                    WHERE telegram_id = %s
                    """,
                    (telegram_id,)
                )

                return True

    except Exception as error:
        print(
            "BOT STATS ERROR:",
            repr(error)
        )
        return False

    finally:
        if conn:
            conn.close()

# ============================================================
# ПРОВЕРКА АДМИНИСТРАТОРА
# ============================================================

def is_admin(user_id):

    if not ADMIN_TELEGRAM_ID:

        return False

    admin_id = safe_int(
        ADMIN_TELEGRAM_ID
    )

    if admin_id is None:

        return False

    return int(user_id) == admin_id


# ============================================================
# ПОЛУЧИТЬ СТАТИСТИКУ
# ============================================================

def get_bot_statistics():

    conn = None

    try:

        conn = get_db_connection()

        with conn:

            with conn.cursor() as cur:

                # ====================================================
                # ОБЩАЯ СТАТИСТИКА
                # ====================================================

                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS total_users,

                        COUNT(*) FILTER (
                            WHERE first_seen >= CURRENT_DATE
                        ) AS today_users,

                        COUNT(*) FILTER (
                            WHERE first_seen >= NOW() - INTERVAL '7 days'
                        ) AS week_users,

                        COUNT(*) FILTER (
                            WHERE first_seen >= NOW() - INTERVAL '30 days'
                        ) AS month_users,

                        COALESCE(
                            SUM(start_count),
                            0
                        ) AS total_starts,

                        COALESCE(
                            SUM(games_count),
                            0
                        ) AS total_games,

                        COALESCE(
                            SUM(analyses_count),
                            0
                        ) AS total_analyses,

                        COALESCE(
                            SUM(mini_app_opens),
                            0
                        ) AS total_mini_app_opens

                    FROM public.bot_users
                    """
                )

                row = cur.fetchone()

                if not row:

                    return None

                return {

                    "total_users":
                        row[0],

                    "today_users":
                        row[1],

                    "week_users":
                        row[2],

                    "month_users":
                        row[3],

                    "total_starts":
                        row[4],

                    "total_games":
                        row[5],

                    "total_analyses":
                        row[6],

                    "total_mini_app_opens":
                        row[7],
                }

    finally:

        if conn:

            conn.close()


# ============================================================
# ЛОГИ
# ============================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)


# ============================================================
# ИГРЫ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================

games = {}

# user_id -> selected square


# ============================================================
# ОСНОВНАЯ КЛАВИАТУРА
# ============================================================

main_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "♟ Играть с компьютером",
                web_app=WebAppInfo(
                    url=WEB_APP_URL
                )
            )
        ]
    ]
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

def create_board_keyboard(
    game,
    selected_square=None
):

    board = game.get_board()

    keyboard = []

    # ========================================================
    # ВЕРХНИЕ КООРДИНАТЫ
    # ========================================================

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

    # ========================================================
    # ДОСКА
    # ========================================================

    for rank in range(
        7,
        -1,
        -1
    ):

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

            # ------------------------------------------------
            # Выбранная клетка
            # ------------------------------------------------

            if selected_square == square:

                text = "🟨" + text

            # ------------------------------------------------
            # Callback
            # ------------------------------------------------

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

        # ----------------------------------------------------
        # Номер горизонтали справа
        # ----------------------------------------------------

        row.append(

            InlineKeyboardButton(
                str(rank + 1),
                callback_data="noop"
            )
        )

        keyboard.append(
            row
        )

    # ========================================================
    # НИЖНИЕ КООРДИНАТЫ
    # ========================================================

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

    # ========================================================
    # НОВАЯ ПАРТИЯ
    # ========================================================

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

    text = (
        "♟ Chess Trainer\n\n"
    )

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

    user = update.effective_user

    # ========================================================
    # СТАТИСТИКА
    # ========================================================

    if user:

        update_bot_user(
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
            },
            count_start=True
        )

    # ========================================================
    # ПРИВЕТСТВИЕ
    # ========================================================

    await update.message.reply_text(

        "♟ Chess Trainer\n\n"
        "Добро пожаловать!\n\n"
        "Нажми «♟ Играть с компьютером», "
        "чтобы начать партию.",

        reply_markup=main_keyboard,
    )


# ============================================================
# /stats
# ============================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user is None:

        return

    # ========================================================
    # ПРОВЕРКА АДМИНИСТРАТОРА
    # ========================================================

    if not is_admin(
        user.id
    ):

        await update.message.reply_text(
            "⛔ Команда недоступна."
        )

        return

    # ========================================================
    # ПОЛУЧАЕМ СТАТИСТИКУ
    # ========================================================

    try:

        statistics = (
            get_bot_statistics()
        )

    except Exception as error:

        print(
            "STATS ERROR:",
            repr(error)
        )

        await update.message.reply_text(
            "❌ Не удалось получить статистику."
        )

        return

    if not statistics:

        await update.message.reply_text(
            "Статистика пока недоступна."
        )

        return

    # ========================================================
    # ФОРМИРУЕМ ОТВЕТ
    # ========================================================

    text = (

        "📊 Статистика Chess Trainer\n\n"

        f"👥 Всего пользователей: "
        f"{statistics['total_users']}\n"

        f"🆕 Новых сегодня: "
        f"{statistics['today_users']}\n"

        f"📅 Новых за 7 дней: "
        f"{statistics['week_users']}\n"

        f"🗓 Новых за 30 дней: "
        f"{statistics['month_users']}\n\n"

        f"▶️ Запусков /start: "
        f"{statistics['total_starts']}\n"

        f"♟ Начатых партий: "
        f"{statistics['total_games']}\n"

        f"📊 Анализов PGN: "
        f"{statistics['total_analyses']}\n"

        f"📱 Открытий Mini App: "
        f"{statistics['total_mini_app_opens']}"
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# НОВАЯ ИГРА
# ============================================================

async def new_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    # ========================================================
    # СТАТИСТИКА
    # ========================================================

    update_bot_user(
        {
            "id": update.effective_user.id,
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
        },
        count_game=True
    )

    # ========================================================
    # ЗАКРЫВАЕМ СТАРУЮ ИГРУ
    # ========================================================

    old_game = games.get(
        user_id
    )

    if old_game is not None:

        old_game.close()

    # ========================================================
    # СОЗДАЁМ НОВУЮ ИГРУ
    # ========================================================

    game = ChessGame(
        player_color=chess.WHITE
    )

    games[user_id] = game

    # ========================================================
    # СБРАСЫВАЕМ ВЫБРАННУЮ ФИГУРУ
    # ========================================================

    context.user_data.pop(
        "selected_square",
        None
    )

    # ========================================================
    # ПОКАЗЫВАЕМ ДОСКУ
    # ========================================================

    await update.message.reply_text(

        board_message(game),

        reply_markup=create_board_keyboard(
            game
        )
    )


# ============================================================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        update.message.text.strip()
    )

    # ========================================================
    # НОВАЯ ИГРА
    # ========================================================

    if text == "♟ Играть с компьютером":

        await new_game(
            update,
            context
        )

        return

    # ========================================================
    # ОБЫЧНЫЙ ТЕКСТ
    # ========================================================

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

        # ----------------------------------------------------
        # СТАТИСТИКА
        # ----------------------------------------------------

        update_bot_user(
            {
                "id": query.from_user.id,
                "username": query.from_user.username,
                "first_name": query.from_user.first_name,
            },
            count_game=True
        )

        await query.edit_message_text(

            board_message(game),

            reply_markup=create_board_keyboard(
                game
            )
        )

        return

    # ========================================================
    # ПЕРВЫЙ КЛИК — SELECT
    # ========================================================

    if query.data.startswith(
        "select:"
    ):

        square_name = (
            query.data.split(
                ":",
                1
            )[1]
        )

        square = chess.parse_square(
            square_name
        )

        board = game.get_board()

        # ----------------------------------------------------
        # Проверяем ход игрока
        # ----------------------------------------------------

        if not game.is_player_turn():

            await query.answer(
                "Сейчас ход компьютера.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # Проверяем фигуру
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Показываем выбранную клетку
        # ----------------------------------------------------

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

    if query.data.startswith(
        "move:"
    ):

        parts = query.data.split(
            ":"
        )

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
        # ПРОВЕРЯЕМ ХОД ИГРОКА
        # ====================================================

        if not game.is_player_turn():

            await query.answer(
                "Сейчас ход компьютера.",
                show_alert=True
            )

            return

        # ====================================================
        # ТА ЖЕ КЛЕТКА
        # ====================================================

        if from_square == to_square:

            await query.answer(
                "Выбор отменён."
            )

            await query.edit_message_text(

                board_message(game),

                reply_markup=create_board_keyboard(
                    game
                )
            )

            return

        # ====================================================
        # СОЗДАЁМ ХОД
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
        # ПРОВЕРЯЕМ ЛЕГАЛЬНОСТЬ
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

            reply_markup=create_board_keyboard(
                game
            )
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

                reply_markup=create_board_keyboard(
                    game
                )
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
                f"Результат: "
                f"{game.get_result()}"
            )

            await query.edit_message_text(

                board_message(
                    game,
                    message
                ),

                reply_markup=create_board_keyboard(
                    game
                )
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

            reply_markup=create_board_keyboard(
                game
            )
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
        # ИГРА ЗАКОНЧИЛАСЬ ПОСЛЕ КОМПЬЮТЕРА
        # ====================================================

        if game.is_game_over():

            message += (

                "\n\n🏁 Партия закончена.\n"
                f"Результат: "
                f"{game.get_result()}"
            )

            await query.edit_message_text(

                board_message(
                    game,
                    message
                ),

                reply_markup=create_board_keyboard(
                    game
                )
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

            reply_markup=create_board_keyboard(
                game
            )
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

    # ========================================================
    # /start
    # ========================================================

    application.add_handler(

        CommandHandler(
            "start",
            start
        )
    )

    # ========================================================
    # /stats
    # ========================================================

    application.add_handler(

        CommandHandler(
            "stats",
            stats
        )
    )

    # ========================================================
    # НАЖАТИЯ НА КЛЕТКИ
    # ========================================================

    application.add_handler(

        CallbackQueryHandler(
            handle_square
        )
    )

    # ========================================================
    # ТЕКСТОВЫЕ СООБЩЕНИЯ
    # ========================================================

    application.add_handler(

        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text
        )
    )

    # ========================================================
    # ЗАПУСК
    # ========================================================

    print(
        "Telegram-бот запущен..."
    )

    application.run_polling()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
