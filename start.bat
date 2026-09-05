@echo off
chcp 65001 >nul
title Telegram Bot
color 0A

echo.
echo ╔═══════════════════════════════════════╗
echo ║     🤖 ЗАПУСК TELEGRAM БОТА        ║
echo ║                                     ║
echo ╚═══════════════════════════════════════╝
echo.

echo [1/2] Активируем виртуальное окружение...
call .venv\Scripts\activate
echo ✅ Готово!
echo.

echo [2/2] Запускаем бота...
echo.
echo ═══════════════════════════════════════════════════════
echo.

python main.py

echo.
echo ═══════════════════════════════════════════════════════
echo.
echo ❌ Бот остановлен.
echo.

pause