import os
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ========== ТОКЕН ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "ВАШ_ТОКЕН"

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
        age_group TEXT,
        remind_time TEXT
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

def delete_user_data(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM sleep_logs WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# ========== БОТ ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== СОСТОЯНИЯ ==========
class SleepForm(StatesGroup):
    waiting_for_sleep = State()
    waiting_for_quality = State()
    waiting_for_mood = State()
    waiting_for_wake_time = State()

# ========== КЛАВИАТУРЫ ==========

# Главная клавиатура (кнопки внизу экрана)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="😴 Записать сон")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="💡 Советы")],
        [KeyboardButton(text="⏰ Рассчитать время сна")]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора часов сна (быстрый ввод)
hours_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="6"), KeyboardButton(text="7"), KeyboardButton(text="8")],
        [KeyboardButton(text="9"), KeyboardButton(text="10"), KeyboardButton(text="Другое")]
    ],
    resize_keyboard=True
)

# Клавиатура для оценки качества (1-10)
quality_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3"), KeyboardButton(text="4"), KeyboardButton(text="5")],
        [KeyboardButton(text="6"), KeyboardButton(text="7"), KeyboardButton(text="8"), KeyboardButton(text="9"), KeyboardButton(text="10")]
    ],
    resize_keyboard=True
)

# Клавиатура для настроения (1-10)
mood_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3"), KeyboardButton(text="4"), KeyboardButton(text="5")],
        [KeyboardButton(text="6"), KeyboardButton(text="7"), KeyboardButton(text="8"), KeyboardButton(text="9"), KeyboardButton(text="10")]
    ],
    resize_keyboard=True
)

# Клавиатура для времени отхода ко сну
time_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="22:00"), KeyboardButton(text="23:00"), KeyboardButton(text="23:30")],
        [KeyboardButton(text="00:00"), KeyboardButton(text="00:30"), KeyboardButton(text="Другое")]
    ],
    resize_keyboard=True
)

# ========== ОБРАБОТЧИКИ ==========

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

# ========== ОБРАБОТКА КНОПОК ==========

@dp.message(lambda msg: msg.text == "😴 Записать сон")
async def log_sleep_start(message: types.Message, state: FSMContext):
    await state.set_state(SleepForm.waiting_for_sleep)
    await message.answer(
        "🛌 Сколько часов ты спал?\n\nВыбери из кнопок или введи своё число:",
        reply_markup=hours_keyboard
    )

@dp.message(lambda msg: msg.text == "📊 Статистика")
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    data = get_last_7_days(user_id)
    
    if not data:
        await message.answer("📭 Нет данных за 7 дней. Запиши свой сон!")
    else:
        text = "📊 *Статистика за 7 дней:*\n\n"
        for day, hours, quality, mood in data:
            date = datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m")
            text += f"📅 {date}: {hours}ч, качество {quality}/10, настроение {mood}/10\n"
        await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(lambda msg: msg.text == "💡 Советы")
async def show_advice(message: types.Message):
    user_id = message.from_user.id
    avg_h, avg_q, avg_m = get_avg_stats(user_id)
    
    if avg_h:
        text = "💡 *Советы:*\n\n"
        if avg_h < 7:
            text += "😴 Ты мало спишь. Попробуй ложиться на 30 минут раньше.\n"
        elif avg_h > 9:
            text += "💤 Ты много спишь. Возможно, нужно больше активности днём.\n"
        else:
            text += "✅ Сон в норме! Так держать.\n"
        if avg_q and avg_q < 5:
            text += "🌙 Качество сна низкое. Не сиди в телефоне перед сном."
        await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)
    else:
        await message.answer("📝 Запиши сон за 3 дня для советов.", reply_markup=main_keyboard)

@dp.message(lambda msg: msg.text == "⏰ Рассчитать время сна")
async def calculate_sleep(message: types.Message):
    await message.answer(
        "⏰ Во сколько ты просыпаешься?\n\nВведи время в формате ЧЧ:ММ (например: 07:30)",
        reply_markup=main_keyboard
    )

# ========== ОБРАБОТКА ВВОДА СНА ==========

@dp.message(SleepForm.waiting_for_sleep)
async def process_sleep(message: types.Message, state: FSMContext):
    try:
        if message.text == "Другое":
            await message.answer("Введи своё число (например: 7.5):")
            return
        
        hours = float(message.text.replace(",", "."))
        if hours < 0 or hours > 24:
            await message.answer("❌ Часы должны быть от 0 до 24")
            return
        
        await state.update_data(sleep_hours=hours)
        await state.set_state(SleepForm.waiting_for_quality)
        await message.answer(
            "⭐ Оцени качество сна от 1 до 10:",
            reply_markup=quality_keyboard
        )
    except ValueError:
        await message.answer("❌ Введи число, например: 7.5")

@dp.message(SleepForm.waiting_for_quality)
async def process_quality(message: types.Message, state: FSMContext):
    try:
        quality = int(message.text)
        if quality < 1 or quality > 10:
            await message.answer("❌ Оценка должна быть от 1 до 10")
            return
        
        await state.update_data(quality=quality)
        await state.set_state(SleepForm.waiting_for_mood)
        await message.answer(
            "😊 Оцени настроение сегодня от 1 до 10:",
            reply_markup=mood_keyboard
        )
    except ValueError:
        await message.answer("❌ Введи целое число от 1 до 10")

@dp.message(SleepForm.waiting_for_mood)
async def process_mood(message: types.Message, state: FSMContext):
    try:
        mood = int(message.text)
        if mood < 1 or mood > 10:
            await message.answer("❌ Оценка должна быть от 1 до 10")
            return
        
        await state.update_data(mood=mood)
        await state.set_state(SleepForm.waiting_for_wake_time)
        await message.answer(
            "🕐 Во сколько ты лёг спать?\n\nВыбери время или введи своё (ЧЧ:ММ):",
            reply_markup=time_keyboard
        )
    except ValueError:
        await message.answer("❌ Введи целое число от 1 до 10")

@dp.message(SleepForm.waiting_for_wake_time)
async def process_wake_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    time_text = message.text.strip()
    
    if time_text == "Другое":
        await message.answer("Введи время в формате ЧЧ:ММ (например: 23:30):")
        return
    
    try:
        datetime.strptime(time_text, "%H:%M")
        data = await state.get_data()
        
        add_sleep_record(
            user_id,
            data['sleep_hours'],
            data['quality'],
            data['mood'],
            time_text
        )
        
        await state.clear()
        await message.answer(
            f"✅ Запись сохранена!\n\n"
            f"💤 Сон: {data['sleep_hours']} ч\n"
            f"⭐ Качество: {data['quality']}/10\n"
            f"😊 Настроение: {data['mood']}/10\n"
            f"🕐 Лёг: {time_text}",
            reply_markup=main_keyboard
        )
    except ValueError:
        await message.answer("❌ Неправильный формат. Введи время как 23:30")

# ========== РАСЧЁТ ВРЕМЕНИ СНА ==========

@dp.message(lambda msg: msg.text and ":" in msg.text and not msg.text.startswith("/"))
async def calculate_time(message: types.Message):
    try:
        wake_time = message.text.strip()
        datetime.strptime(wake_time, "%H:%M")
        
        # Расчёт времени отхода ко сну (7.5 часов = 5 циклов по 90 минут)
        bed_time = (datetime.strptime(wake_time, "%H:%M") - timedelta(hours=7.5)).strftime("%H:%M")
        
        await message.answer(
            f"⏰ *Чтобы проснуться в {wake_time}:*\n\n"
            f"🛌 Ложись в *{bed_time}* — это 7.5 часов сна (5 циклов по 90 минут).\n\n"
            f"💡 Вставай между циклами — будешь бодрее!",
            parse_mode="Markdown",
            reply_markup=main_keyboard
        )
    except ValueError:
        pass  # Игнорируем, если это не время

# ========== ЕЖЕДНЕВНОЕ НАПОМИНАНИЕ ==========

async def daily_reminder():
    """Отправляет напоминание в 12:00 каждый день"""
    while True:
        now = datetime.now()
        # Следующее напоминание в 12:00
        target = now.replace(hour=12, minute=0, second=0, microsecond=0)
        
        if now >= target:
            # Если уже прошло 12:00, переносим на следующий день
            target += timedelta(days=1)
        
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        # Отправляем напоминание всем пользователям (просто в группу или по ID)
        # В этом примере просто логируем
        print(f"⏰ Напоминание: {datetime.now().strftime('%H:%M')} - Пора записать сон!")
        
        # Здесь можно отправить сообщение в чат (нужно знать chat_id)
        # Для простоты оставим только лог

# ========== ЗАПУСК ==========

async def main():
    init_db()
    
    # Запускаем задачу с напоминанием
    asyncio.create_task(daily_reminder())
    
    print("✅ Бот запущен!")
    print("⏰ Напоминания будут приходить в 12:00")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
