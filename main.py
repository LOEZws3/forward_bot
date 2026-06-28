import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ChatType
from dotenv import load_dotenv

# Загрузка переменных
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "-1004426618768"))

if not BOT_TOKEN:
    print("❌ Токен не найден! Создайте .env с BOT_TOKEN")
    sys.exit(1)

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Создание бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище связей (сообщение в группе → пользователь)
forward_map = {}


# ============================================================
# 📨 ПЕРЕСЫЛКА СООБЩЕНИЙ В ГРУППУ
# ============================================================

@dp.message(F.chat.type == ChatType.PRIVATE)
async def forward_to_group(message: Message):
    """
    Пересылает все сообщения от пользователей в группу админов
    """
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"

    try:
        # Пересылаем сообщение в группу
        forwarded = await message.forward(chat_id=ADMIN_GROUP_ID)

        # Сохраняем связь: ID пересланного сообщения → ID пользователя
        forward_map[forwarded.message_id] = user_id

        # Отправляем информацию об отправителе
        await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"👤 <b>Отправитель:</b> {user_name}\n"
                 f"🔖 <b>Юзернейм:</b> {username}\n"
                 f"🆔 <b>ID:</b> <code>{user_id}</code>",
            parse_mode="HTML"
        )

        # Уведомляем пользователя
        await message.answer("📩 Ваше сообщение отправлено администрации. Ожидайте ответа.")

        logger.info(f"📨 Переслано сообщение от {user_name} (ID: {user_id})")

    except Exception as e:
        logger.error(f"❌ Ошибка пересылки: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# ============================================================
# 💬 ОТВЕТЫ АДМИНОВ ИЗ ГРУППЫ
# ============================================================

@dp.message(F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def reply_from_group(message: Message):
    """
    Если админ отвечает на пересланное сообщение, бот отправляет ответ пользователю
    """
    original = message.reply_to_message

    if not original:
        return

    # Проверяем, есть ли связь для этого сообщения
    user_id = forward_map.get(original.message_id)

    if user_id:
        try:
            # Отправляем ответ пользователю
            await bot.send_message(
                chat_id=user_id,
                text=f"👤 <b>Ответ администратора:</b>\n\n{message.text}",
                parse_mode="HTML"
            )

            # Подтверждение в группе
            await message.reply("✅ Ответ отправлен пользователю.")
            logger.info(f"✅ Ответ отправлен пользователю {user_id}")

            # Удаляем связь (чтобы не отвечать дважды)
            del forward_map[original.message_id]

        except Exception as e:
            await message.reply(f"❌ Ошибка при отправке: {e}")
            logger.error(f"❌ Ошибка ответа: {e}")
    else:
        await message.reply(
            "⚠️ Не удалось найти пользователя для этого сообщения.\n"
            "Возможно, связь потерялась после перезапуска."
        )


# ============================================================
# 🚀 ЗАПУСК БОТА
# ============================================================

async def main():
    logger.info("=" * 50)
    logger.info("📨 БОТ-ПЕРЕСЫЛЬЩИК ЗАПУЩЕН!")
    logger.info(f"📡 Группа для пересылки: {ADMIN_GROUP_ID}")
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