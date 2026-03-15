import sqlite3

import db


def test_create_table_migrates_existing_reminders_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "migration.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            task TEXT,
            sent INTEGER DEFAULT 0
        )
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(db, "DB_NAME", str(db_path))

    db.create_table()

    connection = sqlite3.connect(db_path)
    columns = {
        row[1]: row[2]
        for row in connection.execute("PRAGMA table_info(reminders)").fetchall()
    }
    connection.close()

    assert "chat_id" in columns
    assert "timezone" in columns
    assert "recurrence" in columns


def test_reminder_crud_and_user_timezone(tmp_path, monkeypatch):
    db_path = tmp_path / "reminders.db"
    monkeypatch.setattr(db, "DB_NAME", str(db_path))

    db.create_table()

    assert db.get_user_timezone(1234) == db.DEFAULT_TIMEZONE

    db.set_user_timezone(1234, "Europe/London")
    assert db.get_user_timezone(1234) == "Europe/London"

    reminder_id = db.add_reminder(
        chat_id=1234,
        time_str="2030-03-20 19:00:00",
        task="Submit report",
        timezone="Europe/London",
        recurrence="daily",
    )

    reminders = db.get_pending_reminders_for_chat(1234)
    assert reminders == [
        (reminder_id, "2030-03-20 19:00:00", "Submit report", "Europe/London", "daily")
    ]

    assert db.delete_reminder(reminder_id, chat_id=9999) is False
    assert db.delete_reminder(reminder_id, chat_id=1234) is True
    assert db.get_pending_reminders_for_chat(1234) == []