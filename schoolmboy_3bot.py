import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils import executor

TOKEN = "8543870086:AAHwUEFzbzEHKGZ_QBx-SKEjQLg_WDavr84"
ADMIN_ID = 5340788971

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- папка логов ---
if not os.path.exists("logs"):
    os.makedirs("logs")

queue = []
pairs = {}
likes = {}
user_data = {}

# --- клавиатуры ---
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("🔍 Найти собеседника")
main_kb.add("👤 Профиль")

chat_kb = ReplyKeyboardMarkup(resize_keyboard=True)
chat_kb.add("👍", "👎")
chat_kb.add("⏭ Следующий", "❌ Завершить")

admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_kb.add("📁 Логи", "👥 Пользователи")
admin_kb.add("🔙 В меню")

# --- регистрация ---
def register_user(user):
    if user.id not in user_data:
        user_data[user.id] = {
            "likes": 0,
            "username": user.username or "no_username",
            "name": user.first_name
        }

# --- логирование ---
def log_message(user_id, partner_id, username, text):
    filename = f"logs/chat_{min(user_id, partner_id)}_{max(user_id, partner_id)}.txt"
    time = datetime.now().strftime("%H:%M")

    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{time}] @{username}: {text}\n")

# --- старт ---
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    register_user(msg.from_user)

    await msg.answer(
        "👋 Добро пожаловать!\n\n💬 Анонимный чат\n❤️ Лайкай — получай мэтчи",
        reply_markup=main_kb
    )

# --- профиль ---
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    register_user(msg.from_user)

    user = user_data[msg.from_user.id]

    await msg.answer(
        f"👤 {user['name']}\n⭐ Рейтинг: {user['likes']}\n🔗 @{user['username']}"
    )

# --- поиск ---
@dp.message_handler(lambda m: m.text == "🔍 Найти собеседника")
async def find(msg: types.Message):
    register_user(msg.from_user)

    user_id = msg.from_user.id

    if user_id in pairs:
        await msg.answer("⚠️ Ты уже в диалоге")
        return

    if queue:
        partner = queue.pop(0)

        pairs[user_id] = partner
        pairs[partner] = user_id

        await bot.send_message(user_id, "💬 Собеседник найден!", reply_markup=chat_kb)
        await bot.send_message(partner, "💬 Собеседник найден!", reply_markup=chat_kb)
    else:
        queue.append(user_id)
        await msg.answer("🔎 Ищем собеседника...")

# --- лайк ---
@dp.message_handler(lambda m: m.text == "👍")
async def like(msg: types.Message):
    register_user(msg.from_user)

    user_id = msg.from_user.id

    if user_id not in pairs:
        return

    partner = pairs[user_id]

    likes.setdefault(user_id, set()).add(partner)

    await bot.send_message(partner, "❤️ Ты понравился собеседнику!")

    if partner in likes and user_id in likes[partner]:
        user_data[user_id]["likes"] += 1
        user_data[partner]["likes"] += 1

        await bot.send_message(user_id, f"🔥 МЭТЧ! @{user_data[partner]['username']}")
        await bot.send_message(partner, f"🔥 МЭТЧ! @{user_data[user_id]['username']}")
    else:
        await msg.answer("👍 Лайк отправлен")

# --- дизлайк ---
@dp.message_handler(lambda m: m.text == "👎")
async def dislike(msg: types.Message):
    await next_user(msg)

# --- следующий ---
@dp.message_handler(lambda m: m.text == "⏭ Следующий")
async def next_user(msg: types.Message):
    register_user(msg.from_user)

    user_id = msg.from_user.id

    if user_id in pairs:
        partner = pairs[user_id]

        pairs.pop(partner, None)
        pairs.pop(user_id, None)

        await bot.send_message(partner, "❌ Собеседник ушёл")

    if user_id in queue:
        queue.remove(user_id)

    await find(msg)

# --- стоп ---
@dp.message_handler(lambda m: m.text == "❌ Завершить")
async def stop(msg: types.Message):
    register_user(msg.from_user)

    user_id = msg.from_user.id

    if user_id in pairs:
        partner = pairs[user_id]

        pairs.pop(partner, None)
        pairs.pop(user_id, None)

        await bot.send_message(partner, "❌ Диалог завершён")

    if user_id in queue:
        queue.remove(user_id)

    await msg.answer("👋 Ты в меню", reply_markup=main_kb)

# ================= ADMIN =================

@dp.message_handler(commands=['admin'])
async def admin_panel(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    await msg.answer("👑 Админ-панель", reply_markup=admin_kb)

@dp.message_handler(lambda m: m.text == "📁 Логи")
async def logs(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    files = os.listdir("logs")
    if not files:
        await msg.answer("📭 Нет логов")
        return

    await msg.answer("📁 Логи:\n\n" + "\n".join(files[-10:]))

@dp.message_handler(lambda m: m.text.startswith("chat_"))
async def open_log(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    path = f"logs/{msg.text}"

    if not os.path.exists(path):
        await msg.answer("❌ Не найдено")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    await msg.answer(content[-4000:] if content else "Пусто")

@dp.message_handler(lambda m: m.text == "👥 Пользователи")
async def users(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    text = "\n".join(
        [f"{u['name']} (@{u['username']}) ⭐{u['likes']}" for u in user_data.values()]
    )

    await msg.answer(text or "Нет пользователей")

@dp.message_handler(lambda m: m.text == "🔙 В меню")
async def back(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    await msg.answer("Меню", reply_markup=main_kb)

# ================= ЧАТ =================

@dp.message_handler(lambda m: m.text and not m.text.startswith("/"))
async def chat(msg: types.Message):
    register_user(msg.from_user)

    user_id = msg.from_user.id

    if user_id in pairs:
        partner = pairs[user_id]
        username = msg.from_user.username or "no_username"

        log_message(user_id, partner, username, msg.text)

        await bot.send_message(partner, msg.text)
    else:
        if user_id != ADMIN_ID:
            await msg.answer("⚠️ Сначала найди собеседника")

# --- запуск ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)