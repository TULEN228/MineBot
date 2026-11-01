
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# Настройки
TOKEN = os.getenv("9072460110:AAET_MCz6Wpn5qZ8zgP3Aey6_T7YZPoO3kM")
OWNER_ID = int(os.getenv("6958726014"))
GROUP_ID = int(os.getenv("-1004445854725"))

STATE_FILE = os.getenv("STATE_FILE", "status.txt")


# Получение состояния сервера
def get_status():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as file:
            return file.read().strip()

    return "off"


# Сохранение состояния
def save_status(status):
    with open(STATE_FILE, "w") as file:
        file.write(status)


# Команды владельца: /on и /off
async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Только владелец в личных сообщениях
    if chat.type != "private" or user.id != OWNER_ID:
        return

    command = update.message.text.split()[0].split("@")[0]

    if command == "/on":
        save_status("on")
        await update.message.reply_text(
            "🟢 Сервер включён!"
        )

    elif command == "/off":
        save_status("off")
        await update.message.reply_text(
            "🔴 Сервер выключен!"
        )


# Команда /status в группе
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    if get_status() == "on":
        message = "🟢 Сервер включён!"
    else:
        message = "🔴 Сервер выключен!"

    await update.message.reply_text(message)


# Команда /alert в группе
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user

    if user.username:
        name = "@" + user.username
    else:
        name = user.full_name

    time = datetime.now(ZoneInfo("Asia/Tashkent"))
    formatted_time = time.strftime("%H:%M")

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            "⚠️ Запрос на включение сервера!\n\n"
            f"👤 Пользователь: {name}\n"
            f"🕒 Время: {formatted_time}"
        )
    )

    await update.message.reply_text(
        "✅ Запрос отправлен владельцу!"
    )


# Запуск бота
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler(["on", "off"], set_status))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("alert", alert))

    print("Bot started!")

    app.run_polling()


if __name__ == "__main__":
    main()
