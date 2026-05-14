import asyncio
import json
import os
import re
from datetime import datetime, time, timezone, timedelta
from typing import Dict, Set, Optional

from telegram import Update, ChatMember
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler,
    filters, ContextTypes, CallbackContext
)

# ========== КОНФИГ ==========
BOT_TOKEN = "8709216323:AAFbjbsLQV2eF_O5uAslTckXUZqbVrn98NE"  # Замени на свой токен
CHAT_ID = -1003742880726  # Замени на ID чата (отрицательное число)
ADMIN_IDS = {6595788533}  # ID админов (свой Telegram ID)

# Файл для сохранения данных
DATA_FILE = "table_data.json"

# Глобальные переменные
users_status: Dict[str, bool] = {}  # ник: True(✅)/False(❌)
table_message_id: Optional[int] = None  # ID сообщения с таблицей

# ========== РАБОТА С ФАЙЛОМ ==========
def load_data():
    """Загружает данные из JSON файла"""
    global users_status, table_message_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                users_status = data.get("users_status", {})
                table_message_id = data.get("table_message_id")
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            users_status = {}
            table_message_id = None
    else:
        users_status = {}
        table_message_id = None

def save_data():
    """Сохраняет данные в JSON файл"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "users_status": users_status,
                "table_message_id": table_message_id
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")

# ========== ФУНКЦИИ ТАБЛИЦЫ ==========
def get_current_date_moscow() -> str:
    """Возвращает дату по МСК в формате DD.MM.YY"""
    msk_tz = timezone(timedelta(hours=3))
    now = datetime.now(msk_tz)
    return now.strftime("%d.%m.%y")

def build_table() -> str:
    """Формирует текст таблицы с отметками"""
    if not users_status:
        return "📋 Таблица пуста.\nУчастники появятся после входа в чат."
    
    date = get_current_date_moscow()
    lines = [f"📅 {date}\n", "<pre>"]
    
    # Сортируем по имени
    for name in sorted(users_status.keys()):
        mark = "✅" if users_status[name] else "❌"
        lines.append(f"{name:<20} {mark}")
    
    lines.append("</pre>")
    return "\n".join(lines)

async def update_table_message(context: ContextTypes.DEFAULT_TYPE):
    """Создаёт или редактирует сообщение с таблицей"""
    global table_message_id
    text = build_table()
    
    try:
        if table_message_id:
            # Пробуем отредактировать существующее
            await context.bot.edit_message_text(
                chat_id=CHAT_ID,
                message_id=table_message_id,
                text=text,
                parse_mode="HTML"
            )
        else:
            # Создаём новое
            msg = await context.bot.send_message(
                chat_id=CHAT_ID,
                text=text,
                parse_mode="HTML"
            )
            table_message_id = msg.message_id
            save_data()
    except Exception as e:
        print(f"Ошибка обновления таблицы: {e}")
        # Если сообщение потеряно (например, удалено), создаём заново
        if "message to edit not found" in str(e):
            table_message_id = None
            await update_table_message(context)

async def reset_table(context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает все отметки в ❌ и обновляет дату"""
    global users_status
    for user in users_status:
        users_status[user] = False
    save_data()
    await update_table_message(context)
    print(f"[{datetime.now()}] Таблица сброшена")

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка сообщений вида 'П 2500'
    Ставит ✅ игроку и удаляет сообщение игрока + сообщение бота1
    """
    message = update.effective_message
    if not message or not message.chat:
        return
    
    # Проверяем, что чат — нужная группа
    if message.chat.id != CHAT_ID:
        return
    
    user = message.from_user
    if not user or user.is_bot:
        return
    
    # Получаем никнейм
    username = user.username or user.first_name
    
    # Ищем точное совпадение (без учёта регистра)
    matched_name = None
    for name in users_status.keys():
        if name.lower() == username.lower():
            matched_name = name
            break
    
    if not matched_name:
        # Незнакомый человек — просто удаляем сообщение, чтобы не засоряло
        try:
            await message.delete()
        except:
            pass
        return
    
    # Проверяем текст: "П 2500" или "п 2500"
    text = message.text.strip()
    if not re.match(r'^[Пп]\s+\d+$', text):
        return
    
    # Ставим ✅
    users_status[matched_name] = True
    save_data()
    await update_table_message(context)
    
    # Удаляем сообщение игрока
    try:
        await message.delete()
    except:
        pass
    
    # Удаляем сообщение бота1 (если оно есть)
    # Пытаемся найти сообщение бота выше или в ответе
    try:
        # Вариант 1: если сообщение игрока — ответ на сообщение бота1
        if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot:
            await message.reply_to_message.delete()
        
        # Вариант 2: ищем предыдущее сообщение от бота (если не нашли в ответе)
        else:
            # Получаем последние 5 сообщений в чате
            async for msg in context.bot.get_chat_history(CHAT_ID, limit=5):
                if msg.message_id < message.message_id and msg.from_user and msg.from_user.is_bot:
                    # Проверяем, что сообщение бота похоже на перевод (содержит GRAM или имя игрока)
                    if msg.text and ("GRAM" in msg.text or matched_name.lower() in msg.text.lower()):
                        await msg.delete()
                        break
    except Exception as e:
        print(f"Не удалось удалить сообщение бота: {e}")

# ========== ОТСЛЕЖИВАНИЕ ВХОДА/ВЫХОДА ==========
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет участника при входе, удаляет при выходе"""
    chat_member_update = update.chat_member
    if not chat_member_update:
        return
    if chat_member_update.chat.id != CHAT_ID:
        return
    
    new_status = chat_member_update.new_chat_member.status
    user = chat_member_update.new_chat_member.user
    
    if user.is_bot:
        return  # Игнорируем ботов
    
    # Формируем отображаемое имя
    name = user.username if user.username else user.first_name
    
    changed = False
    
    if new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        # Пользователь зашёл в чат
        if name not in users_status:
            users_status[name] = False
            changed = True
            print(f"[+] Добавлен: {name}")
    
    elif new_status == ChatMemberStatus.LEFT:
        # Пользователь вышел
        if name in users_status:
            del users_status[name]
            changed = True
            print(f"[-] Удалён: {name}")
    
    if changed:
        save_data()
        await update_table_message(context)

# ========== КОМАНДЫ ==========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие"""
    await update.message.reply_text(
        "🤖 Бот таблицы отметок работает!\n\n"
        "Правила:\n"
        "• Напиши «П 2500» — получишь ✅\n"
        "• Каждую ночь в 00:00 МСК таблица сбрасывается\n"
        "• При входе/выходе из чата список обновляется"
    )

async def cmd_upd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительное обновление таблицы (только для админов)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    await update_table_message(context)
    await update.message.reply_text("✅ Таблица принудительно обновлена")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручной сброс таблицы (только для админов)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    await reset_table(context)
    await update.message.reply_text("🔄 Таблица сброшена (все отметки ❌)")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику (сколько ✅)"""
    if update.effective_chat.id != CHAT_ID:
        return
    
    total = len(users_status)
    done = sum(1 for v in users_status.values() if v)
    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"Всего участников: {total}\n"
        f"Отметилось: {done}\n"
        f"Не отметилось: {total - done}"
    )

# ========== ЗАПУСК И ПЛАНИРОВЩИК ==========
async def reset_callback(context: ContextTypes.DEFAULT_TYPE):
    """Колбэк для ежедневного сброса"""
    await reset_table(context)

def main():
    # Загружаем сохранённые данные
    load_data()
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("upd", cmd_upd))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CommandHandler("stats", cmd_stats))
    
    # Обработчик сообщений с "П 2500"
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    # Обработчик входа/выхода участников
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    # Планировщик сброса каждый день в 00:00 МСК
    msk_tz = timezone(timedelta(hours=3))
    application.job_queue.run_daily(
        reset_callback,
        time=time(0, 0, 0, tzinfo=msk_tz),
        days=tuple(range(7))
    )
    
    print(f"✅ Бот запущен!")
    print(f"   Чат ID: {CHAT_ID}")
    print(f"   Участников в таблице: {len(users_status)}")
    print(f"   Сброс каждый день в 00:00 МСК")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
