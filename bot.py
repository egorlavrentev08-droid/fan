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
    -1003780899168: "🤖 GramChecker",
    -1003742880726: "🎮 Вторая группа"
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
        return "📋 Таблица пуста.\nУчастники появятся после входа в чат."
    
    date = get_current_date_moscow()
    lines = [f"📅 {date}\n", "<pre>"]
    
    for name in sorted(users.keys()):
        mark = "✅" if users[name]["daily"] else "❌"
        lines.append(f"{name:<20} {mark}")
    
    lines.append("</pre>")
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

# ========== ПОИСК ИМЕНИ ИЗ СООБЩЕНИЯ БОТА1 ==========
def extract_sender_name_from_bot1(text: str) -> Optional[str]:
    """Извлекает имя отправителя из сообщения бота1"""
    # Пример: "Ⲙышⲕⲁ {Ⲙⲁⲫυⳡⲕⲁ}❀ {Она/Её} перевел 2 500 GRAM для"
    # Нужно взять текст до слова "перевел"
    
    match = re.search(r'^(.*?)\s+перевел\s+\d+\s+GRAM', text, re.IGNORECASE)
    if match:
        raw_name = match.group(1).strip()
        # Убираем всякие {дополнения} и ❀ символы
        clean_name = re.sub(r'\{[^}]*\}', '', raw_name)  # Убираем {текст}
        clean_name = re.sub(r'[❀☆★✿]', '', clean_name)  # Убираем украшения
        clean_name = clean_name.strip()
        
        # Если имя слишком длинное или пустое, пробуем другой вариант
        if clean_name and len(clean_name) < 50:
            return clean_name
    
    return None

# ========== ОБРАБОТКА СООБЩЕНИЙ ОТ БОТА1 ==========
async def handle_bot1_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat.id not in CHAT_IDS:
        return
    
    if not message.from_user or message.from_user.id != BOT1_ID:
        return
    
    chat_id = message.chat.id
    text = message.text or ""
    
    # Проверяем на успешный перевод
    if "перевел" in text and "GRAM" in text and "для" in text:
        sender_name = extract_sender_name_from_bot1(text)
        
        if sender_name:
            init_chat(chat_id)
            users = chat_data[chat_id]["users"]
            
            # Ищем отправителя в таблице
            matched_name = None
            for name in users.keys():
                if name.lower() == sender_name.lower():
                    matched_name = name
                    break
            
            if matched_name:
                # Обновляем статистику
                users[matched_name]["daily"] = True
                users[matched_name]["total"] = users[matched_name].get("total", 0) + 1
                save_data()
                await update_table_message(chat_id, context)
                print(f"[✓] {matched_name} отметился (всего: {users[matched_name]['total']}) в чате {chat_id}")
                
                # Удаляем сообщение бота1
                try:
                    await message.delete()
                except:
                    pass
                
                # Удаляем сообщение с П 2500
                try:
                    async for msg in context.bot.get_chat_history(chat_id, limit=30):
                        if msg.from_user and not msg.from_user.is_bot:
                            if msg.text and re.match(r'^[Пп]\s+\d+$', msg.text.strip()):
                                msg_name = msg.from_user.username or msg.from_user.first_name
                                if msg_name.lower() == sender_name.lower():
                                    await msg.delete()
                                    break
                except Exception as e:
                    print(f"Ошибка удаления сообщения игрока: {e}")
        else:
            print(f"[!] Не удалось извлечь имя из: {text[:100]}")
    
    # Проверяем на ошибку "Недостаточно GRAM"
    elif "Недостаточно" in text and "GRAM" in text:
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

# ========== ОБРАБОТЧИК ДОБАВЛЕНИЯ БОТА ==========
async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member_update = update.my_chat_member
    if not chat_member_update:
        return
    
    chat_id = chat_member_update.chat.id
    if chat_id not in CHAT_IDS:
        return
    
    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    
    if old_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED] and \
       new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        
        print(f"[Бот добавлен в чат] {chat_id}")
        await asyncio.sleep(2)
        
        # Получаем админов
        try:
            admins = await context.bot.get_chat_administrators(chat_id)
            init_chat(chat_id)
            users = chat_data[chat_id]["users"]
            
            for admin in admins:
                if not admin.user.is_bot and admin.user.id not in ADMIN_IDS:
                    name = admin.user.username or admin.user.first_name
                    if name not in users:
                        users[name] = {"daily": False, "total": 0}
            
            save_data()
            await update_table_message(chat_id, context)
        except Exception as e:
            print(f"Ошибка: {e}")

# ========== КОМАНДЫ ==========
async def cmd_upd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет таблицу в чате или в ЛС показывает все чаты"""
    user_id = update.effective_user.id
    
    # Если команда в ЛС
    if update.effective_chat.type == "private":
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Нет прав")
            return
        
        # Показываем все чаты
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
        else:
            await update.message.reply_text("Нет данных")
        return
    
    # Если команда в чате
    if user_id not in ADMIN_IDS:
        return
    
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS:
        return
    
    # Обновляем таблицу
    status_msg = await update.message.reply_text("🔄 Обновляю таблицу...")
    
    # Синхронизируем админов
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        init_chat(chat_id)
        users = chat_data[chat_id]["users"]
        
        for admin in admins:
            if not admin.user.is_bot and admin.user.id not in ADMIN_IDS:
                name = admin.user.username or admin.user.first_name
                if name not in users:
                    users[name] = {"daily": False, "total": 0}
        
        save_data()
        await update_table_message(chat_id, context)
    except Exception as e:
        print(f"Ошибка: {e}")
    
    await status_msg.delete()
    await update.message.reply_text(f"✅ Таблица обновлена! Участников: {len(chat_data[chat_id]['users'])}")

async def cmd_l(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику переводов (сколько раз каждый переводил)"""
    user_id = update.effective_user.id
    
    # В ЛС или в чате - показываем текущий чат
    if update.effective_chat.type == "private":
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Нет прав")
            return
        
        # Показываем все чаты
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
        else:
            await update.message.reply_text("Нет данных")
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
                users[name]["daily"] = False
                save_data()
                await update_table_message(chat_id, context)
                print(f"[X] Чат {chat_id}: {name} ❌ (всего: {users[name]['total']})")
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
                users[name]["daily"] = True
                save_data()
                await update_table_message(chat_id, context)
                print(f"[V] Чат {chat_id}: {name} ✅")
                break

# ========== ФОНОВЫЙ СБРОС ==========
async def scheduler_loop(application: Application):
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
                    users[user]["daily"] = False  # Сбрасываем только дневную отметку
                save_data()
                
                fake_context = type('obj', (object,), {'bot': application.bot})()
                await update_table_message(chat_id, fake_context)
                print(f"[{datetime.now()}] Дневные отметки сброшены в чате {chat_id}")
            except Exception as e:
                print(f"Ошибка сброса чата {chat_id}: {e}")

# ========== ЗАПУСК ==========
async def post_init(application: Application):
    print("🔄 Загрузка данных...")
    
    for chat_id in CHAT_IDS:
        try:
            init_chat(chat_id)
            # Получаем админов
            admins = await application.bot.get_chat_administrators(chat_id)
            users = chat_data[chat_id]["users"]
            
            for admin in admins:
                if not admin.user.is_bot and admin.user.id not in ADMIN_IDS:
                    name = admin.user.username or admin.user.first_name
                    if name not in users:
                        users[name] = {"daily": False, "total": 0}
            
            save_data()
            fake_context = type('obj', (object,), {'bot': application.bot})()
            await update_table_message(chat_id, fake_context)
        except Exception as e:
            print(f"Ошибка инициализации чата {chat_id}: {e}")
    
    asyncio.create_task(scheduler_loop(application))
    print("✅ Бот готов к работе")

def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.post_init = post_init
    
    # Команды
    application.add_handler(CommandHandler("upd", cmd_upd))
    application.add_handler(CommandHandler("l", cmd_l))
    application.add_handler(CommandHandler("x", cmd_x))
    application.add_handler(CommandHandler("v", cmd_v))
    
    # Обработчики
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bot1_message))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    
    print(f"✅ Бот запущен!")
    print(f"   Чаты: {CHAT_IDS}")
    print(f"   Бот1 ID: {BOT1_ID}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
