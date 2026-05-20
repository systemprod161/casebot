import asyncio
import json
import websockets
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from collections import defaultdict

TOKEN = "8701511595:AAFr8dOEvt2O3nP3LqqbahuTvci5tX0jYkM"

WS_URL = "wss://ws3.gamecontent.io/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

drops_history = []
case_stats = defaultdict(list)

users = set()


# ===== AI ANALYZER =====

def analyze_case(case_name):
    history = case_stats.get(case_name, [])

    if len(history) < 5:
        return "Недостаточно данных"

    avg = sum(history) / len(history)

    last = history[-5:]

    high = sum(1 for x in last if x > avg)

    if high >= 4:
        return "🔥 Кейс перегрет — лучше пропустить"

    if high <= 1:
        return "🟢 Возможен хороший прокрут"

    return "🟡 Нейтрально"


# ===== TELEGRAM =====

@dp.message(Command("start"))
async def start(message: Message):
    users.add(message.chat.id)

    text = (
        "✅ AI Case Bot запущен\n\n"
        "/stats - статистика\n"
        "/top - топ дропов\n"
        "/predict - AI прогноз"
    )

    await message.answer(text)


@dp.message(Command("stats"))
async def stats(message: Message):

    total = len(drops_history)

    if total == 0:
        await message.answer("Нет данных")
        return

    avg = sum(d["price"] for d in drops_history) / total

    text = (
        f"📊 Всего дропов: {total}\n"
        f"💰 Средняя цена: {round(avg, 2)}"
    )

    await message.answer(text)


@dp.message(Command("top"))
async def top(message: Message):

    if not drops_history:
        await message.answer("Нет данных")
        return

    top_drops = sorted(
        drops_history,
        key=lambda x: x["price"],
        reverse=True
    )[:10]

    text = "🏆 ТОП ДРОПОВ\n\n"

    for d in top_drops:
        text += (
            f"{d['title']}\n"
            f"💰 {d['price']}$\n"
            f"📦 {d['case']}\n\n"
        )

    await message.answer(text)


@dp.message(Command("predict"))
async def predict(message: Message):

    if not case_stats:
        await message.answer("Нет данных")
        return

    text = "🤖 AI ПРОГНОЗЫ\n\n"

    for case_name in list(case_stats.keys())[:10]:
        result = analyze_case(case_name)

        text += (
            f"📦 {case_name}\n"
            f"{result}\n\n"
        )

    await message.answer(text)


# ===== WEBSOCKET =====

async def websocket_worker():

    while True:

        try:
            async with websockets.connect(WS_URL) as ws:

                print("CONNECTED TO WS")

                while True:

                    message = await ws.recv()

                    try:
                        data = json.loads(message)

                    except:
                        continue

                    if not isinstance(data, dict):
                        continue

                    # live drops
                    if "ld" in data:

                        drops = data["ld"]

                        for drop in drops:

                            try:

                                asset = drop.get("asset", {})
                                case = drop.get("case", {})

                                title = asset.get("title", "Unknown")
                                price = float(drop.get("price", 0))
                                rarity = asset.get("rarity", "unknown")

                                case_name = case.get("title", "Unknown Case")

                                drop_data = {
                                    "title": title,
                                    "price": price,
                                    "rarity": rarity,
                                    "case": case_name
                                }

                                drops_history.append(drop_data)

                                case_stats[case_name].append(price)

                                print(drop_data)

                                # дорогие дропы
                                if price >= 100:

                                    text = (
                                        f"💎 ДОРОГОЙ ДРОП\n\n"
                                        f"🔫 {title}\n"
                                        f"💰 {price}$\n"
                                        f"📦 {case_name}"
                                    )

                                    for user_id in users:
                                        try:
                                            await bot.send_message(
                                                user_id,
                                                text
                                            )
                                        except:
                                            pass

                            except Exception as e:
                                print(e)

        except Exception as e:
            print("WS ERROR:", e)

        await asyncio.sleep(5)


# ===== MAIN =====

async def main():

    ws_task = asyncio.create_task(
        websocket_worker()
    )

    bot_task = asyncio.create_task(
        dp.start_polling(bot)
    )

    await asyncio.gather(
        ws_task,
        bot_task
    )


if __name__ == "__main__":
    asyncio.run(main())