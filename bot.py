import telebot
import time
import threading
from datetime import datetime, timedelta

# токен
BOT_TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения сообщений: {chat_id: [(message_id, timestamp), ...]}
messages = {}

# Время жизни сообщения в секундах (3 минуты)
MESSAGE_LIFETIME = 3 * 60

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Бот запущен. Все сообщения старше 3 минут будут удалены.")

# Обработчик всех новых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    msg_id = message.message_id
    now = time.time()

    # Сохраняем сообщение в список чата
    if chat_id not in messages:
        messages[chat_id] = []
    messages[chat_id].append((msg_id, now))

    # Удаляем старые сообщения (в том числе только что добавленное, если оно старше лимита — для подстраховки)
    delete_old_messages(chat_id)

def delete_old_messages(chat_id):
    """Удаляет сообщения в указанном чате, которые старше MESSAGE_LIFETIME"""
    now = time.time()
    if chat_id not in messages:
        return

    to_delete = []
    remaining = []

    for msg_id, timestamp in messages[chat_id]:
        if now - timestamp > MESSAGE_LIFETIME:
            to_delete.append(msg_id)
        else:
            remaining.append((msg_id, timestamp))

    messages[chat_id] = remaining

    # Удаляем сообщения по одному (Telegram не позволяет массовое удаление старых сообщений одной командой)
    for msg_id in to_delete:
        try:
            bot.delete_message(chat_id, msg_id)
            time.sleep(0.3)  # чтобы не превысить лимиты API
        except Exception as e:
            # Ошибка, если сообщение уже удалено или нет прав
            pass

# Фоновая задача: каждые 10 секунд проверять все чаты
def periodic_cleanup():
    while True:
        time.sleep(10)
        # Копируем ключи, чтобы избежать изменения словаря во время итерации
        for chat_id in list(messages.keys()):
            delete_old_messages(chat_id)

# Если бот только запустился — можно очистить историю чата (опционально)
def clean_initial_messages(chat_id):
    """Удаляет все сообщения в чате, которые старше лимита (при запуске)"""
    try:
        # Получаем последние 100 сообщений (лимит API)
        updates = bot.get_updates(offset=-1, timeout=1)
        # Это неидеально, но для быстрого старта — можно пропустить
        # Или просто положиться на периодическую очистку
    except:
        pass

# Запуск фонового потока для чистки
thread = threading.Thread(target=periodic_cleanup, daemon=True)
thread.start()

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен. Удаляет сообщения старше 3 минут.")
    bot.infinity_polling()
