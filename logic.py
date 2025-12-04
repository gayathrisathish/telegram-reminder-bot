import dateparser
from db import add_reminder
from scheduler import schedule_job

DATEPARSER_SETTINGS = {
    'TIMEZONE': 'Asia/Kolkata',
    'RETURN_AS_TIMEZONE_AWARE': False
}

import dateparser
import pytz
from db import add_reminder
from scheduler import schedule_job

DATEPARSER_SETTINGS = {
    'TIMEZONE': 'Asia/Kolkata',
    'RETURN_AS_TIMEZONE_AWARE': False
}

def process_message(text):
    text = text.lower().strip()

    if not text.startswith("remind me"):
        return "Please start your reminder with 'remind me ...'"

    if " to " not in text:
        return "Please use: remind me <time> to <task>"

    # Split message
    parts = text.split(" to ", 1)
    time_part = parts[0].replace("remind me", "").strip()
    task = parts[1].strip()

    # Parse time
    reminder_time = dateparser.parse(time_part, settings=DATEPARSER_SETTINGS)
    if reminder_time is None:
        return "I couldn't understand the time."

    # ---- FIX: make datetime timezone aware ----
    ist = pytz.timezone("Asia/Kolkata")
    reminder_time = ist.localize(reminder_time.replace(microsecond=0))
    # -------------------------------------------

    # Save to DB
    time_str = reminder_time.strftime("%Y-%m-%d %H:%M:%S")
    reminder_id = add_reminder(time_str, task)

    # Schedule it
    schedule_job(reminder_id, reminder_time, task)

    return f"Saved! I will remind you at {time_str} to '{task}'."
