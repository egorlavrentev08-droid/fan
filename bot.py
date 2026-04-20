from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re

TOKEN = '8248495057:AAF8D20-moOxOSEZVsTzuDjpVNMUvSQqgWo'
ALLOWED_USER_ID = 6595788533

def god_mode_normalize(text: str) -> str:
    """Режим Бога — распознаёт абсолютно всё: греческий, матсимволы, японский, leet"""
    original = text
    text = text.lower()
    
    # 1. Удаляем все пробельные символы (включая переносы строк)
    text = re.sub(r'[\s\n\r\t\v\f]', '', text)
    
    # 2. Греческие буквы и математические символы -> русские
    greek_map = {
        # Греческие буквы
        'α': 'а', 'ά': 'а', 'ὰ': 'а', 'ἀ': 'а', 'ἁ': 'а',
        'β': 'в', 'γ': 'г', 'δ': 'д', 'Δ': 'д',
        'ε': 'е', 'έ': 'е', 'ὲ': 'е', 'ϵ': 'е',
        'ζ': 'з', 'η': 'н', 'ή': 'н', 'ὴ': 'н', 'ἠ': 'н',
        'θ': 'т', 'ϑ': 'т', 'ι': 'и', 'ί': 'и', 'ὶ': 'и',
        'κ': 'к', 'ϰ': 'к', 'λ': 'л', 'μ': 'м',
        'ν': 'н', 'ξ': 'кс', 'ο': 'о', 'ό': 'о', 'ὸ': 'о',
        'π': 'п', 'ϖ': 'п', 'ρ': 'р', 'ϱ': 'р',
        'σ': 'с', 'ς': 'с', 'τ': 'т', 'υ': 'у', 'ύ': 'у', 'ὺ': 'у',
        'φ': 'ф', 'ϕ': 'ф', 'χ': 'х', 'ψ': 'пс', 'ω': 'о', 'ώ': 'о', 'ὼ': 'о',
        # Математические символы
        '∀': 'а',           # for all -> A
        '∃': 'е',           # exists -> E
        '∄': 'е', 
        '∈': 'в',           # element of -> B
        '∉': 'в',
        '∋': 'в',
        '∌': 'в',
        '∩': 'п',           # intersection
        '∪': 'о',           # union
        '⊂': 'п',
        '⊃': 'п',
        '⊆': 'п',
        '⊇': 'п',
        '⊕': 'о',
        '⊗': 'о',
        '⊥': 'т',
        '⊤': 'т',
        '∠': 'у',
        '∡': 'у',
        '∞': 'в',
        '✓': 'в',
        '★': 'з',
        '☆': 'з',
        '❤': 'с',
        '♪': 'н',
        '♫': 'н',
        # Символы, имитирующие буквы
        '|-|': 'н',         # H
        '|_|': 'п',         # П
        '|': '',            # палка
        '-': '',            # тире
        '_': '',            # подчёркивание
        '[': '', ']': '',
        '{': '', '}': '',
        '(': '', ')': '',
        '/\\': 'л',         # Лямбда-подобное
        '\\/': 'л',
    }
    
    # Замена комбинаций (длинные первыми)
    for old, new in sorted(greek_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    
    # 3. Японская катакана/хирагана
    japanese_map = {
        'ファ': 'фа', 'フ': 'ф', 'ア': 'а', 'ナ': 'н', 'ン': 'н',
        'タ': 'т', 'ト': 'т', 'ふぁ': 'фа', 'ふ': 'ф', 'あ': 'а',
        'な': 'н', 'ん': 'н', 'た': 'т', 'と': 'т',
    }
    for jap, rus in japanese_map.items():
        text = text.replace(jap, rus)
    
    # 4. Названия букв
    letter_names = {
        'эф': 'ф', 'еф': 'ф', 'ef': 'ф', 'eff': 'ф',
        'а': 'а', 'эй': 'а', 'ay': 'а', 'a': 'а',
        'эн': 'н', 'ен': 'н', 'en': 'н', 'enn': 'н',
        'тэ': 'т', 'те': 'т', 'ат': 'т', 'эт': 'т', 'tee': 'т', 'tea': 'т', 't': 'т',
        'пи': 'п', 'ро': 'р', 'каппа': 'к', 'дельта': 'д', 'ламбда': 'л',
    }
    for _ in range(3):
        for name, letter in letter_names.items():
            text = text.replace(name, letter)
    
    # 5. Leet-speak и спецсимволы
    leet = {
        '4': 'а', '3': 'е', '1': 'и', '0': 'о', '5': 'с', '7': 'т',
        '8': 'в', '6': 'г', '9': 'г', '2': 'з', '@': 'а', '$': 'с',
        '!': 'и', '+': 'т', '#': '', '*': '', '∆': 'д', '^': '',
        '&': 'и', '?': '', '/': '', '\\': '', '|': '', '~': '',
        '`': '', "'": '', '"': '', ';': '', ':': '', ',': '',
        '.': '', '<': '', '>': '', '=': '', '€': 'е', '£': 'л',
        '¥': 'й', '©': 'с', '®': 'р', '™': 'т',
    }
    for old, new in leet.items():
        text = text.replace(old, new)
    
    # 6. Латынь -> Кириллица
    eng_to_rus = {
        'f': 'ф', 'a': 'а', 'n': 'н', 't': 'т', 'y': 'ы',
        'p': 'п', 'h': 'х', 'e': 'е', 'o': 'о', 'c': 'с',
        'b': 'в', 'k': 'к', 'm': 'м', 'i': 'и', 'u': 'у',
        'g': 'г', 'd': 'д', 'j': 'ж', 'l': 'л', 'q': 'к',
        'r': 'р', 's': 'с', 'v': 'в', 'w': 'в', 'x': 'кс', 'z': 'з'
    }
    for eng, rus in eng_to_rus.items():
        text = text.replace(eng, rus)
    
    # 7. Удаляем всё, кроме русских букв
    text = re.sub(r'[^а-яё]', '', text)
    
    # 8. Убираем повторы
    text = re.sub(r'(.)\1+', r'\1', text)
    
    print(f"Нормализация: '{original}' -> '{text}'")
    return text

def contains_forbidden(text: str) -> bool:
    """Проверка на запрещённые слова"""
    normalized = god_mode_normalize(text)
    
    if len(normalized) < 2:
        return False
    
    targets = ['фанат', 'фанаты', 'фан', 'фанатик', 'фанатка']
    
    for target in targets:
        if target in normalized:
            return True
    
    patterns = [r'фнт', r'ф[ао]н', r'ф[ао]н[ао]т', r'ф[ао]н[ао]ты']
    
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
    print("🚀 Бот запущен в режиме GOD MODE")
    print(f"🛡️ Иммунитет у ID: {ALLOWED_USER_ID}")
    print("📋 Распознаёт: греческий, матсимволы, японский, leet, названия букв, переносы строк")
    app.run_polling()

if __name__ == '__main__':
    main()
