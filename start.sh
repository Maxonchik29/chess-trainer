#!/bin/sh

echo "========================================"
echo "ЗАПУСК TELEGRAM BOT"
echo "========================================"

python -u telegram_bot.py &
BOT_PID=$!

echo "Telegram bot PID: $BOT_PID"

echo "========================================"
echo "ЗАПУСК FLASK"
echo "========================================"

gunicorn \
    --bind 0.0.0.0:10000 \
    --timeout 300 \
    web_server:app

kill $BOT_PID 2>/dev/null || true