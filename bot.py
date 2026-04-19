from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
ALLOWED_USER_ID = 6595788533  # Этот ID не трогаем

# Слова для поиска (все в нижнем регистре)
FORBIDDEN_WORDS = ['фанат', 'фанаты', 'фан']

async def check_and_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Не удаляем сообщения от разрешённого пользователя
    if update.message.from_user.id == ALLOWED_USER_ID:
        return

    # Не удаляем сообщения от ботов
    if update.message.from_user.is_bot:
        return

    text = update.message.text or ''
    text_lower = text.lower()

    # Проверяем, есть ли хоть одно запрещённое слово
    if any(word in text_lower for word in FORBIDDEN_WORDS):
        try:
            await update.message.delete()
            print(f"Удалено сообщение от {update.message.from_user.id}: {text}")
        except Exception as e:
            print(f"Не удалось удалить: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_and_delete))
    print("Бот запущен. Удаляет сообщения со словами: фанат, фанаты, фан")
    print(f"Пользователь {ALLOWED_USER_ID} имеет иммунитет")
    app.run_polling()

if __name__ == '__main__':
    main()
