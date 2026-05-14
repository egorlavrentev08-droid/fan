import asyncio
import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

from telegram import Update, ChatMember
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler,
    filters, ContextTypes
)

# ========== КОНФИГ ==========
BOT_TOKEN = "8709216323:AAFbjbsLQV2eF_O5uAslTckXUZqbVrn98NE"
ADMIN_IDS = {6595788533}

# Список чатов, где работает бот
CHAT_IDS = [-1003780899168, -1003742880726]

DATA_FILE = "table_data.json"

# Храним данные для каждого чата отдельно
# Структура: { chat_id: {"users": {ник: bool}, "message_id": int} }
chat_data: Dict[int, Dict] = {}

# ========== РАБОТА С ФАЙЛОМ ==========
def load_data():
    global chat_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Преобразуем ключи из строк в числа
                chat_data = {int(k): v for k, v in loaded.items()}
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            chat_data = {}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def init_chat(chat_id: int):
    """Инициализирует данные для чата, если их нет"""
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "users": {},
            "message_id": None
        }
        save_data()

# ========== ТАБЛИЦА ==========
def get_current_date_moscow() -> str:
    msk_tz = timezone(timedelta(hours=3))
    return datetime.now(msk_tz).strftime("%d.%m.%y")

def build_table(users: Dict[str, bool]) -> str:
    if not users:
        return "📋 Таблица пуста.\nУчастники появятся после входа в чат."
    
    date = get_current_date_moscow()
    lines = [f"📅 {date}\n", "<pre>"]
    
    for name in sorted(users.keys()):
        mark = "✅" if users[name] else "❌"
        lines.append(f"{name:<20} {mark}")
    
    lines.append("</pre>")
    return "\n".join(lines)

async def update_table_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет таблицу в конкретном чате"""
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    message_id = chat_data[chat_id]["message_id"]
    text = build_table(users)
    
    try:
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML"
            )
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            chat_data[chat_id]["message_id"] = msg.message_id
            save_data()
    except Exception as e:
        print(f"Ошибка в чате {chat_id}: {e}")
        if "message to edit not found" in str(e):
            chat_data[chat_id]["message_id"] = None
            save_data()
            await update_table_message(chat_id, context)

async def reset_table(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает отметки в конкретном чате"""
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    for user in users:
        users[user] = False
    save_data()
    await update_table_message(chat_id, context)
    print(f"[{datetime.now()}] Таблица сброшена в чате {chat_id}")

# ========== ОБРАБОТКА ПЛАТЕЖЕЙ ==========
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat.id not in CHAT_IDS:
        return
    
    chat_id = message.chat.id
    init_chat(chat_id)
    
    user = message.from_user
    if not user or user.is_bot:
        return
    
    username = user.username or user.first_name
    
    # Ищем ник в таблице этого чата
    users = chat_data[chat_id]["users"]
    matched_name = None
    for name in users.keys():
        if name.lower() == username.lower():
            matched_name = name
            break
    
    if not matched_name:
        try:
            await message.delete()
        except:
            pass
        return
    
    text = message.text.strip()
    if not re.match(r'^[Пп]\s+\d+$', text):
        return
    
    # Ставим отметку
    users[matched_name] = True
    save_data()
    await update_table_message(chat_id, context)
    
    # Удаляем сообщение игрока
    try:
        await message.delete()
    except:
        pass
    
    # Удаляем сообщение бота1
    try:
        if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot:
            await message.reply_to_message.delete()
        else:
            async for msg in context.bot.get_chat_history(chat_id, limit=5):
                if msg.message_id < message.message_id and msg.from_user and msg.from_user.is_bot:
                    if msg.text and ("GRAM" in msg.text or matched_name.lower() in msg.text.lower()):
                        await msg.delete()
                        break
    except Exception as e:
        print(f"Ошибка удаления бота: {e}")

# ========== ВХОД/ВЫХОД ==========
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member_update = update.chat_member
    if not chat_member_update:
        return
    
    chat_id = chat_member_update.chat.id
    if chat_id not in CHAT_IDS:
        return
    
    init_chat(chat_id)
    
    new_status = chat_member_update.new_chat_member.status
    user = chat_member_update.new_chat_member.user
    
    if user.is_bot:
        return
    
    name = user.username if user.username else user.first_name
    users = chat_data[chat_id]["users"]
    changed = False
    
    if new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        if name not in users:
            users[name] = False
            changed = True
            print(f"[+] Чат {chat_id}: добавлен {name}")
    elif new_status == ChatMemberStatus.LEFT:
        if name in users:
            del users[name]
            changed = True
            print(f"[-] Чат {chat_id}: удалён {name}")
    
    if changed:
        save_data()
        await update_table_message(chat_id, context)

# ========== КОМАНДЫ ==========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in CHAT_IDS:
        return
    await update.message.reply_text(
        "🤖 Бот таблицы отметок работает!\n\n"
        "Правила:\n"
        "• Напиши «П 2500» — получишь ✅\n"
        "• Каждую ночь в 00:00 МСК таблица сбрасывается\n"
        "• При входе/выходе список обновляется"
    )

async def cmd_upd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет прав")
        return
    
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    await update_table_message(chat_id, context)
    await update.message.reply_text("✅ Таблица обновлена")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет прав")
        return
    
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    await reset_table(chat_id, context)
    await update.message.reply_text("🔄 Таблица сброшена")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    total = len(users)
    done = sum(1 for v in users.values() if v)
    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"Всего: {total}\n"
        f"Отметилось: {done}\n"
        f"Осталось: {total - done}"
    )

# ========== ФОНОВЫЙ СБРОС ==========
async def scheduler_loop(application: Application):
    """Сбрасывает таблицы в 00:00 МСК для всех чатов"""
    msk_tz = timezone(timedelta(hours=3))
    
    while True:
        now = datetime.now(msk_tz)
        next_midnight = datetime(
            now.year, now.month, now.day, 0, 0, 0, tzinfo=msk_tz
        ) + timedelta(days=1)
        
        seconds_until = (next_midnight - now).total_seconds()
        print(f"Следующий сброс через {seconds_until/3600:.1f} часов")
        
        await asyncio.sleep(seconds_until)
        
        # Сбрасываем таблицы во всех чатах
        for chat_id in CHAT_IDS:
            try:
                await reset_table(chat_id, application.bot)
                # Передаём фейковый контекст, используем только bot
            except Exception as e:
                print(f"Ошибка сброса чата {chat_id}: {e}")

# ========== ЗАПУСК ==========
def main():
    load_data()
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("upd", cmd_upd))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    # Запускаем фоновый таск
    async def startup():
        asyncio.create_task(scheduler_loop(application))
    
    application.post_init = startup
    
    print(f"✅ Бот запущен!")
    print(f"   Чаты: {CHAT_IDS}")
    print(f"   Админ: {ADMIN_IDS}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Фикс для корректного импорта
    import asyncio
    main()
