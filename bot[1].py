import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN

# Логи
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Временный доступ
user_access = {}
ACCESS_DURATION = timedelta(hours=24)

def has_access(user_id: int) -> bool:
    return user_id in user_access and datetime.now() < user_access[user_id]

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    user_access[message.from_user.id] = datetime.now() + ACCESS_DURATION
    await message.answer("✅ Бот работает! Доступ активирован на 24 часа.")

@dp.message(F.text == "/status")
async def cmd_status(message: Message):
    uid = message.from_user.id
    if has_access(uid):
        left = user_access[uid] - datetime.now()
        h, m = divmod(left.total_seconds(), 3600)
        m = int(m // 60)
        await message.answer(f"🕐 Доступ активен. Осталось: {int(h)} ч {m} мин.")
    else:
        await message.answer("❌ Доступ истёк. Обратитесь к администратору.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())