import asyncio
import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from telegram import Update, ChatMember
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler,
    filters, ContextTypes
)

# ========== КОНФИГ ==========
BOT_TOKEN = "8709216323:AAFbjbsLQV2eF_O5uAslTckXUZqbVrn98NE"
ADMIN_IDS = {6595788533}

CHAT_IDS = [-1003780899168, -1003742880726]
CHAT_NAMES = {
    -1003780899168: "GramChecker",
    -1003742880726: "Вторая группа"
}

DATA_FILE = "table_data.json"

chat_data: Dict[int, Dict] = {}

# ========== РАБОТА С ФАЙЛОМ ==========
def load_data():
    global chat_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
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
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "users": {},  # ник: bool (True=✅, False=❌)
            "message_id": None
        }
        save_data()

# ========== ТАБЛИЦА ==========
def get_current_date_moscow() -> str:
    msk_tz = timezone(timedelta(hours=3))
    return datetime.now(msk_tz).strftime("%d.%m.%y")

def build_table(users: Dict[str, bool]) -> str:
    if not users:
        return "📋 Таблица пуста"
    
    date = get_current_date_moscow()
    lines = [f"📅 {date}"]
    
    for name in sorted(users.keys()):
        mark = "✅" if users[name] else "❌"
        lines.append(f"{name} {mark}")
    
    return "\n".join(lines)

async def update_table_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    message_id = chat_data[chat_id]["message_id"]
    text = build_table(users)
    
    try:
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text
            )
            chat_data[chat_id]["message_id"] = msg.message_id
            save_data()
    except Exception as e:
        print(f"Ошибка в чате {chat_id}: {e}")
        if "message to edit not found" in str(e):
            chat_data[chat_id]["message_id"] = None
            save_data()
            await update_table_message(chat_id, context)

# ========== ОБРАБОТКА ПЛАТЕЖЕЙ ==========
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat.id not in CHAT_IDS:
        return
    
    user = message.from_user
    if not user or user.is_bot:
        return
    
    if user.id in ADMIN_IDS:
        return
    
    text = message.text.strip()
    if not re.match(r'^[Пп]\s+\d+$', text):
        return
    
    chat_id = message.chat.id
    name = user.username or user.first_name
    
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    
    if name not in users:
        users[name] = False
    
    users[name] = True
    save_data()
    
    await update_table_message(chat_id, context)
    
    try:
        await message.delete()
    except:
        pass

# ========== ОБРАБОТКА ВХОДА/ВЫХОДА ==========
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
    
    if user.id in ADMIN_IDS:
        return
    
    name = user.username or user.first_name
    users = chat_data[chat_id]["users"]
    changed = False
    
    if new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        if name not in users:
            users[name] = False
            changed = True
    elif new_status == ChatMemberStatus.LEFT:
        if name in users:
            del users[name]
            changed = True
    
    if changed:
        save_data()
        await update_table_message(chat_id, context)

# ========== КОМАНДЫ ==========
async def cmd_upd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновить таблицу"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if update.effective_chat.type == "private":
        # В ЛС показываем все чаты
        for chat_id in CHAT_IDS:
            init_chat(chat_id)
            users = chat_data[chat_id]["users"]
            chat_name = CHAT_NAMES.get(chat_id, str(chat_id))
            
            if users:
                lines = [f"{chat_name}:"]
                for name in sorted(users.keys()):
                    mark = "✅" if users[name] else "❌"
                    lines.append(f"  {name} {mark}")
                await update.message.reply_text("\n".join(lines))
            else:
                await update.message.reply_text(f"{chat_name}:\n  Таблица пуста")
        return
    
    # В чате обновляем таблицу
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    await update_table_message(chat_id, context)

async def cmd_l(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика (только для админа в ЛС)"""
    if update.effective_chat.type != "private":
        return
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    # Подсчитываем статистику из истории сообщений
    result = []
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        users = chat_data[chat_id]["users"]
        chat_name = CHAT_NAMES.get(chat_id, str(chat_id))
        
        if users:
            lines = [f"{chat_name}:"]
            for name in sorted(users.keys()):
                lines.append(f"  {name}")
            result.append("\n".join(lines))
        else:
            result.append(f"{chat_name}:\n  Пусто")
    
    await update.message.reply_text("\n\n".join(result))

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить все отметки в ❌"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        for name in chat_data[chat_id]["users"]:
            chat_data[chat_id]["users"][name] = False
        save_data()
        await update_table_message(chat_id, context)

# ========== СБРОС В 00:00 ==========
async def scheduler_loop(application):
    msk_tz = timezone(timedelta(hours=3))
    
    while True:
        now = datetime.now(msk_tz)
        next_midnight = datetime(
            now.year, now.month, now.day, 0, 0, 0, tzinfo=msk_tz
        ) + timedelta(days=1)
        
        seconds_until = (next_midnight - now).total_seconds()
        await asyncio.sleep(seconds_until)
        
        for chat_id in CHAT_IDS:
            try:
                init_chat(chat_id)
                for name in chat_data[chat_id]["users"]:
                    chat_data[chat_id]["users"][name] = False
                save_data()
                
                fake_context = type('obj', (object,), {'bot': application.bot})()
                await update_table_message(chat_id, fake_context)
            except Exception as e:
                print(f"Ошибка: {e}")

# ========== ЗАПУСК ==========
async def post_init(application):
    for chat_id in CHAT_IDS:
        try:
            fake_context = type('obj', (object,), {'bot': application.bot})()
            await update_table_message(chat_id, fake_context)
        except Exception as e:
            print(f"Ошибка: {e}")
    
    asyncio.create_task(scheduler_loop(application))
    print("✅ Бот запущен")

def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.post_init = post_init
    
    application.add_handler(CommandHandler("upd", cmd_upd))
    application.add_handler(CommandHandler("l", cmd_l))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
