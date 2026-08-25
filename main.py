import os
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

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
        went_to_bed TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def get_today_record(user_id):
    """Получить запись за сегодня"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute('''SELECT sleep_hours, sleep_quality, mood, went_to_bed FROM sleep_logs 
                 WHERE user_id = ? AND date = ?''', (user_id, today))
    row = c.fetchone()
    conn.close()
    return row  # (hours, quality, mood, bed_time) или None

def save_record(user_id, sleep_hours=None, sleep_quality=None, mood=None, went_to_bed=None):
    """Сохранить или обновить запись"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    created_at = datetime.now().isoformat()
    
    # Проверяем, есть ли запись за сегодня
    c.execute('SELECT id FROM sleep_logs WHERE user_id = ? AND date = ?', (user_id, today))
    row = c.fetchone()
    
    if row:
        # Обновляем существующую запись
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
        # Создаём новую запись
        c.execute('''INSERT INTO sleep_logs (user_id, date, sleep_hours, sleep_quality, mood, went_to_bed, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, today, sleep_hours, sleep_quality, mood, went_to_bed, created_at))
    
    conn.commit()
    conn.close()

def get_stats(user_id, days=7):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    week_ago = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute('''SELECT date, sleep_hours, sleep_quality, mood FROM sleep_logs 
                 WHERE user_id = ? AND date >= ? ORDER BY date''',
              (user_id, week_ago))
    data = c.fetchall()
    conn.close()
    return data

def delete_today_record(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute('DELETE FROM sleep_logs WHERE user_id = ? AND date = ?', (user_id, today))
    conn.commit()
    conn.close()

# ========== БОТ ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== КЛАВИАТУРЫ ==========

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🕐 Часы сна"), KeyboardButton(text="⭐ Качество сна")],
        [KeyboardButton(text="😊 Настроение"), KeyboardButton(text="🛏️ Время отхода")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🗑️ Очистить сегодня")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора часов
hours_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="6"), KeyboardButton(text="7"), KeyboardButton(text="8")],
        [KeyboardButton(text="9"), KeyboardButton(text="10"), KeyboardButton(text="Отмена")]
    ],
    resize_keyboard=True
)

quality_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3"), KeyboardButton(text="4"), KeyboardButton(text="5")],
        [KeyboardButton(text="6"), KeyboardButton(text="7"), KeyboardButton(text="8"), KeyboardButton(text="9"), KeyboardButton(text="10")],
        [KeyboardButton(text="Отмена")]
    ],
    resize_keyboard=True
)

time_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="22:00"), KeyboardButton(text="23:00"), KeyboardButton(text="23:30")],
        [KeyboardButton(text="00:00"), KeyboardButton(text="00:30"), KeyboardButton(text="01:00")],
        [KeyboardButton(text="Отмена")]
    ],
    resize_keyboard=True
)

# ========== ОБРАБОТЧИКИ ==========

user_state = {}  # Временное состояние: {user_id: {"field": "hours"|"quality"|"mood"|"bed_time"}}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "😴 *Трекер сна*\n\n"
        "Я помогу тебе отслеживать сон!\n\n"
        "📌 *Как это работает:*\n"
        "1. Нажимай на кнопки, чтобы заполнить данные за сегодня\n"
        "2. Ты можешь заполнять их в любом порядке\n"
        "3. В 12:00 я буду напоминать тебе записать сон\n\n"
        "📊 Нажми *Статистика*, чтобы посмотреть свои данные за 7 дней.",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message(lambda msg: msg.text == "ℹ️ Помощь")
async def help_command(message: types.Message):
    await message.answer(
        "📖 *Помощь*\n\n"
        "🕐 *Часы сна* — сколько часов ты спал (6, 7, 8, 9, 10)\n"
        "⭐ *Качество сна* — оценка от 1 до 10\n"
        "😊 *Настроение* — оценка от 1 до 10\n"
        "🛏️ *Время отхода* — во сколько ты лёг спать\n"
        "📊 *Статистика* — данные за 7 дней\n"
        "🗑️ *Очистить сегодня* — удалить данные за сегодня\n\n"
        "Все данные сохраняются автоматически!",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message(lambda msg: msg.text == "🕐 Часы сна")
async def set_hours(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id] = {"field": "hours"}
    await message.answer(
        "🕐 Сколько часов ты спал?\n\nВыбери из кнопок:",
        reply_markup=hours_keyboard
    )

@dp.message(lambda msg: msg.text == "⭐ Качество сна")
async def set_quality(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id] = {"field": "quality"}
    await message.answer(
        "⭐ Оцени качество сна от 1 до 10:\n\n1 — ужасно, 10 — отлично",
        reply_markup=quality_keyboard
    )

@dp.message(lambda msg: msg.text == "😊 Настроение")
async def set_mood(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id] = {"field": "mood"}
    await message.answer(
        "😊 Оцени настроение от 1 до 10:\n\n1 — ужасно, 10 — отлично",
        reply_markup=quality_keyboard
    )

@dp.message(lambda msg: msg.text == "🛏️ Время отхода")
async def set_bed_time(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id] = {"field": "bed_time"}
    await message.answer(
        "🛏️ Во сколько ты лёг спать?\n\nВыбери время или введи своё (ЧЧ:ММ):",
        reply_markup=time_keyboard
    )

@dp.message(lambda msg: msg.text == "📊 Статистика")
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    data = get_stats(user_id)
    
    if not data:
        await message.answer(
            "📭 Нет данных за 7 дней.\n\n"
            "Начни записывать сон сегодня!",
            reply_markup=main_keyboard
        )
        return
    
    text = "📊 *Статистика за 7 дней:*\n\n"
    for day, hours, quality, mood in data:
        date = datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m")
        hours_str = f"{hours}ч" if hours else "❌"
        quality_str = f"{quality}/10" if quality else "❌"
        mood_str = f"{mood}/10" if mood else "❌"
        text += f"📅 {date}: {hours_str}, ⭐ {quality_str}, 😊 {mood_str}\n"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(lambda msg: msg.text == "🗑️ Очистить сегодня")
async def clear_today(message: types.Message):
    user_id = message.from_user.id
    delete_today_record(user_id)
    await message.answer(
        "🗑️ Данные за сегодня удалены!",
        reply_markup=main_keyboard
    )

@dp.message(lambda msg: msg.text == "Отмена")
async def cancel(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_state:
        del user_state[user_id]
    await message.answer(
        "❌ Отменено!",
        reply_markup=main_keyboard
    )

# ========== ОБРАБОТКА ВВОДА ==========

@dp.message(lambda msg: msg.text in ["6", "7", "8", "9", "10"])
async def process_hours_preset(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_state or user_state[user_id].get("field") != "hours":
        return
    
    hours = float(message.text)
    save_record(user_id, sleep_hours=hours)
    del user_state[user_id]
    
    await message.answer(
        f"✅ Часы сна сохранены: *{hours} ч*",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message(lambda msg: msg.text in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
async def process_quality_mood(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_state:
        return
    
    field = user_state[user_id].get("field")
    value = int(message.text)
    
    if field == "quality":
        save_record(user_id, sleep_quality=value)
        del user_state[user_id]
        await message.answer(
            f"✅ Качество сна сохранено: *{value}/10*",
            parse_mode="Markdown",
            reply_markup=main_keyboard
        )
    elif field == "mood":
        save_record(user_id, mood=value)
        del user_state[user_id]
        await message.answer(
            f"✅ Настроение сохранено: *{value}/10*",
            parse_mode="Markdown",
            reply_markup=main_keyboard
        )

@dp.message(lambda msg: msg.text in ["22:00", "23:00", "23:30", "00:00", "00:30", "01:00"])
async def process_time_preset(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_state or user_state[user_id].get("field") != "bed_time":
        return
    
    bed_time = message.text
    save_record(user_id, went_to_bed=bed_time)
    del user_state[user_id]
    
    await message.answer(
        f"✅ Время отхода сохранено: *{bed_time}*",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message()
async def process_custom_input(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_state:
        await message.answer(
            "Используй кнопки для управления ботом!",
            reply_markup=main_keyboard
        )
        return
    
    field = user_state[user_id].get("field")
    text = message.text.strip()
    
    if field == "hours":
        try:
            hours = float(text.replace(",", "."))
            if hours < 0 or hours > 24:
                await message.answer("❌ Часы должны быть от 0 до 24")
                return
            save_record(user_id, sleep_hours=hours)
            del user_state[user_id]
            await message.answer(
                f"✅ Часы сна сохранены: *{hours} ч*",
                parse_mode="Markdown",
                reply_markup=main_keyboard
            )
        except ValueError:
            await message.answer("❌ Введи число, например: 7.5")
    
    elif field == "quality":
        try:
            quality = int(text)
            if quality < 1 or quality > 10:
                await message.answer("❌ Оценка должна быть от 1 до 10")
                return
            save_record(user_id, sleep_quality=quality)
            del user_state[user_id]
            await message.answer(
                f"✅ Качество сна сохранено: *{quality}/10*",
                parse_mode="Markdown",
                reply_markup=main_keyboard
            )
        except ValueError:
            await message.answer("❌ Введи число от 1 до 10")
    
    elif field == "mood":
        try:
            mood = int(text)
            if mood < 1 or mood > 10:
                await message.answer("❌ Оценка должна быть от 1 до 10")
                return
            save_record(user_id, mood=mood)
            del user_state[user_id]
            await message.answer(
                f"✅ Настроение сохранено: *{mood}/10*",
                parse_mode="Markdown",
                reply_markup=main_keyboard
            )
        except ValueError:
            await message.answer("❌ Введи число от 1 до 10")
    
    elif field == "bed_time":
        try:
            datetime.strptime(text, "%H:%M")
            save_record(user_id, went_to_bed=text)
            del user_state[user_id]
            await message.answer(
                f"✅ Время отхода сохранено: *{text}*",
                parse_mode="Markdown",
                reply_markup=main_keyboard
            )
        except ValueError:
            await message.answer("❌ Введи время в формате ЧЧ:ММ, например: 23:30")

# ========== НАПОМИНАНИЕ ==========

async def daily_reminder():
    while True:
        now = datetime.now()
        target = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        print(f"⏰ [LOG] Напоминание в 12:00")

# ========== ЗАПУСК ==========

async def main():
    init_db()
    asyncio.create_task(daily_reminder())
    print("✅ Бот запущен!")
    print("⏰ Напоминания в 12:00")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
