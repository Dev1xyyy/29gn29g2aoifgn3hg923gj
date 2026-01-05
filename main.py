import asyncio
import logging
import re
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8584459028:AAH-w1zry_dsJU8n8zBg1gtJsKSVcMgreqQ"

# Список ID админов (числа, не строки)
ADMIN_IDS = [7728878522, 8301914167]

# Файл для хранения ID пользователей (простая база данных)
USERS_FILE = "users.txt"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная переменная для хранения пользователей в памяти
users_db = set()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def load_users():
    """Загружает ID пользователей из файла при запуске."""
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        with open(USERS_FILE, "r") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except Exception as e:
        logging.error(f"Ошибка загрузки пользователей: {e}")
        return set()

def save_user(user_id):
    """Сохраняет нового пользователя в память и файл."""
    if user_id not in users_db:
        users_db.add(user_id)
        try:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")
        except Exception as e:
            logging.error(f"Ошибка сохранения пользователя: {e}")

# Загружаем пользователей при старте
users_db = load_users()
print(f"Загружено пользователей: {len(users_db)}")

# --- КЛАВИАТУРЫ ---

# Главное меню для обычных пользователей
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="👤 Профиль")]
], resize_keyboard=True)

# --- ЛОГИКА БОТА ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Приветствие пользователя."""
    save_user(message.from_user.id)
    await message.answer(
        "Привет! Напиши сообщение, и я передам его администраторам.",
        reply_markup=main_kb
    )

@dp.message(F.text == "👤 Профиль")
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """
    Показывает профиль пользователя (Имя, ID, Хеш).
    Работает и по команде /profile, и по кнопке '👤 Профиль'.
    """
    save_user(message.from_user.id)
    user = message.from_user
    
    profile_text = (
        f"📂 <b>Твой профиль:</b>\n\n"
        f"👤 <b>Имя:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🔗 <b>Username:</b> @{user.username if user.username else 'Не указан'}\n"
        f"🔑 <b>Хеш:</b> <code>#id{user.id}</code>"
    )
    
    await message.answer(profile_text, parse_mode="HTML")

@dp.message(F.chat.type == "private", ~F.from_user.id.in_(ADMIN_IDS), ~F.text.startswith("/"))
async def handle_user_message(message: types.Message):
    """
    Обработчик сообщений от обычных пользователей.
    """
    save_user(message.from_user.id)
    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет юзернейма"
    
    info_text = (
        f"<b>Новое сообщение!</b>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"хеш: #id{user.id}\n\n"
        f"<b>Сообщение:</b>\n{message.text if message.text else '<i>[Медиафайл]</i>'}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Перейти в лс", url=f"tg://user?id={user.id}")]
    ])

    # Рассылаем админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, 
                text=info_text, 
                parse_mode="HTML", 
                reply_markup=keyboard
            )
            if not message.text:
                await message.send_copy(chat_id=admin_id)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    await message.answer("✅ Сообщение отправлено администраторам. Ждите ответа.")

@dp.message(Command("reply"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_reply_by_id(message: types.Message):
    """
    Команда /reply [id] [текст] для админов.
    """
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer("⚠️ Формат: /reply [ID] [сообщение]")
            return
            
        user_id = int(args[1])
        text_response = args[2]
        
        final_text = f"🔔 <b>Получено сообщение от администрации:</b>\n\n{text_response}"
        
        await bot.send_message(chat_id=user_id, text=final_text, parse_mode="HTML")
        await message.answer(f"✅ Сообщение отправлено пользователю {user_id}.")
        
    except ValueError:
        await message.answer("⚠️ Ошибка: ID должен быть числом.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("mass"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_mass_broadcast(message: types.Message):
    """
    Команда /mass [текст] для рассылки всем пользователям.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Использование: /mass [текст рассылки]")
        return

    broadcast_text = args[1]
    status_msg = await message.answer(f"⏳ Начинаю рассылку на {len(users_db)} пользователей...")

    count_success = 0
    count_error = 0

    for user_id in users_db:
        try:
            await bot.send_message(
                chat_id=user_id, 
                text=broadcast_text, 
                parse_mode="HTML"
            )
            count_success += 1
            await asyncio.sleep(0.05) 
        except Exception:
            count_error += 1

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n"
        f"Отправлено: {count_success}\n"
        f"Не доставлено: {count_error}",
        parse_mode="HTML"
    )

@dp.message(F.from_user.id.in_(ADMIN_IDS), F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    """
    Обработчик ответов админов через Reply.
    """
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    
    if not original_text:
        return

    match = re.search(r"(?:Hash|хеш): #id(\d+)", original_text)

    if match:
        user_id = int(match.group(1))
        try:
            if message.text:
                final_text = f"🔔 <b>Получено сообщение от администрации:</b>\n\n{message.text}"
                await bot.send_message(chat_id=user_id, text=final_text, parse_mode="HTML")
            else:
                new_caption = f"🔔 <b>Получено сообщение от администрации:</b>\n\n{message.caption}" if message.caption else "🔔 <b>Получено сообщение от администрации</b>"
                await message.copy_to(chat_id=user_id, caption=new_caption, parse_mode="HTML")

            await message.answer("✅ Ответ отправлен пользователю.")
        except Exception as e:
            await message.answer(f"❌ Не удалось отправить ответ. Ошибка: {e}")
    else:
        pass

# --- ЗАПУСК ---

async def main():
    print("Бот запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
