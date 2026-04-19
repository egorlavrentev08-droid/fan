from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re

TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
ALLOWED_USER_ID = 6595788533

def smart_normalize(text: str) -> str:
    """Умная нормализация — распознаёт любые обфускации"""
    text = text.lower()
    
    # 1. Замена цифр и символов на буквы
    leet_map = {
        '4': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's', '7': 't', '8': 'b',
        '6': 'g', '9': 'g', '2': 'z', '@': 'a', '$': 's', '!': 'i', '+': 't',
        '*': 'x', '#': 'h', '&': 'e', '%': 'o', '?': 'q', '/': 'i', '\\': 'i'
    }
    for old, new in leet_map.items():
        text = text.replace(old, new)
    
    # 2. Замена похожих букв (латиница -> кириллица)
    similar = {
        'a': 'а', 'o': 'о', 'e': 'е', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х',
        'b': 'в', 'h': 'н', 'k': 'к', 'm': 'м', 't': 'т', 'u': 'и', 'i': 'и'
    }
    for eng, rus in similar.items():
        text = text.replace(eng, rus)
    
    # 3. Удаление всех символов, кроме букв
    text = re.sub(r'[^а-яёa-z]', '', text)
    
    # 4. Удаление повторов букв (фффанаат -> фанат)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)  # 3+ повторов -> 2
    text = re.sub(r'(.)\1{1,}', r'\1', text)     # 2 повтора -> 1
    
    return text

def contains_forbidden(text: str) -> bool:
    """Проверяет, содержит ли текст запрещённое слово"""
    normalized = smart_normalize(text)
    
    # Базовые шаблоны (распознают почти всё)
    patterns = [
        r'ф[ао]н[ао]т',      # фанат, фонот, фонат
        r'ф[ао]н[ао]ты',     # фанаты
        r'ф[ао]н',           # фан
        r'[fр][aао][nн]',    # fan, фан, fан
        r'[fр][aао][nн][aао][tт]',  # fanat, фанат
        r'[fр][aао][nн][aао][tт]ы', # fanaty, фанаты
        r'p[hн][aао][nн]',   # phan
        r'p[hн][aао][nн][aао][tт]', # phanat
    ]
    
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True
    return False

async def check_and_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ALLOWED_USER_ID:
        return
    if update.message.from_user.is_bot:
        return

    text = update.message.text or ''
    
    if contains_forbidden(text):
        try:
            await update.message.delete()
            print(f"✅ УДАЛЕНО: {text}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_and_delete))
    print("🚀 Бот запущен. Удаляет ВСЕ варианты написания fan/фанат")
    print(f"🛡️ Иммунитет у ID: {ALLOWED_USER_ID}")
    app.run_polling()

if __name__ == '__main__':
    main()
