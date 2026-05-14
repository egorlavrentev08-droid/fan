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
BOT1_ID = 5788046441  # ID бота1

CHAT_IDS = [-1003780899168, -1003742880726]

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

async def sync_users_from_chat(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Синхронизирует список участников чата с таблицей"""
    init_chat(chat_id)
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        
        current_users = set()
        
        for admin in admins:
            if not admin.user.is_bot:
                name = admin.user.username or admin.user.first_name
                current_users.add(name)
        
        users = chat_data[chat_id]["users"]
        changed = False
        
        for name in current_users:
            if name not in users:
                users[name] = False
                changed = True
                print(f"[Синхронизация] Чат {chat_id}: добавлен {name}")
        
        if changed:
            save_data()
            await update_table_message(chat_id, context)
            
    except Exception as e:
        print(f"Ошибка синхронизации чата {chat_id}: {e}")

# ========== ОБРАБОТКА СООБЩЕНИЙ ОТ БОТА1 ==========
async def handle_bot1_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения от бота1"""
    message = update.effective_message
    if not message or message.chat.id not in CHAT_IDS:
        return
    
    if not message.from_user or message.from_user.id != BOT1_ID:
        return
    
    chat_id = message.chat.id
    text = message.text or ""
    
    success_pattern = r'перевел\s+\d+\s+GRAM\s+для\s+@?(\w+)'
    fail_pattern = r'Недостаточно\s+GRAM\s+на\s+балансе'
    
    success_match = re.search(success_pattern, text, re.IGNORECASE)
    fail_match = re.search(fail_pattern, text, re.IGNORECASE)
    
    if success_match:
        parts = text.split('перевел')
        if len(parts) > 0:
            sender_name = parts[0].strip()
            
            if sender_name:
                init_chat(chat_id)
                users = chat_data[chat_id]["users"]
                
                matched_name = None
                for name in users.keys():
                    if name.lower() == sender_name.lower():
                        matched_name = name
                        break
                
                if matched_name:
                    users[matched_name] = True
                    save_data()
                    await update_table_message(chat_id, context)
                    print(f"[✓] {matched_name} отметился в чате {chat_id}")
                    
                    try:
                        await message.delete()
                    except:
                        pass
                    
                    try:
                        async for msg in context.bot.get_chat_history(chat_id, limit=20):
                            if msg.from_user and not msg.from_user.is_bot:
                                if msg.text and re.match(r'^[Пп]\s+\d+$', msg.text.strip()):
                                    msg_name = msg.from_user.username or msg.from_user.first_name
                                    if msg_name.lower() == sender_name.lower():
                                        await msg.delete()
                                        break
                    except Exception as e:
                        print(f"Ошибка удаления сообщения игрока: {e}")
    
    elif fail_match:
        try:
            await message.delete()
            print(f"[✗] Недостаточно средств - сообщение бота1 удалено")
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
    
    if user.is_bot and user.id != BOT1_ID:
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
async def cmd_upd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет таблицу и синхронизирует участников"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    await sync_users_from_chat(chat_id, context)
    await update_table_message(chat_id, context)

async def cmd_x(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ставит ❌ указанному пользователю во всех чатах (/x username)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        return
    
    target_name = context.args[0]
    
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        users = chat_data[chat_id]["users"]
        
        for name in users.keys():
            if name.lower() == target_name.lower():
                users[name] = False
                save_data()
                await update_table_message(chat_id, context)
                print(f"[X] Чат {chat_id}: {name} установлен ❌")
                break

async def cmd_v(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ставит ✅ указанному пользователю во всех чатах (/v username)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        return
    
    target_name = context.args[0]
    
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        users = chat_data[chat_id]["users"]
        
        for name in users.keys():
            if name.lower() == target_name.lower():
                users[name] = True
                save_data()
                await update_table_message(chat_id, context)
                print(f"[V] Чат {chat_id}: {name} установлен ✅")
                break

# ========== ФОНОВЫЙ СБРОС ==========
async def scheduler_loop(application: Application):
    """Сбрасывает таблицы в 00:00 МСК"""
    msk_tz = timezone(timedelta(hours=3))
    
    while True:
        now = datetime.now(msk_tz)
        next_midnight = datetime(
            now.year, now.month, now.day, 0, 0, 0, tzinfo=msk_tz
        ) + timedelta(days=1)
        
        seconds_until = (next_midnight - now).total_seconds()
        print(f"Следующий сброс через {seconds_until/3600:.1f} часов")
        
        await asyncio.sleep(seconds_until)
        
        for chat_id in CHAT_IDS:
            try:
                init_chat(chat_id)
                users = chat_data[chat_id]["users"]
                for user in users:
                    users[user] = False
                save_data()
                
                fake_context = type('obj', (object,), {'bot': application.bot})()
                await update_table_message(chat_id, fake_context)
                print(f"[{datetime.now()}] Таблица сброшена в чате {chat_id}")
            except Exception as e:
                print(f"Ошибка сброса чата {chat_id}: {e}")

# ========== ИНИЦИАЛИЗАЦИЯ ==========
async def post_init(application: Application):
    """Запускается после инициализации приложения"""
    for chat_id in CHAT_IDS:
        try:
            fake_context = type('obj', (object,), {'bot': application.bot})()
            await sync_users_from_chat(chat_id, fake_context)
        except Exception as e:
            print(f"Ошибка синхронизации чата {chat_id}: {e}")
    
    asyncio.create_task(scheduler_loop(application))
    print("✅ Бот готов к работе")

# ========== ЗАПУСК ==========
def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.post_init = post_init
    
    # Только нужные команды
    application.add_handler(CommandHandler("upd", cmd_upd))
    application.add_handler(CommandHandler("x", cmd_x))
    application.add_handler(CommandHandler("v", cmd_v))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bot1_message))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    print(f"✅ Бот запущен!")
    print(f"   Чаты: {CHAT_IDS}")
    print(f"   Админ: {ADMIN_IDS}")
    print(f"   Отслеживается бот1: {BOT1_ID}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
