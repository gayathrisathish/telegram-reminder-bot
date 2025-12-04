from telegram import Bot

# This global bot object will be shared across all imports.
bot_instance = None


def set_telegram_sender(token):
    global bot_instance
    bot_instance = Bot(token=token)
    print("[utils] Bot instance created")  # for debugging


def send_message(chat_id, text):
    from utils import bot_instance   # ensure it uses updated global object

    if bot_instance is None:
        print("[send_message] ERROR: bot_instance is None — set_telegram_sender() was not called yet.")
        return

    try:
        bot_instance.send_message(chat_id=chat_id, text=text)
        print(f"[send_message] Sent to {chat_id}: {text}")  # debugging
    except Exception as e:
        print(f"[send_message] ERROR sending to {chat_id}: {e}")
