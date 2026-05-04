import telebot
import time
import threading
from datetime import datetime

BOT_TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
bot = telebot.TeleBot(BOT_TOKEN)

MESSAGE_LIFETIME = 2 * 60  # 2 минуты

# Храним сообщения: {chat_id: [(msg_id, timestamp), ...]}
messages = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "✅ Бот запущен. Все сообщения старше 2 минут будут удаляться.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    msg_id = message.message_id
    now = time.time()
    
    # Сохраняем сообщение
    if chat_id not in messages:
        messages[chat_id] = []
    messages[chat_id].append((msg_id, now))
    
    # Сразу проверяем, не нужно ли удалить это сообщение (если вдруг оно уже старое)
    delete_old_messages(chat_id)

def delete_old_messages(chat_id):
    """Удаляет сообщения старше 2 минут"""
    if chat_id not in messages:
        return
    
    now = time.time()
    to_delete = []
    remaining = []
    
    for msg_id, timestamp in messages[chat_id]:
        if now - timestamp > MESSAGE_LIFETIME:
            to_delete.append(msg_id)
        else:
            remaining.append((msg_id, timestamp))
    
    messages[chat_id] = remaining
    
    # Удаляем каждое сообщение
    for msg_id in to_delete:
        try:
            bot.delete_message(chat_id, msg_id)
            print(f"🗑 Удалено сообщение {msg_id} в чате {chat_id}")
            time.sleep(0.2)  # защита от флуда
        except Exception as e:
            print(f"❌ Ошибка удаления {msg_id}: {e}")

def background_cleaner():
    """Фоновый процесс: каждые 5 секунд проверяет и удаляет"""
    while True:
        time.sleep(5)  # проверяем каждые 5 секунд
        for chat_id in list(messages.keys()):
            delete_old_messages(chat_id)

# Запускаем фоновую чистку
thread = threading.Thread(target=background_cleaner, daemon=True)
thread.start()

print("🚀 Бот запущен. Удаляет сообщения старше 2 минут.")
bot.infinity_polling()
