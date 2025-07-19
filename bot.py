import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN
import aiohttp
from bs4 import BeautifulSoup

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

async def fetch_tonnel_gifts():
    url = "https://tonnel.market/gifts"
    gifts = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("div", class_="gift-card")
            for card in cards:
                try:
                    name = card.find("div", class_="gift-name").text.strip()
                    price = float(card.find("div", class_="gift-price").text.replace("TON", "").strip())
                    gifts.append({"name": name, "price": price, "market": "tonnel"})
                except:
                    continue
    return gifts

async def fetch_portals_gifts():
    url = "https://portals.market/gifts"
    gifts = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("div", class_="gift-card")
            for card in cards:
                try:
                    name = card.find("div", class_="gift-name").text.strip()
                    price = float(card.find("div", class_="gift-price").text.replace("TON", "").strip())
                    gifts.append({"name": name, "price": price, "market": "portals"})
                except:
                    continue
    return gifts

def analyze_arbitrage(tonnel_data, portals_data, min_price=1, max_price=1000):
    results = []
    commission = 0.05
    portals_dict = {item['name']: item for item in portals_data}
    tonnel_dict = {item['name']: item for item in tonnel_data}
    all_names = set(portals_dict.keys()) & set(tonnel_dict.keys())

    for name in all_names:
        p_price = portals_dict[name]['price']
        t_price = tonnel_dict[name]['price']

        # Tonnel → Portals
        buy_price = t_price
        sell_price = p_price * (1 - commission)
        profit = sell_price - buy_price
        if min_price <= buy_price <= max_price and profit > 0.3:
            results.append({
                "gift": name,
                "buy_market": "Tonnel",
                "buy_price": round(buy_price, 2),
                "sell_market": "Portals",
                "sell_price": round(sell_price, 2),
                "profit": round(profit, 2)
            })

        # Portals → Tonnel
        buy_price = p_price
        sell_price = t_price * (1 - commission)
        profit = sell_price - buy_price
        if min_price <= buy_price <= max_price and profit > 0.3:
            results.append({
                "gift": name,
                "buy_market": "Portals",
                "buy_price": round(buy_price, 2),
                "sell_market": "Tonnel",
                "sell_price": round(sell_price, 2),
                "profit": round(profit, 2)
            })

    return sorted(results, key=lambda x: x["profit"], reverse=True)

@dp.message(F.text == "/analyze")
async def cmd_analyze(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="1–10 TON")],
        [KeyboardButton(text="10–20 TON")],
        [KeyboardButton(text="20+ TON")]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Выбери диапазон TON:", reply_markup=kb)

@dp.message(F.text.in_(["1–10 TON", "10–20 TON", "20+ TON"]))
async def handle_range(message: Message):
    await message.answer("🔄 Анализирую рынок, подожди...")

    tonnel = await fetch_tonnel_gifts()
    portals = await fetch_portals_gifts()

    if message.text == "1–10 TON":
        min_price, max_price = 1, 10
    elif message.text == "10–20 TON":
        min_price, max_price = 10, 20
    else:
        min_price, max_price = 20, 9999

    results = analyze_arbitrage(tonnel, portals, min_price, max_price)

    if not results:
        await message.answer("❌ Ничего не найдено.")
        return

    for item in results[:5]:
        text = (
            f"🎁 <b>{item['gift']}</b>\n"
            f"Купить на: <b>{item['buy_market']}</b> за <b>{item['buy_price']} TON</b>\n"
            f"Продать на: <b>{item['sell_market']}</b> за <b>{item['sell_price']} TON</b>\n"
            f"💰 Профит: <b>{item['profit']} TON</b>"
        )
        await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
