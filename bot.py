from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'  # Замените на новый токен!
ALLOWED_USER_ID = 6595788533

# Таблица замен похожих букв (латиница -> кириллица)
REPLACEMENTS = {
    'a': 'а', 'o': 'о', 'e': 'е', 'p': 'р', 'c': 'с',
    'y': 'у', 'x': 'х', 'b': 'в', 'h': 'н', 'k': 'к',
    'm': 'м', 't': 'т', 'a': 'а', 'u': 'и', 'i': 'и'
}

def normalize_text(text: str) -> str:
    """Приводит текст к единому виду (кириллица в нижнем регистре)"""
    text = text.lower()
    # Заменяем английские буквы на русские
    for eng, rus in REPLACEMENTS.items():
        text = text.replace(eng, rus)
    return text

FORBIDDEN_WORDS = ['фанат', 'фанаты', 'фан']

async def check_and_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ALLOWED_USER_ID:
        return
    if update.message.from_user.is_bot:
        return

    text = update.message.text or ''
    normalized = normalize_text(text)

    if any(word in normalized for word in FORBIDDEN_WORDS):
        try:
            await update.message.delete()
            print(f"Удалено: {text} (нормализовано: {normalized})")
        except Exception as e:
            print(f"Ошибка удаления: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_and_delete))
    print("Бот запущен. Ловит обходы с английскими буквами!")
    app.run_polling()

if __name__ == '__main__':
    main()
