import os
import sqlite3
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ========== ТОКЕН ==========
BOT_TOKEN = os.environ.get("8537321553:AAGF6sywXfiSs7bJEO9dPnw-GSS-cUFZvds") or "8537321553:AAGF6sywXfiSs7bJEO9dPnw-GSS-cUFZvds"

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
    conn.commit()
    conn.close()

def save_record(user_id, sleep_hours=None, sleep_quality=None, mood=None, went_to_bed=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    c.execute('SELECT id FROM sleep_logs WHERE user_id = ? AND date = ?', (user_id, today))
    row = c.fetchone()
    
    if row:
        updates = []
        params = []
        if sleep_hours is not None:
            updates.append("sleep_hours = ?")
            params.append(sleep_hours)
        if sleep_quality is not None:
            updates.append("sleep_quality = ?")
            params.append(sleep_quality)
        if mood is not None:
            updates.append("mood = ?")
            params.append(mood)
        if went_to_bed is not None:
            updates.append("went_to_bed = ?")
            params.append(went_to_bed)
        
        if updates:
            params.append(user_id)
            params.append(today)
            query = f"UPDATE sleep_logs SET {', '.join(updates)} WHERE user_id = ? AND date = ?"
            c.execute(query, params)
    else:
        c.execute('''INSERT INTO sleep_logs (user_id, date, sleep_hours, sleep_quality, mood, went_to_bed)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, today, sleep_hours, sleep_quality, mood, went_to_bed))
    
    conn.commit()
    conn.close()

def get_today_record(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute('''SELECT sleep_hours, sleep_quality, mood, went_to_bed FROM sleep_logs 
                 WHERE user_id = ? AND date = ?''', (user_id, today))
    row = c.fetchone()
    conn.close()
    return row

def get_stats(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute('''SELECT date, sleep_hours, sleep_quality, mood FROM sleep_logs 
                 WHERE user_id = ? AND date >= ? ORDER BY date''',
              (user_id, week_ago))
    data = c.fetchall()
    conn.close()
    return data

# ========== БОТ ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ========== КЛАВИАТУРЫ ==========

main_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="🕐 Часы сна")],
        [types.KeyboardButton(text="⭐ Качество сна")],
        [types.KeyboardButton(text="😊 Настроение")],
        [types.KeyboardButton(text="🛏️ Время отхода")],
        [types.KeyboardButton(text="📊 Статистика")]
    ],
    resize_keyboard=True
)

hours_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="6"), types.KeyboardButton(text="7"), types.KeyboardButton(text="8")],
        [types.KeyboardButton(text="9"), types.KeyboardButton(text="10")],
        [types.KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

numbers_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="1"), types.KeyboardButton(text="2"), types.KeyboardButton(text="3"), 
         types.KeyboardButton(text="4"), types.KeyboardButton(text="5")],
        [types.KeyboardButton(text="6"), types.KeyboardButton(text="7"), types.KeyboardButton(text="8"), 
         types.KeyboardButton(text="9"), types.KeyboardButton(text="10")],
        [types.KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

time_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="23:00"), types.KeyboardButton(text="23:30")],
        [types.KeyboardButton(text="00:00"), types.KeyboardButton(text="00:30")],
        [types.KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

# ========== СОСТОЯНИЯ ==========
user_state = {}

# ========== ОБРАБОТЧИКИ ==========

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    init_db()
    await message.answer(
        "😴 *Трекер сна*\n\n"
        "Нажимай на кнопки, чтобы заполнить данные за сегодня.\n"
        "📊 Статистика — данные за 7 дней.",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message_handler(lambda msg: msg.text == "🕐 Часы сна")
async def set_hours(message: types.Message):
    user_state[message.from_user.id] = "hours"
    await message.answer(
        "🕐 Выбери сколько часов спал:",
        reply_markup=hours_keyboard
    )

@dp.message_handler(lambda msg: msg.text == "⭐ Качество сна")
async def set_quality(message: types.Message):
    user_state[message.from_user.id] = "quality"
    await message.answer(
        "⭐ Оцени качество сна (1-10):",
        reply_markup=numbers_keyboard
    )

@dp.message_handler(lambda msg: msg.text == "😊 Настроение")
async def set_mood(message: types.Message):
    user_state[message.from_user.id] = "mood"
    await message.answer(
        "😊 Оцени настроение (1-10):",
        reply_markup=numbers_keyboard
    )

@dp.message_handler(lambda msg: msg.text == "🛏️ Время отхода")
async def set_bed_time(message: types.Message):
    user_state[message.from_user.id] = "bed_time"
    await message.answer(
        "🛏️ Выбери время или введи своё (ЧЧ:ММ):",
        reply_markup=time_keyboard
    )

@dp.message_handler(lambda msg: msg.text == "📊 Статистика")
async def show_stats(message: types.Message):
    data = get_stats(message.from_user.id)
    if not data:
        await message.answer("📭 Нет данных за 7 дней.", reply_markup=main_keyboard)
        return
    
    text = "📊 *Статистика за 7 дней:*\n\n"
    for day, hours, quality, mood in data:
        date = datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m")
        hours_str = f"{hours}ч" if hours else "❌"
        quality_str = f"{quality}/10" if quality else "❌"
        mood_str = f"{mood}/10" if mood else "❌"
        text += f"📅 {date}: {hours_str}, ⭐ {quality_str}, 😊 {mood_str}\n"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message_handler(lambda msg: msg.text == "❌ Отмена")
async def cancel(message: types.Message):
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    await message.answer("❌ Отменено!", reply_markup=main_keyboard)

# ========== ОБРАБОТКА ВВОДА ==========

@dp.message_handler()
async def handle_input(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_state:
        await message.answer("Используй кнопки!", reply_markup=main_keyboard)
        return
    
    action = user_state[user_id]
    text = message.text
    
    if action == "hours":
        try:
            hours = float(text.replace(",", "."))
            save_record(user_id, sleep_hours=hours)
            del user_state[user_id]
            await message.answer(f"✅ Часы сна: {hours} ч", reply_markup=main_keyboard)
        except ValueError:
            await message.answer("❌ Введи число", reply_markup=hours_keyboard)
    
    elif action in ["quality", "mood"]:
        try:
            value = int(text)
            if value < 1 or value > 10:
                await message.answer("❌ От 1 до 10")
                return
            if action == "quality":
                save_record(user_id, sleep_quality=value)
                await message.answer(f"✅ Качество сна: {value}/10", reply_markup=main_keyboard)
            else:
                save_record(user_id, mood=value)
                await message.answer(f"✅ Настроение: {value}/10", reply_markup=main_keyboard)
            del user_state[user_id]
        except ValueError:
            await message.answer("❌ Введи число от 1 до 10")
    
    elif action == "bed_time":
        try:
            datetime.strptime(text, "%H:%M")
            save_record(user_id, went_to_bed=text)
            del user_state[user_id]
            await message.answer(f"✅ Время отхода: {text}", reply_markup=main_keyboard)
        except ValueError:
            await message.answer("❌ Формат ЧЧ:ММ, например: 23:30")

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    init_db()
    print("✅ Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
