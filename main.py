from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import logging
import os

BOT_TOKEN = os.environ.get("8537321553:AAGF6sywXfiSs7bJEO9dPnw-GSS-cUFZvds") or "8537321553:AAGF6sywXfiSs7bJEO9dPnw-GSS-cUFZvds"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "😴 *Трекер сна*\n\n"
        "Я помогу тебе отслеживать сон!\n"
        "Просто нажимай на кнопки ниже.",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="😴 Записать сон")],
                [types.KeyboardButton(text="📊 Статистика")],
                [types.KeyboardButton(text="💡 Советы")]
            ],
            resize_keyboard=True
        )
    )

@dp.message_handler(lambda msg: msg.text == "😴 Записать сон")
async def log_sleep(message: types.Message):
    await message.answer("🛌 Сколько часов ты спал? (например: 7.5)")

@dp.message_handler(lambda msg: msg.text == "📊 Статистика")
async def stats(message: types.Message):
    await message.answer("📊 Скоро здесь будет статистика!")

@dp.message_handler(lambda msg: msg.text == "💡 Советы")
async def advice(message: types.Message):
    await message.answer("💡 Советы появятся после 3 дней записей!")

@dp.message_handler()
async def handle_sleep(message: types.Message):
    try:
        hours = float(message.text.replace(",", "."))
        await message.answer(f"✅ Записано! Ты спал {hours} часов.\n\nОцени качество сна (1-10):")
    except ValueError:
        await message.answer("❌ Введи число, например: 7.5")

if __name__ == '__main__':
    print("✅ Бот запущен на Railway!")
    executor.start_polling(dp, skip_updates=True)
