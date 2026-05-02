from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
from difflib import SequenceMatcher

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
    
    # 8. Исправление типичных замен гласных
    vowel_fixes = {
        'о': 'а',  # фонат -> фанат
        'у': 'а',  # фунат -> фанат
        'ы': 'и',  # фынат -> финат
        'е': 'и',  # фенат -> финат
        'ю': 'у',  # фюнат -> фунат -> фанат
        'я': 'а',  # фянат -> фанат
    }
    for old, new in vowel_fixes.items():
        text = text.replace(old, new)
    
    # 9. Удаляем всё, кроме русских букв
    text = re.sub(r'[^а-яё]', '', text)
    
    # 10. Убираем повторы
    text = re.sub(r'(.)\1+', r'\1', text)
    
    print(f"Нормализация: '{original}' -> '{text}'")
    return text

def fuzzy_contains_forbidden(text: str) -> bool:
    """Нечёткий поиск запрещённых слов"""
    normalized = god_mode_normalize(text)
    if len(normalized) < 2:
        return False
    
    targets = ['фанат', 'фанаты', 'фан']
    
    # Прямые вхождения
    for target in targets:
        if target in normalized:
            print(f"✅ Прямое совпадение: {target}")
            return True
    
    # Нечёткое совпадение для каждого целевого слова
    for target in targets:
        target_len = len(target)
        
        # Проверяем все подстроки подходящей длины
        for i in range(len(normalized) - target_len + 1):
            substring = normalized[i:i+target_len]
            ratio = SequenceMatcher(None, substring, target).ratio()
            if ratio > 0.7:  # 70% схожести достаточно
                print(f"⚠️ Нечёткое совпадение: '{substring}' ≈ '{target}' (схожесть {ratio:.2f})")
                return True
        
        # Также проверяем более длинные строки (если вставлены лишние буквы)
        for i in range(len(normalized) - target_len - 2 + 1):
            if i + target_len + 2 <= len(normalized):
                substring = normalized[i:i+target_len+2]
                ratio = SequenceMatcher(None, substring, target).ratio()
                if ratio > 0.65:
                    print(f"⚠️ Нечёткое совпадение (с лишними буквами): '{substring}' ≈ '{target}' (схожесть {ratio:.2f})")
                    return True
    
    # Особая проверка: наличие букв ф, а, н в правильном порядке
    # Ищем паттерн: ф, потом а, потом н
    pattern_fan = r'ф[аоуыэяюие]*[аоуыэяюие]?н'
    if re.search(pattern_fan, normalized):
        print(f"⚠️ Совпадение по паттерну 'ф*н': {re.search(pattern_fan, normalized).group()}")
        return True
    
    return False

async def check_and_delete_message(message, update: Update, context: ContextTypes.DEFAULT_TYPE, event_type: str = "message"):
    """Общая функция для проверки и удаления сообщения"""
    if message.from_user.id == ALLOWED_USER_ID:
        return
    if message.from_user.is_bot:
        return
    
    text = message.text or ''
    if fuzzy_contains_forbidden(text):
        try:
            await message.delete()
            print(f"✅ УДАЛЕНО ({event_type}): {text}")
        except Exception as e:
            print(f"❌ Ошибка при удалении ({event_type}): {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка новых сообщений"""
    if update.message:
        await check_and_delete_message(update.message, update, context, "new")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отредактированных сообщений"""
    if update.edited_message:
        await check_and_delete_message(update.edited_message, update, context, "edited")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Обработчик новых сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
        handle_message
    ))
    
    # Обработчик отредактированных сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.UpdateType.EDITED_MESSAGE,
        handle_edited_message
    ))
    
    print("🚀 Бот запущен")
    print(f"🛡️ Иммунитет у ID: {ALLOWED_USER_ID}")
    print("📝 Проверяются и новые, и отредактированные сообщения")
    print("🔍 Используется нечёткий поиск (фонат, фунат и другие вариации тоже будут удаляться)")
    app.run_polling()

if __name__ == '__main__':
    main()        '4': 'а', '3': 'е', '1': 'и', '0': 'о', '7': 'т',
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

async def check_and_delete_message(message, update: Update, context: ContextTypes.DEFAULT_TYPE, event_type: str = "message"):
    """Общая функция для проверки и удаления сообщения"""
    if message.from_user.id == ALLOWED_USER_ID:
        return
    if message.from_user.is_bot:
        return
    
    text = message.text or ''
    if contains_forbidden(text):
        try:
            await message.delete()
            print(f"✅ УДАЛЕНО ({event_type}): {text}")
        except Exception as e:
            print(f"❌ Ошибка при удалении ({event_type}): {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка новых сообщений"""
    if update.message:
        await check_and_delete_message(update.message, update, context, "new")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отредактированных сообщений"""
    if update.edited_message:
        await check_and_delete_message(update.edited_message, update, context, "edited")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Обработчик новых сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
        handle_message
    ))
    
    # Обработчик отредактированных сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.UpdateType.EDITED_MESSAGE,
        handle_edited_message
    ))
    
    print("🚀 Бот запущен")
    print(f"🛡️ Иммунитет у ID: {ALLOWED_USER_ID}")
    print("📝 Проверяются и новые, и отредактированные сообщения")
    app.run_polling()

if __name__ == '__main__':
    main()
