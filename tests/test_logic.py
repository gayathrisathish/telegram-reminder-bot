import pytz

import logic


def test_parse_reminder_message_supports_time_first_format():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "remind me March 20 2030 7pm to Study Algebra",
        "Asia/Kolkata",
    )

    assert task == "Study Algebra"
    assert timezone_name == "Asia/Kolkata"
    assert reminder_time.year == 2030
    assert reminder_time.month == 3
    assert reminder_time.day == 20
    assert reminder_time.hour == 19
    assert recurrence == "none"


def test_parse_reminder_message_supports_task_first_format():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "remind me to Submit report on March 20 2030 at 7pm",
        "Europe/London",
    )

    assert task == "Submit report"
    assert timezone_name == "Europe/London"
    assert reminder_time.year == 2030
    assert reminder_time.month == 3
    assert reminder_time.day == 20
    assert reminder_time.hour == 19
    assert recurrence == "none"


def test_parse_reminder_message_supports_tomorrow_suffix_time():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "remind me to go to park tomorrow at 10PM",
        "Asia/Kolkata",
    )

    assert task == "go to park"
    assert timezone_name == "Asia/Kolkata"
    assert recurrence == "none"
    assert reminder_time.hour == 22


def test_parse_reminder_message_supports_at_time_suffix():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "remind me to go to park at 10PM",
        "Asia/Kolkata",
    )

    assert task == "go to park"
    assert timezone_name == "Asia/Kolkata"
    assert recurrence == "none"
    assert reminder_time.hour == 22


def test_parse_reminder_message_supports_recurrence():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "remind me every day at 9am to Walk",
        "UTC",
    )

    assert task == "Walk"
    assert timezone_name == "UTC"
    assert recurrence == "daily"


def test_parse_reminder_message_supports_open_phrase_without_prefix():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "drink water in 2 minutes",
        "Asia/Kolkata",
    )

    assert task == "drink water"
    assert timezone_name == "Asia/Kolkata"
    assert recurrence == "none"


def test_parse_reminder_message_supports_open_phrase_with_clock_time():
    reminder_time, task, timezone_name, recurrence = logic.parse_reminder_message(
        "go to park tomorrow at 10PM",
        "Asia/Kolkata",
    )

    assert task == "go to park"
    assert timezone_name == "Asia/Kolkata"
    assert recurrence == "none"
    assert reminder_time.hour == 22


def test_normalize_timezone_supports_aliases():
    assert logic.normalize_timezone("IST") == "Asia/Kolkata"
    assert logic.normalize_timezone("UTC") == "UTC"


def test_process_message_schedules_and_persists(monkeypatch):
    captured = {}

    def fake_add_reminder(chat_id, time_str, task, timezone, recurrence):
        captured["chat_id"] = chat_id
        captured["time_str"] = time_str
        captured["task"] = task
        captured["timezone"] = timezone
        captured["recurrence"] = recurrence
        return 77

    def fake_schedule_job(reminder_id, chat_id, reminder_time, task, recurrence, timezone_name):
        captured["scheduled_id"] = reminder_id
        captured["scheduled_chat_id"] = chat_id
        captured["scheduled_task"] = task
        captured["scheduled_recurrence"] = recurrence
        captured["scheduled_timezone_name"] = timezone_name
        captured["scheduled_timezone"] = reminder_time.tzinfo.zone

    monkeypatch.setattr(logic, "add_reminder", fake_add_reminder)
    monkeypatch.setattr(logic, "schedule_job", fake_schedule_job)

    response = logic.process_message(
        "remind me in 10 minutes to Drink Water",
        chat_id=555,
        timezone_name="UTC",
    )

    assert "Saved reminder #77" in response
    assert captured["chat_id"] == 555
    assert captured["task"] == "Drink Water"
    assert captured["timezone"] == "UTC"
    assert captured["recurrence"] == "none"
    assert captured["scheduled_id"] == 77
    assert captured["scheduled_chat_id"] == 555
    assert captured["scheduled_task"] == "Drink Water"
    assert captured["scheduled_recurrence"] == "none"
    assert captured["scheduled_timezone_name"] == "UTC"
    assert captured["scheduled_timezone"] == pytz.timezone("UTC").zone


def test_process_message_supports_open_phrase(monkeypatch):
    captured = {}

    def fake_add_reminder(chat_id, time_str, task, timezone, recurrence):
        captured["chat_id"] = chat_id
        captured["task"] = task
        return 88

    def fake_schedule_job(reminder_id, chat_id, reminder_time, task, recurrence, timezone_name):
        captured["scheduled_id"] = reminder_id
        captured["scheduled_task"] = task

    monkeypatch.setattr(logic, "add_reminder", fake_add_reminder)
    monkeypatch.setattr(logic, "schedule_job", fake_schedule_job)

    response = logic.process_message(
        "drink water in 2 minutes",
        chat_id=999,
        timezone_name="Asia/Kolkata",
    )

    assert "Saved reminder #88" in response
    assert captured["chat_id"] == 999
    assert captured["task"] == "drink water"
    assert captured["scheduled_id"] == 88
    assert captured["scheduled_task"] == "drink water"