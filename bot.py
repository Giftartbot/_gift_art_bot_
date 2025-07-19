import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN
import requests
from bs4 import BeautifulSoup

# Настройки
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
user_access = {}
ACCESS_DURATION = timedelta(hours=24)

# Проверка доступа
def has_access(user_id: int) -> bool:
    return user_id in user_access and datetime.now() < user_access[user_id]

# Команда /start
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    user_access[message.from_user.id] = datetime.now() + ACCESS_DURATION
    await message.answer("✅ Доступ активирован на 24 часа.")

# Команда /status
@dp.message(F.text == "/status")
async def cmd_status(message: Message):
    uid = message.from_user.id
    if has_access(uid):
        left = user_access[uid] - datetime.now()
        h, m = divmod(left.total_seconds(), 3600)
        m = int(m // 60)
        await message.answer(f"🕐 Доступ активен. Осталось: {int(h)} ч {m} мин.")
    else:
        await message.answer("❌ Доступ истёк. Напиши администратору.")

# Парсинг Tonnel
def parse_tonnel():
    url = "https://tonnel.market/gifts"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for el in soup.select(".gift-card"):
            name = el.select_one(".gift-title").text.strip()
            price = float(el.select_one(".gift-price").text.replace("TON", "").strip())
            items.append({"name": name, "price": price})
        return items
    except Exception:
        return []

# Парсинг Portals
def parse_portals():
    url = "https://portals.market/gifts"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for el in soup.select(".gift-card"):
            name = el.select_one(".gift-title").text.strip()
            price = float(el.select_one(".gift-price").text.replace("TON", "").strip())
            items.append({"name": name, "price": price})
        return items
    except Exception:
        return []

# Команда /analyze
@dp.message(F.text == "/analyze")
async def cmd_analyze(message: Message):
    if not has_access(message.from_user.id):
        await message.answer("❌ Доступ истёк.")
        return

    await message.answer("🔍 Анализирую рынок...")

    tonnel = parse_tonnel()
    portals = parse_portals()
    result = []

    fee_buy = 0.03
    fee_sell = 0.05

    for t in tonnel:
        match = next((p for p in portals if p["name"] == t["name"]), None)
        if match:
            buy_price = t["price"] * (1 + fee_buy)
            sell_price = match["price"] * (1 - fee_sell)
            profit = round(sell_price - buy_price, 2)
            if profit > 0:
                result.append(f"🎁 <b>{t['name']}</b>\nКупить за: {t['price']} TON\nПродать за: {match['price']} TON\n💰 Прибыль: <b>{profit}</b> TON\n")

    if result:
        reply = "\n\n".join(result[:10])
    else:
        reply = "❌ Не найдено связок с прибылью."

    await message.answer(reply)

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

