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
BOT1_ID = 5788046441

CHAT_IDS = [-1003780899168, -1003742880726]
CHAT_NAMES = {
    -1003780899168: "🤖 Группа Админа",
    -1003742880726: "🎮 Группа Рабов"
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
            "users": {},  # ник: {"daily": bool, "total": int}
            "message_id": None
        }
        save_data()

# ========== ТАБЛИЦА ==========
def get_current_date_moscow() -> str:
    msk_tz = timezone(timedelta(hours=3))
    return datetime.now(msk_tz).strftime("%d.%m.%y")

def build_table(users: Dict[str, Dict]) -> str:
    if not users:
        return "📋 Таблица пуста.\nНапишите «П 2500» чтобы отметиться"
    
    date = get_current_date_moscow()
    lines = [f"📅 {date}\n", "<pre>"]
    
    for name in sorted(users.keys()):
        mark = "✅" if users[name]["daily"] else "❌"
        lines.append(f"{name:<20} {mark}")
    
    lines.append("</pre>")
    lines.append("\n⭐ Всего переводов — /l")
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

# ========== ОБРАБОТКА ПЛАТЕЖЕЙ ==========
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения 'П 2500' от пользователей"""
    message = update.effective_message
    if not message or message.chat.id not in CHAT_IDS:
        return
    
    user = message.from_user
    if not user or user.is_bot:
        return
    
    # Пропускаем админа
    if user.id in ADMIN_IDS:
        return
    
    # Проверяем текст
    text = message.text.strip()
    if not re.match(r'^[Пп]\s+\d+$', text):
        return
    
    chat_id = message.chat.id
    name = user.username or user.first_name
    
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    
    # Добавляем пользователя если его нет
    if name not in users:
        users[name] = {"daily": False, "total": 0}
    
    # Ставим отметку
    users[name]["daily"] = True
    users[name]["total"] = users[name].get("total", 0) + 1
    save_data()
    
    await update_table_message(chat_id, context)
    print(f"[✓] {name} отметился (всего: {users[name]['total']}) в чате {chat_id}")
    
    # Удаляем сообщение пользователя
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
            users[name] = {"daily": False, "total": 0}
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
    """Обновляет таблицу в чате или в ЛС показывает все чаты"""
    user_id = update.effective_user.id
    
    # Если команда в ЛС
    if update.effective_chat.type == "private":
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Нет прав")
            return
        
        result = []
        for chat_id in CHAT_IDS:
            init_chat(chat_id)
            users = chat_data[chat_id]["users"]
            chat_name = CHAT_NAMES.get(chat_id, f"Чат {chat_id}")
            
            if users:
                lines = [f"<b>{chat_name}</b>:", "<pre>"]
                for name in sorted(users.keys()):
                    daily = "✅" if users[name]["daily"] else "❌"
                    total = users[name].get("total", 0)
                    lines.append(f"{name:<20} {daily} (всего: {total})")
                lines.append("</pre>")
                result.append("\n".join(lines))
            else:
                result.append(f"<b>{chat_name}</b>:\n📋 Пусто")
        
        if result:
            await update.message.reply_text("\n\n".join(result), parse_mode="HTML")
        return
    
    # Если команда в чате
    if user_id not in ADMIN_IDS:
        return
    
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    await update_table_message(chat_id, context)
    await update.message.reply_text(f"✅ Таблица обновлена")

async def cmd_l(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику переводов"""
    user_id = update.effective_user.id
    
    # В ЛС
    if update.effective_chat.type == "private":
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Нет прав")
            return
        
        result = []
        for chat_id in CHAT_IDS:
            init_chat(chat_id)
            users = chat_data[chat_id]["users"]
            chat_name = CHAT_NAMES.get(chat_id, f"Чат {chat_id}")
            
            if users:
                lines = [f"<b>📊 {chat_name}</b>", "<pre>"]
                sorted_users = sorted(users.items(), key=lambda x: x[1].get("total", 0), reverse=True)
                for name, data in sorted_users:
                    total = data.get("total", 0)
                    lines.append(f"{name:<25} {total} раз")
                lines.append("</pre>")
                result.append("\n".join(lines))
            else:
                result.append(f"<b>{chat_name}</b>:\n📋 Нет данных")
        
        if result:
            await update.message.reply_text("\n\n".join(result), parse_mode="HTML")
        return
    
    # В чате
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    init_chat(chat_id)
    users = chat_data[chat_id]["users"]
    
    if not users:
        await update.message.reply_text("📋 Статистики пока нет")
        return
    
    lines = ["📊 <b>Статистика переводов</b>", "<pre>"]
    sorted_users = sorted(users.items(), key=lambda x: x[1].get("total", 0), reverse=True)
    for name, data in sorted_users:
        total = data.get("total", 0)
        lines.append(f"{name:<25} {total} раз")
    lines.append("</pre>")
    
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает общую статистику (только для админа)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        for name in chat_data[chat_id]["users"]:
            chat_data[chat_id]["users"][name]["total"] = 0
        save_data()
        await update_table_message(chat_id, context)
    
    await update.message.reply_text("✅ Общая статистика сброшена")

async def cmd_x(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ставит ❌ пользователю во всех чатах (/x имя)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        return
    
    target_name = " ".join(context.args)
    
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        users = chat_data[chat_id]["users"]
        
        for name in users.keys():
            if name.lower() == target_name.lower():
                users[name]["daily"] = False
                save_data()
                await update_table_message(chat_id, context)
                print(f"[X] {name} ❌")
                break

async def cmd_v(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ставит ✅ пользователю во всех чатах (/v имя)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        return
    
    target_name = " ".join(context.args)
    
    for chat_id in CHAT_IDS:
        init_chat(chat_id)
        users = chat_data[chat_id]["users"]
        
        for name in users.keys():
            if name.lower() == target_name.lower():
                users[name]["daily"] = True
                save_data()
                await update_table_message(chat_id, context)
                print(f"[V] {name} ✅")
                break

# ========== ФОНОВЫЙ СБРОС ==========
async def scheduler_loop(application):
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
                    users[user]["daily"] = False
                save_data()
                
                fake_context = type('obj', (object,), {'bot': application.bot})()
                await update_table_message(chat_id, fake_context)
                print(f"[{datetime.now()}] Дневные отметки сброшены в чате {chat_id}")
            except Exception as e:
                print(f"Ошибка сброса: {e}")

# ========== ЗАПУСК ==========
async def post_init(application):
    print("🔄 Загрузка данных...")
    
    for chat_id in CHAT_IDS:
        try:
            init_chat(chat_id)
            fake_context = type('obj', (object,), {'bot': application.bot})()
            await update_table_message(chat_id, fake_context)
        except Exception as e:
            print(f"Ошибка: {e}")
    
    asyncio.create_task(scheduler_loop(application))
    print("✅ Бот готов к работе!")

def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.post_init = post_init
    
    # Команды
    application.add_handler(CommandHandler("upd", cmd_upd))
    application.add_handler(CommandHandler("l", cmd_l))
    application.add_handler(CommandHandler("x", cmd_x))
    application.add_handler(CommandHandler("v", cmd_v))
    application.add_handler(CommandHandler("reset_stats", cmd_reset_stats))
    
    # Обработчики
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    print(f"✅ Бот запущен!")
    print(f"   Чаты: {CHAT_IDS}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
