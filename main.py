import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ========== ТОКЕН (ЗАМЕНИ!) ==========
BOT_TOKEN = "8537321553:AAGF6sywXfiSs7bJEO9dPnw-GSS-cUFZvds"

# ========== БАЗА ДАННЫХ ==========
DB_NAME = "sleep_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sleep_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        sleep_hours REAL,
        sleep_quality INTEGER,
        mood INTEGER,
        went_to_bed TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        age_group TEXT
    )''')
    conn.commit()
    conn.close()

def add_sleep_record(user_id, sleep_hours, quality, mood, went_to_bed):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    c.execute('''INSERT INTO sleep_logs (user_id, date, sleep_hours, sleep_quality, mood, went_to_bed)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, date, sleep_hours, quality, mood, went_to_bed))
    conn.commit()
    conn.close()

def get_last_7_days(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute('''SELECT date, sleep_hours, sleep_quality, mood FROM sleep_logs 
                 WHERE user_id = ? AND date >= ? ORDER BY date''',
              (user_id, week_ago))
    data = c.fetchall()
    conn.close()
    return data

def get_user_age_group(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT age_group FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_user_age_group(user_id, age_group):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, age_group) VALUES (?, ?)',
              (user_id, age_group))
    conn.commit()
    conn.close()

def get_avg_stats(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute('''SELECT AVG(sleep_hours), AVG(sleep_quality), AVG(mood) FROM sleep_logs 
                 WHERE user_id = ? AND date >= ?''',
              (user_id, week_ago))
    row = c.fetchone()
    conn.close()
    return row if row else (None, None, None)

# ========== БОТ ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SleepForm(StatesGroup):
    waiting_for_age = State()
    waiting_for_sleep = State()
    waiting_for_quality = State()
    waiting_for_mood = State()
    waiting_for_wake_time = State()
    waiting_for_custom_time = State()

main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="😴 Записать сон", callback_data="log_sleep")],
    [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
    [InlineKeyboardButton(text="💡 Советы", callback_data="advice")],
    [InlineKeyboardButton(text="⏰ Рассчитать время сна", callback_data="calculate")]
])

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    age_group = get_user_age_group(user_id)
    
    if not age_group:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="14-17 лет", callback_data="age_14-17")],
            [InlineKeyboardButton(text="18-25 лет", callback_data="age_18-25")],
            [InlineKeyboardButton(text="26-64 года", callback_data="age_26-64")],
            [InlineKeyboardButton(text="65+ лет", callback_data="age_65+")]
        ])
        await message.answer(
            "👋 Привет! Я трекер сна.\n\nСколько тебе лет?",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            "😴 *Трекер сна*\n\nЧто хочешь сделать?",
            parse_mode="Markdown",
            reply_markup=main_keyboard
        )

@dp.callback_query(lambda c: c.data.startswith("age_"))
async def set_age(callback: types.CallbackQuery):
    age_group = callback.data.replace("age_", "")
    set_user_age_group(callback.from_user.id, age_group)
    await callback.message.edit_text(
        f"✅ Возраст сохранён!\n\nТеперь пользуйся ботом:",
        reply_markup=main_keyboard
    )
    await callback.answer()

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    user_id = callback.from_user.id
    
    if action == "log_sleep":
        await state.set_state(SleepForm.waiting_for_sleep)
        await callback.message.answer("🛌 Сколько часов спал? (например: 7.5)")
        await callback.answer()
    
    elif action == "stats":
        data = get_last_7_days(user_id)
        if not data:
            await callback.message.answer("📭 Нет данных за 7 дней.")
        else:
            text = "📊 *Статистика за 7 дней:*\n\n"
            for day, hours, quality, mood in data:
                date = datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m")
                text += f"📅 {date}: {hours}ч, качество {quality}/10, настроение {mood}/10\n"
            await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()
    
    elif action == "advice":
        avg_h, avg_q, avg_m = get_avg_stats(user_id)
        if avg_h:
            text = f"💡 *Советы:*\n\n"
            if avg_h < 7:
                text += "😴 Ты мало спишь. Попробуй ложиться на 30 минут раньше.\n"
            elif avg_h > 9:
                text += "💤 Ты много спишь. Возможно, нужно больше активности днём.\n"
            else:
                text += "✅ Сон в норме! Так держать.\n"
            if avg_q and avg_q < 5:
                text += "🌙 Качество сна низкое. Не сиди в телефоне перед сном."
            await callback.message.answer(text, parse_mode="Markdown")
        else:
            await callback.message.answer("📝 Запиши сон за 3 дня для советов.")
        await callback.answer()
    
    elif action == "calculate":
        await state.set_state(SleepForm.waiting_for_custom_time)
        await callback.message.answer("⏰ Во сколько просыпаешься? (ЧЧ:ММ)")
        await callback.answer()

@dp.message(SleepForm.waiting_for_sleep)
async def process_sleep(message: Message, state: FSMContext):
    try:
        hours = float(message.text.replace(",", "."))
        await state.update_data(sleep_hours=hours)
        await state.set_state(SleepForm.waiting_for_quality)
        await message.answer("⭐ Оцени качество сна (1-10):")
    except ValueError:
        await message.answer("❌ Введи число")

@dp.message(SleepForm.waiting_for_quality)
async def process_quality(message: Message, state: FSMContext):
    try:
        quality = int(message.text)
        await state.update_data(quality=quality)
        await state.set_state(SleepForm.waiting_for_mood)
        await message.answer("😊 Оцени настроение (1-10):")
    except ValueError:
        await message.answer("❌ Введи число")

@dp.message(SleepForm.waiting_for_mood)
async def process_mood(message: Message, state: FSMContext):
    try:
        mood = int(message.text)
        await state.update_data(mood=mood)
        await state.set_state(SleepForm.waiting_for_wake_time)
        await message.answer("🕐 Во сколько лёг? (ЧЧ:ММ)")
    except ValueError:
        await message.answer("❌ Введи число")

@dp.message(SleepForm.waiting_for_wake_time)
async def process_wake(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
        data = await state.get_data()
        add_sleep_record(message.from_user.id, data['sleep_hours'], data['quality'], data['mood'], message.text)
        await state.clear()
        await message.answer(
            f"✅ Записано!\n💤 {data['sleep_hours']}ч\n⭐ {data['quality']}/10\n😊 {data['mood']}/10",
            reply_markup=main_keyboard
        )
    except ValueError:
        await message.answer("❌ Формат ЧЧ:ММ")

@dp.message(SleepForm.waiting_for_custom_time)
async def calculate_time(message: Message, state: FSMContext):
    try:
        wake_time = message.text.strip()
        datetime.strptime(wake_time, "%H:%M")
        # Простой расчёт: 7.5 часов сна = 5 циклов по 90 минут
        bed_time = (datetime.strptime(wake_time, "%H:%M") - timedelta(hours=7.5)).strftime("%H:%M")
        await state.clear()
        await message.answer(
            f"⏰ Чтобы проснуться в {wake_time},\n🛌 ложись в *{bed_time}* (7.5 часов сна)",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ Формат ЧЧ:ММ")

async def main():
    init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())