from db import create_table, delete_reminder, get_pending_reminders_for_chat
from logic import process_message
import scheduler

LOCAL_CHAT_ID = 0

create_table()
scheduler.load_and_schedule_pending()
scheduler.start_scheduler()

print("=== Your Reminder Bot (local) ===")
print("Type a reminder like: remind me tomorrow at 5pm to study")
print("Local mode stores reminders with chat_id=0. Telegram delivery requires telegram_bot.py.")
print("Commands:")
print("  list               - list pending reminders")
print("  cancel <id>        - cancel a reminder by id")
print("  quit               - exit")

try:
    while True:
        msg = input("\nYou: ").strip()
        if not msg:
            continue

        if msg.lower() == "quit":
            print("Bye — shutting down.")
            break

        if msg.lower() == "list":
            items = get_pending_reminders_for_chat(LOCAL_CHAT_ID)
            if not items:
                print("No pending reminders.")
            else:
                print("Pending reminders:")
                for r in items:
                    print(
                        f"  id={r[0]}  time={r[1]}  task={r[2]}  timezone={r[3]}  recurrence={r[4]}"
                    )
            continue

        if msg.lower().startswith("cancel "):
            try:
                rid = int(msg.split(" ", 1)[1].strip())
                delete_reminder(rid, chat_id=LOCAL_CHAT_ID)
                scheduler.cancel_job(rid)
                print(f"Deleted reminder id={rid}")
            except Exception as e:
                print("Usage: cancel <id>  (example: cancel 3)")
            continue

        response = process_message(msg, chat_id=LOCAL_CHAT_ID)
        print("Bot:", response)

except KeyboardInterrupt:
    print("\nInterrupted, exiting.")
