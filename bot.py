import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import asyncio

# Замените на токен вашего бота
BOT_TOKEN = "8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo"

# Словарь для хранения активных пользователей {user_id: True}
active_users = {}

# Команда /active <код>
async def active_command(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) == 2 and args[1] == "700900300":
        active_users[user_id] = True
        await message.answer("✅ Активация успешна! Теперь на любое слово я буду отвечать: Связано")
    else:
        await message.answer("❌ Неверный код активации.")

# Обработка всех сообщений (кроме /active)
async def handle_all_messages(message: Message):
    user_id = message.from_user.id

    if active_users.get(user_id, False):
        await message.answer("Связано")
    else:
        await message.answer("💎 Требуется оплата 100 звёзд. Используйте /active <код> для доступа.")

# Регистрация хендлеров
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(active_command, Command(commands=["active"]))
    dp.message.register(handle_all_messages)

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
