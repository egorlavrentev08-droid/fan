from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re

TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
ALLOWED_USER_ID = 6595788533

def god_mode_normalize(text: str) -> str:
    """Режим Бога — распознаёт абсолютно всё"""
    original = text
    text = text.lower()
    
    # 1. Удаляем все пробельные символы
    text = re.sub(r'[\s\n\r\t\v\f]', '', text)
    
    # 2. Замена буквы Ф
    f_variants = {
        '∅': 'ф', 'ø': 'ф', 'Ø': 'ф',
        'ф': 'ф', 'φ': 'ф', 'ϕ': 'ф', 'ph': 'ф',
    }
    for old, new in f_variants.items():
        text = text.replace(old, new)
    
    # 3. Греческие и математические символы
    symbol_map = {
        'α': 'а', 'β': 'в', 'γ': 'г', 'δ': 'д', 'Δ': 'д',
        'ε': 'е', 'ζ': 'з', 'η': 'н', 'θ': 'т', 'ι': 'и',
        'κ': 'к', 'λ': 'л', 'μ': 'м', 'ν': 'н', 'ξ': 'кс',
        'ο': 'о', 'π': 'п', 'ρ': 'р', 'σ': 'с', 'τ': 'т',
        'υ': 'у', 'φ': 'ф', 'χ': 'х', 'ψ': 'пс', 'ω': 'о',
        '∀': 'а', '∃': 'е', '∅': 'ф', 'ø': 'ф', 'Ø': 'ф',
        '∈': 'в', '∩': 'н', '∪': 'о', '⊥': 'т', '∠': 'у',
        '|-|': 'н', '|_|': 'п', '/\\': 'л', '\\/': 'л',
    }
    for old, new in sorted(symbol_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    
    # 4. Японский
    japanese_map = {
        'ファ': 'фа', 'フ': 'ф', 'ア': 'а', 'ナ': 'н', 'ン': 'н',
        'タ': 'т', 'ト': 'т', 'ふぁ': 'фа', 'ふ': 'ф',
    }
    for jap, rus in japanese_map.items():
        text = text.replace(jap, rus)
    
    # 5. Названия букв
    letter_names = {
        'эф': 'ф', 'еф': 'ф', 'ef': 'ф', 'а': 'а', 'эй': 'а',
        'эн': 'н', 'ен': 'н', 'тэ': 'т', 'те': 'т', 'ат': 'т',
    }
    for _ in range(3):
        for name, letter in letter_names.items():
            text = text.replace(name, letter)
    
    # 6. Leet
    leet = {
        '4': 'а', '3': 'е', '1': 'и', '0': 'о', '7': 'т',
        '@': 'а', '$': 'с', '#': '', '*': '', '∆': 'д',
    }
    for old, new in leet.items():
        text = text.replace(old, new)
    
    # 7. Латынь -> Кириллица
    eng_to_rus = {
        'f': 'ф', 'a': 'а', 'n': 'н', 't': 'т', 'p': 'п',
        'h': 'х', 'e': 'е', 'o': 'о', 'c': 'с', 'b': 'в',
        'k': 'к', 'm': 'м', 'i': 'и', 'u': 'у', 'g': 'г',
        'd': 'д', 'j': 'ж', 'l': 'л', 'r': 'р', 's': 'с',
        'v': 'в', 'w': 'в', 'x': 'кс', 'z': 'з'
    }
    for eng, rus in eng_to_rus.items():
        text = text.replace(eng, rus)
    
    # 8. Удаляем всё, кроме русских букв
    text = re.sub(r'[^а-яё]', '', text)
    
    # 9. Убираем повторы
    text = re.sub(r'(.)\1+', r'\1', text)
    
    print(f"Нормализация: '{original}' -> '{text}'")
    return text

def contains_forbidden(text: str) -> bool:
    normalized = god_mode_normalize(text)
    if len(normalized) < 2:
        return False
    targets = ['фанат', 'фанаты', 'фан']
    for target in targets:
        if target in normalized:
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
    print("🚀 Бот запущен")
    print(f"🛡️ Иммунитет у ID: {ALLOWED_USER_ID}")
    app.run_polling()

if __name__ == '__main__':
    main()
