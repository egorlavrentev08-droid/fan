import telebot
import time
import threading

# токен
BOT_TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения сообщений: {chat_id: [(message_id, timestamp), ...]}
messages = {}

# Время жизни сообщения в секундах (2 минуты)
MESSAGE_LIFETIME = 2 * 60  # 120 секунд

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Бот запущен. Все сообщения старше 2 минут будут удалены.")

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

    # Удаляем старые сообщения
    delete_old_messages(chat_id)

def delete_old_messages(chat_id):
    """Удаляет сообщения в указанном чате, которые старше 2 минут"""
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

    # Удаляем сообщения
    for msg_id in to_delete:
        try:
            bot.delete_message(chat_id, msg_id)
            time.sleep(0.3)
        except Exception as e:
            pass

# Фоновая задача: каждые 10 секунд проверять все чаты
def periodic_cleanup():
    while True:
        time.sleep(10)
        for chat_id in list(messages.keys()):
            delete_old_messages(chat_id)

# Запуск фонового потока
thread = threading.Thread(target=periodic_cleanup, daemon=True)
thread.start()

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен. Удаляет сообщения старше 2 минут.")
    bot.infinity_polling()
