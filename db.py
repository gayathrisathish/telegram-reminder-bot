import sqlite3

DB_NAME = "reminders.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def create_table():
    conn = get_connection()
    cursor = conn.cursor()

    # Correct schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            task TEXT,
            sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def add_reminder(time_str, task):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO reminders (time, task, sent) VALUES (?, ?, 0)",
        (time_str, task)
    )

    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_pending_reminders():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, time, task FROM reminders WHERE sent = 0"
    )

    data = cursor.fetchall()
    conn.close()
    return data


def mark_sent(reminder_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))

    conn.commit()
    conn.close()


def delete_reminder(reminder_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

    conn.commit()
    conn.close()
