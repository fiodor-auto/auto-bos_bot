"""
🚗 Auto Boss Bot - Telegram Bot для автомехаников
Функции: VIN расшифровка, поиск проблем, добавление решений, поиск запчастей
"""

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
import asyncio
import sqlite3
import aiohttp
import feedparser
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# ====================== ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======================
load_dotenv()

# ====================== ЛОГИРОВАНИЕ ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== НАСТРОЙКИ ======================
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "-100755229383"))
DATABASE_FILE = os.getenv("DATABASE_FILE", "car_problems.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not TOKEN:
    logger.error("❌ ОШИБКА: TOKEN не найден в .env файле!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ====================== БАЗА ДАННЫХ ======================
def init_database():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        cur = conn.cursor()

        cur.execute('''CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY,
            make TEXT,
            model TEXT,
            year TEXT,
            problem TEXT,
            solution TEXT,
            added_by TEXT,
            date TEXT
        )''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            joined_date TEXT
        )''')
        
        conn.commit()
        logger.info("✅ База данных инициализирована")
        return conn, cur
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return None, None

conn, cur = init_database()

# ====================== VIN РАСШИФРОВКА ======================
async def decode_vin(vin: str):
    """Расшифровка VIN через NHTSA API"""
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("Results", [{}])[0]
                else:
                    return None
    except asyncio.TimeoutError:
        logger.error("⏱️ Timeout при расшифровке VIN")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка VIN: {e}")
        return None

# ====================== ПОИСК ЗАПЧАСТЕЙ ======================
async def search_parts(query: str):
    """Поиск запчастей через eBay API (демонстрация)"""
    try:
        # Демонстрационный поиск - в реальном проекте используйте реальный API
        search_query = query.replace(" ", "%20")
        # Здесь можно добавить реальный API для поиска запчастей
        return [
            {"name": f"Запчасть: {query}", "price": "500$", "source": "eBay"},
            {"name": f"OEM {query}", "price": "800$", "source": "Amazon"}
        ]
    except Exception as e:
        logger.error(f"❌ Ошибка поиска запчастей: {e}")
        return []

# ====================== RSS НОВОСТИ ======================
async def get_auto_news():
    """Получение новостей об авто"""
    try:
        feed_url = "https://feeds.bloomberg.com/markets/news.rss"
        feed = feedparser.parse(feed_url)
        
        news = []
        for entry in feed.entries[:5]:
            news.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", "")
            })
        return news
    except Exception as e:
        logger.error(f"❌ Ошибка RSS: {e}")
        return []

# ====================== РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ ======================
def register_user(user_id: int, username: str, first_name: str):
    """Регистрация пользователя в БД"""
    try:
        cur.execute("""INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации пользователя: {e}")

# ====================== КОМАНДЫ ======================

@dp.message(Command("start"))
async def start(message: types.Message):
    """Команда /start - приветствие"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        first_name = message.from_user.first_name or "User"
        
        register_user(user_id, username, first_name)
        
        text = (
            "🚗 <b>Auto Boss Bot</b> — ваш помощник в автомеханике!\n\n"
            "<b>📋 Доступные команды:</b>\n"
            "/vin &lt;VIN&gt; — расшифровка VIN номера\n"
            "/problem &lt;марка&gt; &lt;модель&gt; — поиск частых проблем\n"
            "/search &lt;запчасть&gt; — поиск запчастей\n"
            "/addproblem — добавить проблему и решение\n"
            "/rss — автомобильные новости\n"
            "/help — справка\n\n"
            "<b>💡 Пример:</b> /vin WBA3A5C52EP600000"
        )
        await message.answer(text, parse_mode="HTML")
        logger.info(f"✅ Пользователь {username} запустил бота")
    except Exception as e:
        logger.error(f"❌ Ошибка /start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Команда /help - справка"""
    try:
        text = (
            "<b>🆘 Справка</b>\n\n"
            "<b>VIN Расшифровка:</b>\n"
            "Введите /vin и свой VIN номер\n"
            "Пример: /vin WBA3A5C52EP600000\n\n"
            "<b>Поиск проблем:</b>\n"
            "Используйте /problem марка модель\n"
            "Пример: /problem BMW 3Series\n\n"
            "<b>Поиск запчастей:</b>\n"
            "Введите /search название запчасти\n"
            "Пример: /search тормозные колодки\n\n"
            "<b>Добавить знание:</b>\n"
            "Используйте /addproblem и следуйте инструкциям\n\n"
            "<b>Новости:</b>\n"
            "Получайте последние новости авто через /rss"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Ошибка /help: {e}")
        await message.answer("❌ Ошибка получения справки.")

# ====================== VIN КОМАНДА ======================

@dp.message(Command("vin"))
async def vin_decode(message: types.Message):
    """Команда /vin - расшифровка VIN номера"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "❌ Использование: /vin &lt;VIN номер&gt;\n\n"
                "Пример: /vin WBA3A5C52EP600000",
                parse_mode="HTML"
            )
            return
        
        vin = parts[1].strip().upper()
        
        if len(vin) != 17:
            await message.answer("❌ VIN номер должен состоять из 17 символов")
            return
        
        await message.answer("🔍 <b>Расшифровываю VIN...</b>", parse_mode="HTML")
        
        result = await decode_vin(vin)
        
        if not result:
            await message.answer("❌ Не удалось расшифровать VIN. Проверьте номер.")
            return
        
        make = result.get("Make", "").capitalize() or "Unknown"
        model = result.get("Model", "").capitalize() or "Unknown"
        year = result.get("ModelYear", "—")
        body_class = result.get("VehicleType", "")
        engine = result.get("EngineDisplacement", "")
        
        text = f"✅ <b>Информация о ТС:</b>\n\n"
        text += f"🏭 <b>Марка:</b> {make}\n"
        text += f"🚗 <b>Модель:</b> {model}\n"
        text += f"📅 <b>Год:</b> {year}\n"
        text += f"📦 <b>Тип кузова:</b> {body_class}\n"
        if engine:
            text += f"⚙️ <b>Объём двигателя:</b> {engine}L\n"
        
        text += "\n" + "="*40 + "\n"
        
        # Поиск проблем по марке и модели
        try:
            cur.execute("SELECT problem, solution FROM problems WHERE make=? AND model=? LIMIT 5", 
                       (make, model))
            problems = cur.fetchall()
            
            if problems:
                text += "\n🔧 <b>Частые проблемы этой модели:</b>\n\n"
                for idx, (p, s) in enumerate(problems, 1):
                    text += f"<b>{idx}. �� {p}</b>\n"
                    text += f"   ✅ {s[:150]}...\n\n"
            else:
                text += "\n🔍 Пока нет записей проблем по этой модели в нашей базе."
        except Exception as e:
            logger.error(f"❌ Ошибка поиска проблем: {e}")
            text += "\n⚠️ Не удалось загрузить проблемы."
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /vin: {e}")
        await message.answer("❌ Произошла ошибка при расшифровке VIN")

# ====================== ПОИСК ПРОБЛЕМ ======================

@dp.message(Command("problem"))
async def search_problems(message: types.Message):
    """Команда /problem - поиск проблем по марке и модели"""
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(
                "❌ Использование: /problem &lt;марка&gt; &lt;модель&gt;\n\n"
                "Пример: /problem BMW 3Series",
                parse_mode="HTML"
            )
            return
        
        make = parts[1].capitalize()
        model = parts[2].capitalize()
        
        await message.answer(f"🔍 <b>Ищу проблемы для {make} {model}...</b>", parse_mode="HTML")
        
        cur.execute("SELECT problem, solution, added_by, date FROM problems WHERE make=? AND model=?", 
                   (make, model))
        problems = cur.fetchall()
        
        if not problems:
            await message.answer(
                f"❌ Нет записей для {make} {model}\n\n"
                f"Помогите базе! Используйте /addproblem",
                parse_mode="HTML"
            )
            return
        
        text = f"✅ <b>Проблемы {make} {model}:</b>\n\n"
        for idx, (problem, solution, author, date) in enumerate(problems, 1):
            text += f"<b>{idx}. ❓ {problem}</b>\n"
            text += f"   ✅ {solution}\n"
            text += f"   👤 Автор: {author} ({date})\n\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /problem: {e}")
        await message.answer("❌ Произошла ошибка при поиске проблем")

# ====================== ДОБАВЛЕНИЕ ПРОБЛЕМЫ ======================

user_states = {}

@dp.message(Command("addproblem"))
async def add_problem_start(message: types.Message):
    """Команда /addproblem - начало добавления проблемы"""
    try:
        user_id = message.from_user.id
        user_states[user_id] = {"step": "make"}
        
        text = (
            "➕ <b>Добавление проблемы в базу знаний</b>\n\n"
            "Спасибо за помощь сообществу! 🙏\n\n"
            "<b>Шаг 1:</b> Напишите <b>марку</b> автомобиля\n"
            "Пример: BMW, Mercedes, Toyota"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Ошибка /addproblem: {e}")
        await message.answer("❌ Произошла ошибка")

@dp.message(F.text)
async def handle_states(message: types.Message):
    """Обработка добавления проблемы пошагово"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            return
        
        state = user_states[user_id]
        text = message.text.strip()

        if state.get("step") == "make":
            state["make"] = text.capitalize()
            state["step"] = "model"
            await message.answer(
                f"✅ Марка: <b>{state['make']}</b>\n\n"
                "<b>Шаг 2:</b> Напишите <b>модель</b>\n"
                "Пример: 3Series, E-Class, Camry",
                parse_mode="HTML"
            )

        elif state.get("step") == "model":
            state["model"] = text.capitalize()
            state["step"] = "year"
            await message.answer(
                f"✅ Модель: <b>{state['model']}</b>\n\n"
                "<b>Шаг 3:</b> Напишите <b>год выпуска</b> (опционально)\n"
                "Пример: 2020 или 2015-2020",
                parse_mode="HTML"
            )

        elif state.get("step") == "year":
            state["year"] = text or "Any"
            state["step"] = "problem"
            await message.answer(
                f"✅ Год: <b>{state['year']}</b>\n\n"
                "<b>Шаг 4:</b> Опишите <b>проблему</b>\n"
                "Пример: Двигатель не запускается с первого раза",
                parse_mode="HTML"
            )

        elif state.get("step") == "problem":
            state["problem"] = text
            state["step"] = "solution"
            await message.answer(
                f"✅ Проблема: <b>{state['problem']}</b>\n\n"
                "<b>Шаг 5:</b> Напишите <b>решение</b>\n"
                "Пример: Заменить свечи зажигания на новые OEM",
                parse_mode="HTML"
            )

        elif state.get("step") == "solution":
            try:
                cur.execute("""INSERT INTO problems (make, model, year, problem, solution, added_by, date)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (state["make"], state["model"], state["year"], state["problem"], text,
                             message.from_user.first_name or "Anonymous", 
                             datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                
                await message.answer(
                    "✅ <b>Спасибо!</b>\n\n"
                    f"Проблема <b>{state['problem']}</b>\n"
                    f"добавлена в базу знаний для {state['make']} {state['model']}",
                    parse_mode="HTML"
                )
                del user_states[user_id]
                logger.info(f"✅ Новая проблема добавлена: {state['make']} {state['model']}")
            except Exception as e:
                logger.error(f"❌ Ошибка при сохранении: {e}")
                await message.answer("❌ Ошибка при сохранении. Попробуйте позже.")
                del user_states[user_id]

    except Exception as e:
        logger.error(f"❌ Ошибка обработки состояния: {e}")

# ====================== ПОИСК ЗАПЧАСТЕЙ ======================

@dp.message(Command("search"))
async def search_parts_command(message: types.Message):
    """Команда /search - поиск запчастей"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "❌ Использование: /search &lt;запчасть&gt;\n\n"
                "Пример: /search тормозные колодки",
                parse_mode="HTML"
            )
            return
        
        query = parts[1].strip()
        await message.answer(f"🔍 <b>Ищу запчасти: {query}</b>...", parse_mode="HTML")
        
        results = await search_parts(query)
        
        if not results:
            await message.answer("❌ Запчасти не найдены. Попробуйте другой поиск.")
            return
        
        text = f"✅ <b>Результаты поиска: {query}</b>\n\n"
        for idx, item in enumerate(results, 1):
            text += f"<b>{idx}. {item['name']}</b>\n"
            text += f"   💰 Цена: {item['price']}\n"
            text += f"   🌐 Источник: {item['source']}\n\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /search: {e}")
        await message.answer("❌ Произошла ошибка при поиске запчастей")

# ====================== RSS НОВОСТИ ======================

@dp.message(Command("rss"))
async def rss_news(message: types.Message):
    """Команда /rss - получение новостей об авто"""
    try:
        await message.answer("📰 <b>Загружаю новости авто...</b>", parse_mode="HTML")
        
        news = await get_auto_news()
        
        if not news:
            await message.answer("❌ Не удалось загрузить новости. Попробуйте позже.")
            return
        
        text = "📰 <b>Последние новости авто:</b>\n\n"
        for idx, item in enumerate(news, 1):
            text += f"<b>{idx}. {item['title'][:80]}</b>\n"
            text += f"   📅 {item['published'][:10]}\n"
            text += f"   🔗 <a href='{item['link']}'>Читать</a>\n\n"
        
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"❌ Ошибка /rss: {e}")
        await message.answer("❌ Произошла ошибка при загрузке новостей")

# ====================== ОСНОВНОЙ ЦИКЛ ======================

async def main():
    """Запуск бота"""
    try:
        logger.info("🤖 Auto Boss Bot запущен...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("⛔ Бот остановлен")
    finally:
        if conn:
            conn.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
