#!/bin/sh

echo "========================================"
echo "ЗАПУСК TELEGRAM BOT"
echo "========================================"

echo "=== PROCESSES BEFORE BOT ==="

for dir in /proc/[0-9]*; do
    pid="${dir#/proc/}"
    if [ -f "$dir/cmdline" ]; then
        echo "PID $pid:"
        tr '\0' ' ' < "$dir/cmdline"
        echo
    fi
done

echo "========================================"

python -u telegram_bot.py &
BOT_PID=$!

echo "Telegram bot PID: $BOT_PID"

sleep 2

echo "=== PROCESSES AFTER BOT START ==="

for dir in /proc/[0-9]*; do
    pid="${dir#/proc/}"
    if [ -f "$dir/cmdline" ]; then
        echo "PID $pid:"
        tr '\0' ' ' < "$dir/cmdline"
        echo
    fi
done

echo "========================================"
echo "ЗАПУСК FLASK"
echo "========================================"

gunicorn \
    --bind 0.0.0.0:10000 \
    --timeout 300 \
    web_server:app

kill $BOT_PID 2>/dev/null || true