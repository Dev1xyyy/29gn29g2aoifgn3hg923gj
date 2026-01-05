import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- КОНФИГУРАЦИЯ ---
# Вставь сюда новый токен, если сгенерировал новый (рекомендуется!)
TOKEN = "8584459028:AAH-w1zry_dsJU8n8zBg1gtJsKSVcMgreqQ"

# Список ID админов (числа, не строки)
ADMIN_IDS = [7728878522, 8301914167]

# Включаем логирование, чтобы видеть ошибки в консоли
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА БОТА ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Приветствие пользователя."""
    await message.answer("Привет! Напиши сообщение, и я передам его администраторам.")

@dp.message(F.chat.type == "private", ~F.from_user.id.in_(ADMIN_IDS))
async def handle_user_message(message: types.Message):
    """
    Обработчик сообщений от обычных пользователей.
    Пересылает сообщение админам с информацией о юзере.
    """
    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет юзернейма"
    
    # Текст уведомления для админа
    # Мы добавляем ID в формате #id12345, чтобы потом легко найти его регулярным выражением
    info_text = (
        f"<b>Новое сообщение!</b>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"хеш: #id{user.id}\n\n"
        f"<b>Сообщение:</b>\n{message.text if message.text else '<i>[Медиафайл]</i>'}"
    )

    # Кнопка для перехода в ЛС
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Перейти в лс", url=f"tg://user?id={user.id}")]
    ])

    # Рассылаем уведомление всем админам
    for admin_id in ADMIN_IDS:
        try:
            # Отправляем инфо
            await bot.send_message(
                chat_id=admin_id, 
                text=info_text, 
                parse_mode="HTML", 
                reply_markup=keyboard
            )
            # Если это не просто текст (например фото), пересылаем и само сообщение следом
            if not message.text:
                await message.send_copy(chat_id=admin_id)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    await message.answer("✅ Сообщение отправлено администраторам. Ждите ответа.")

@dp.message(F.from_user.id.in_(ADMIN_IDS), F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    """
    Обработчик ответов админов.
    Если админ делает Reply на сообщение бота, ответ улетает пользователю.
    """
    # Получаем текст сообщения, на которое ответил админ
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    
    if not original_text:
        return

    # Ищем ID пользователя в тексте сообщения (по метке Hash: #id...)
    # Используем регулярное выражение для надежности
    match = re.search(r"Hash: #id(\d+)", original_text)

    if match:
        user_id = int(match.group(1))
        try:
            # Метод copy_message позволяет отправить пользователю любой тип контента (текст, фото, стикер)
            await message.copy_to(chat_id=user_id)
            await message.answer("✅ Ответ отправлен пользователю.")
        except Exception as e:
            await message.answer(f"❌ Не удалось отправить ответ. Возможно, пользователь заблокировал бота.\nОшибка: {e}")
    else:
        # Если админ ответил не на уведомление бота, а просто так
        await message.answer("⚠️ Чтобы ответить пользователю, нужно сделать <b>Reply</b> (Ответить) на сообщение с его ID.", parse_mode="HTML")

# --- ЗАПУСК ---

async def main():
    print("Бот запущен...")
    # Удаляем вебхуки и запускаем полинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:

        print("Бот остановлен")
