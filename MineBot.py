
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# Настройки
TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])
GROUP_ID = int(os.environ["GROUP_ID"])
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
DATABASE_URL = os.environ["DATABASE_URL"]

logging.basicConfig(level=logging.INFO)

telegram_app = Application.builder().token(TOKEN).build()
db = None


# Получение и сохранение статуса через базу данных
async def get_status():
    result = await db.fetchval(
        "SELECT value FROM bot_state WHERE key = 'server_status'"
    )
    return result or "off"


async def save_status(status):
    await db.execute(
        """
        INSERT INTO bot_state (key, value)
        VALUES ('server_status', $1)
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value
        """,
        status
    )


# Команды владельца
async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != "private" or user.id != OWNER_ID:
        return

    command = update.message.text.split()[0].split("@")[0]

    if command == "/on":
        await save_status("on")
        await update.message.reply_text("🟢 Сервер включён!")

    elif command == "/off":
        await save_status("off")
        await update.message.reply_text("🔴 Сервер выключен!")


# Проверка статуса в группе
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    current = await get_status()

    if current == "on":
        message = "🟢 Сервер включён!"
    else:
        message = "🔴 Сервер выключен!"

    await update.message.reply_text(message)


# Запрос на включение сервера
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user

    if user.username:
        name = "@" + user.username
    else:
        name = user.full_name

    time = datetime.now(
        ZoneInfo("Asia/Tashkent")
    ).strftime("%H:%M")

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            "⚠️ Запрос на включение сервера!\n\n"
            f"👤 Пользователь: {name}\n"
            f"🕒 Время: {time}"
        )
    )

    await update.message.reply_text(
        "✅ Запрос отправлен владельцу!"
    )


# Запуск Telegram-обработчиков
telegram_app.add_handler(
    CommandHandler(["on", "off"], set_status)
)
telegram_app.add_handler(
    CommandHandler("status", status)
)
telegram_app.add_handler(
    CommandHandler("alert", alert)
)


# Запуск веб-сервера и Telegram-приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db

    db = await asyncpg.create_pool(DATABASE_URL)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    await db.execute("""
        INSERT INTO bot_state (key, value)
        VALUES ('server_status', 'off')
        ON CONFLICT (key) DO NOTHING
    """)

    await telegram_app.initialize()
    await telegram_app.start()

    logging.info("Telegram bot started!")

    yield

    await telegram_app.stop()
    await telegram_app.shutdown()
    await db.close()


app = FastAPI(lifespan=lifespan)


# Проверка работы сайта
@app.get("/")
async def home():
    return {"status": "Bot is running!"}


# Webhook Telegram
@app.post("/telegram")
async def telegram_webhook(request: Request):

    secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    )

    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()

    update = Update.de_json(data, telegram_app.bot)

    await telegram_app.process_update(update)

    return {"ok": True}
