from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

from db import get_pending_reminders, mark_sent
from utils import send_message

# Global variable for storing Telegram chat_id
user_chat_id = None


def set_chat_id(cid):
    global user_chat_id
    user_chat_id = cid
    print(f"[scheduler] Chat ID set to: {cid}")


scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def _send_and_mark(reminder_id, task):
    if user_chat_id is None:
        print(f"[scheduler] No chat ID — cannot send reminder {reminder_id}")
        return

    try:
        send_message(user_chat_id, f"🔔 Reminder: {task}")
        mark_sent(reminder_id)
        print(f"[scheduler] Sent reminder {reminder_id}: {task}")

    except Exception as e:
        print(f"[scheduler] Error sending reminder {reminder_id}: {e}")


def schedule_job(reminder_id, run_dt, task):
    # Ensure datetime is timezone-aware
    ist = pytz.timezone("Asia/Kolkata")
    
    if run_dt.tzinfo is None:
        run_dt = ist.localize(run_dt)

    try:
        scheduler.add_job(
            func=_send_and_mark,
            trigger="date",
            run_date=run_dt,
            args=[reminder_id, task],
            id=str(reminder_id),
            replace_existing=True
        )
        print(f"[scheduler] Scheduled reminder id={reminder_id} at {run_dt} -> {task}")

    except Exception as e:
        print(f"[scheduler] Failed to schedule reminder {reminder_id}: {e}")


def load_and_schedule_pending():
    reminders = get_pending_reminders()
    now = datetime.now(pytz.timezone("Asia/Kolkata"))

    print(f"[scheduler] Loading {len(reminders)} pending reminders...")

    for reminder_id, time_str, task in reminders:
        try:
            # Parse stored ISO string
            run_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            run_dt = pytz.timezone("Asia/Kolkata").localize(run_dt)

            if run_dt > now:
                schedule_job(reminder_id, run_dt, task)
            else:
                mark_sent(reminder_id)
                print(f"[scheduler] Marked reminder {reminder_id} as sent (past time).")

        except Exception as e:
            print(f"[scheduler] Error loading reminder {reminder_id}: {e}")


def start_scheduler():
    scheduler.start()
    print("[scheduler] APScheduler started.")
