from telegram.ext import Updater, MessageHandler, Filters
from logic import process_message
from utils import set_telegram_sender
import scheduler
from db import create_table

# ----- BOT TOKEN -----
from os import getenv
BOT_TOKEN = getenv("BOT_TOKEN")
# ----------------------
def show_id(update, context):
    chat_id = update.effective_chat.id
    print(f"[bot] Your chat_id is: {chat_id}")
    context.bot.send_message(chat_id=chat_id, text=f"Your chat_id is: {chat_id}")



def handle_message(update, context):
    user_text = update.message.text
    print("[bot] Received:", user_text)

    # ---- VERY IMPORTANT ----
    from scheduler import set_chat_id
    set_chat_id(update.effective_chat.id)
    # ------------------------

    response = process_message(user_text)
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)
def show_id(update, context):
    chat_id = update.effective_chat.id
    print(f"[bot] Your chat_id is: {chat_id}")
    context.bot.send_message(chat_id=chat_id, text=f"Your chat_id is: {chat_id}")
    dp.add_handler(MessageHandler(Filters.regex('^my id$'), show_id))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))



def main():
    print("Telegram bot running...")

    # Setup DB + Scheduler
    create_table()
    scheduler.load_and_schedule_pending()
    scheduler.start_scheduler()

    # Setup bot instance for sending messages
    set_telegram_sender(BOT_TOKEN)

    # Create updater (sync)
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(MessageHandler(Filters.regex('^my id$'), show_id))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start polling
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
