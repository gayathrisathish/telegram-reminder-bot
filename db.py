import os
import sqlite3

DB_NAME = os.getenv("REMINDER_DB_NAME", "reminders.db")
DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def _get_column_names(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_reminders_schema(cursor):
    columns = _get_column_names(cursor, "reminders")

    if "chat_id" not in columns:
        cursor.execute("ALTER TABLE reminders ADD COLUMN chat_id INTEGER NOT NULL DEFAULT 0")
    if "timezone" not in columns:
        cursor.execute(
            "ALTER TABLE reminders ADD COLUMN timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata'"
        )
    if "recurrence" not in columns:
        cursor.execute(
            "ALTER TABLE reminders ADD COLUMN recurrence TEXT NOT NULL DEFAULT 'none'"
        )


def create_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL DEFAULT 0,
            time TEXT NOT NULL,
            task TEXT NOT NULL,
            timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            recurrence TEXT NOT NULL DEFAULT 'none',
            sent INTEGER DEFAULT 0
        )
        """
    )
    _ensure_reminders_schema(cursor)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            chat_id INTEGER PRIMARY KEY,
            timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata'
        )
        """
    )

    conn.commit()
    conn.close()


def add_reminder(chat_id, time_str, task, timezone=DEFAULT_TIMEZONE, recurrence="none"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO reminders (chat_id, time, task, timezone, recurrence, sent)
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (chat_id, time_str, task, timezone, recurrence),
    )

    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_pending_reminders():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, chat_id, time, task, timezone, recurrence
        FROM reminders
        WHERE sent = 0
        ORDER BY time ASC, id ASC
        """
    )

    data = cursor.fetchall()
    conn.close()
    return data


def get_pending_reminders_for_chat(chat_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, time, task, timezone, recurrence
        FROM reminders
        WHERE sent = 0 AND chat_id = ?
        ORDER BY time ASC, id ASC
        """,
        (chat_id,),
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


def delete_reminder(reminder_id, chat_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    if chat_id is None:
        cursor.execute("DELETE FROM reminders WHERE id = ? AND sent = 0", (reminder_id,))
    else:
        cursor.execute(
            "DELETE FROM reminders WHERE id = ? AND chat_id = ? AND sent = 0",
            (reminder_id, chat_id),
        )

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_reminder(reminder_id, chat_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    if chat_id is None:
        cursor.execute(
            """
            SELECT id, chat_id, time, task, timezone, recurrence, sent
            FROM reminders
            WHERE id = ?
            """,
            (reminder_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, chat_id, time, task, timezone, recurrence, sent
            FROM reminders
            WHERE id = ? AND chat_id = ?
            """,
            (reminder_id, chat_id),
        )

    row = cursor.fetchone()
    conn.close()
    return row


def update_reminder_task(reminder_id, chat_id, task):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE reminders SET task = ? WHERE id = ? AND chat_id = ? AND sent = 0",
        (task, reminder_id, chat_id),
    )

    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_reminder_time(reminder_id, chat_id, time_str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE reminders SET time = ? WHERE id = ? AND chat_id = ? AND sent = 0",
        (time_str, reminder_id, chat_id),
    )

    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_reminder_schedule(reminder_id, chat_id, time_str, recurrence):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE reminders
        SET time = ?, recurrence = ?
        WHERE id = ? AND chat_id = ? AND sent = 0
        """,
        (time_str, recurrence, reminder_id, chat_id),
    )

    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_user_timezone(chat_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT timezone FROM user_settings WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()

    conn.close()
    if row is None:
        return DEFAULT_TIMEZONE
    return row[0]


def set_user_timezone(chat_id, timezone_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO user_settings (chat_id, timezone)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET timezone = excluded.timezone
        """,
        (chat_id, timezone_name),
    )

    conn.commit()
    conn.close()
