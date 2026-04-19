from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re

TOKEN = 'НОВЫЙ_ТОКЕН_СЮДА'
ALLOWED_USER_ID = 6595788533

def super_normalize(text: str) -> str:
    """Супер-нормализация — удаляет ЛЮБЫЕ символы между буквами"""
    text = text.lower()
    
    # 1. Замена спецсимволов на буквы
    leet_map = {
        '4': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's', '7': 't', '8': 'b',
        '6': 'g', '9': 'g', '2': 'z', '@': 'a', '$': 's', '!': 'i', '+': 't',
        '*': 'a', '#': 'a', '∆': 'a', '^': 'a', '&': 'a', '%': 'a', '?': 'a',
        '/': 'a', '\\': 'a', '|': 'a', '~': 'a', '`': 'a', "'": 'a', '"': 'a',
        ';': 'a', ':': 'a', ',': 'a', '.': 'a', '<': 'a', '>': 'a', '{': 'a',
        '}': 'a', '[': 'a', ']': 'a', '(': 'a', ')': 'a', '=': 'a', '-': 'a',
        '_': 'a', ' ': 'a', '№': 'a', '₽': 'a', '€': 'a', '$': 'a', '¢': 'a'
    }
    for old, new in leet_map.items():
        text = text.replace(old, new)
    
    # 2. Замена похожих букв
    similar = {
        'a': 'а', 'o': 'о', 'e': 'е', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х',
        'b': 'в', 'h': 'н', 'k': 'к', 'm': 'м', 't': 'т', 'u': 'и', 'i': 'и',
        'f': 'ф', 'n': 'н', 'p': 'п', 'q': 'г', 'w': 'в', 'z': 'з'
    }
    for eng, rus in similar.items():
        text = text.replace(eng, rus)
    
    # 3. Удаляем всё, кроме русских букв
    text = re.sub(r'[^а-яё]', '', text)
    
    # 4. Убираем повторы букв
    text = re.sub(r'(.)\1+', r'\1', text)
    
    return text

def contains_forbidden(text: str) -> bool:
    """Проверка на запрещённые слова"""
    normalized = super_normalize(text)
    
    # Если после нормализации текст стал слишком коротким или пустым
    if len(normalized) < 2:
        return False
    
    print(f"Нормализовано: '{normalized}' из '{text}'")
    
    # Точные совпадения
    exact_matches = ['фанат', 'фанаты', 'фан', 'фанат']
    for match in exact_matches:
        if match in normalized:
            return True
    
    # Шаблоны с регулярками
    patterns = [
        r'ф[ао]н[ао]т',      # фанат, фонат
        r'ф[ао]н[ао]ты',     # фанаты
        r'ф[ао]н',           # фан
        r'фнт',              # фнт (фанат без гласных)
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
    print("🚀 Бот запущен. Удаляет ЛЮБЫЕ варианты: Ф#н#т, Ф*н*т, Ф∆н∆т и т.д.")
    print(f"🛡️ Иммунитет у ID: {ALLOWED_USER_ID}")
    app.run_polling()

if __name__ == '__main__':
    main()
