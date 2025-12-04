from db import create_table, get_pending_reminders, delete_reminder
from logic import process_message
import scheduler

import threading
import time

# initialize DB and scheduler
create_table()
scheduler.load_and_schedule_pending()
scheduler.start_scheduler()

print("=== Your Reminder Bot (local) ===")
print("Type a reminder like: remind me tomorrow at 5pm to study")
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
            items = get_pending_reminders()
            if not items:
                print("No pending reminders.")
            else:
                print("Pending reminders:")
                for r in items:
                    print(f"  id={r[0]}  time={r[1]}  task={r[2]}")
            continue

        if msg.lower().startswith("cancel "):
            try:
                rid = int(msg.split(" ", 1)[1].strip())
                delete_reminder(rid)
                # attempt to remove scheduled job if present
                try:
                    scheduler.scheduler.remove_job(str(rid))
                except Exception:
                    pass
                print(f"Deleted reminder id={rid}")
            except Exception as e:
                print("Usage: cancel <id>  (example: cancel 3)")
            continue

        # otherwise treat input as a reminder command
        response = process_message(msg)
        print("Bot:", response)

except KeyboardInterrupt:
    print("\nInterrupted, exiting.")
