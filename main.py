import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

# ============================================================
# ЗАГРУЗКА ПЕРЕМЕННЫХ
# ============================================================

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "-1004426618768"))

if not BOT_TOKEN:
    print("❌ Токен не найден! Создайте .env с BOT_TOKEN")
    sys.exit(1)

# ============================================================
# НАСТРОЙКА ЛОГОВ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ============================================================
# ПРОКСИ (как в основном боте)
# ============================================================

PROXY = "socks5://127.0.0.1:3066"  # Порт Karing

# ============================================================
# СОЗДАНИЕ БОТА
# ============================================================

# Создаём сессию с прокси
session = AiohttpSession(proxy=PROXY, timeout=60)
bot = Bot(token=BOT_TOKEN, session=session)

dp = Dispatcher()

# Хранилище связей
forward_map = {}

# Список админов (замени на свои ID)
ADMIN_IDS = [
    8076284478,
    6036991812,
]


# ============================================================
# БЕЗОПАСНЫЕ ФУНКЦИИ
# ============================================================

def safe_get_user_id(message: Message):
    if message.from_user:
        return message.from_user.id
    return None


def safe_get_user_name(message: Message):
    if message.from_user:
        return message.from_user.full_name
    return "Неизвестный"


def safe_get_username(message: Message):
    if message.from_user and message.from_user.username:
        return f"@{message.from_user.username}"
    return "без юзернейма"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
# КОМАНДА /start
# ============================================================

@dp.message(Command('start'))
async def cmd_start(message: Message):
    user = message.from_user
    if user is None:
        await message.answer("❌ Не удалось определить пользователя.")
        return

    await message.answer(
        f"👋 Привет, {user.full_name}!\n\n"
        f"Я бот-пересыльщик. Я передаю ваши сообщения администраторам.\n"
        f"Если у вас есть вопросы — ближайший освободившийся администратор ответит вам, как только сможет.\n\n"
        f"📌 Напишите любое сообщение, и я перешлю его администрации."
    )


# ============================================================
# КОМАНДА /reply
# ============================================================

@dp.message(Command('reply'))
async def cmd_reply(message: Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещён. Только для администраторов.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "❌ Используйте: /reply <user_id> <текст>\n\n"
            "📌 Пример: /reply 123456789 Привет! Как дела?"
        )
        return

    try:
        target_id = int(parts[1])
        text = parts[2]
    except ValueError:
        await message.answer("❌ Неверный ID пользователя.")
        return

    try:
        await bot.send_message(
            chat_id=target_id,
            text=f"👤 <b>Ответ администратора:</b>\n\n{text}",
            parse_mode="HTML"
        )
        await message.answer(f"✅ Сообщение отправлено пользователю <code>{target_id}</code>", parse_mode="HTML")
        logger.info(f"Админ {user_id} ответил пользователю {target_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка ответа: {e}")


# ============================================================
# ПЕРЕСЫЛКА В ГРУППУ
# ============================================================

@dp.message(F.chat.type == ChatType.PRIVATE)
async def forward_to_group(message: Message):
    user_id = safe_get_user_id(message)
    if user_id is None:
        return

    if is_admin(user_id):
        return

    user_name = safe_get_user_name(message)
    username = safe_get_username(message)

    try:
        forwarded = await message.forward(chat_id=ADMIN_GROUP_ID)
        forward_map[forwarded.message_id] = user_id

        await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"👤 <b>Отправитель:</b> {user_name}\n"
                 f"🔖 <b>Юзернейм:</b> {username}\n"
                 f"🆔 <b>ID:</b> <code>{user_id}</code>",
            parse_mode="HTML"
        )

        await message.answer("📩 Ваше сообщение отправлено администрации. Ожидайте ответа.")
        logger.info(f"📨 Переслано от {user_name} (ID: {user_id})")

    except Exception as e:
        logger.error(f"❌ Ошибка пересылки: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# ============================================================
# ОТВЕТЫ ИЗ ГРУППЫ
# ============================================================

@dp.message(F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def reply_from_group(message: Message):
    original = message.reply_to_message
    if not original:
        return

    user_id = forward_map.get(original.message_id)

    if user_id is None:
        await message.reply(
            "⚠️ Не удалось найти пользователя.\n"
            "💡 Используйте /reply <id> <текст> в чате с ботом."
        )
        return

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"👤 <b>Ответ администратора:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        await message.reply("✅ Ответ отправлен пользователю.")
        logger.info(f"✅ Ответ отправлен пользователю {user_id}")

        if original.message_id in forward_map:
            del forward_map[original.message_id]

    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")
        logger.error(f"❌ Ошибка ответа: {e}")


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    logger.info("=" * 50)
    logger.info("📨 БОТ-ПЕРЕСЫЛЬЩИК ЗАПУЩЕН!")
    logger.info(f"📡 Группа: {ADMIN_GROUP_ID}")
    logger.info(f"🔗 Прокси: {PROXY}")
    logger.info("📡 Ожидание сообщений...")
    logger.info("=" * 50)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")