import re
from datetime import datetime

import dateparser
import pytz
from dateparser.search import search_dates

from db import DEFAULT_TIMEZONE, add_reminder
from scheduler import schedule_job

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMEZONE_ALIASES = {
    "IST": "Asia/Kolkata",
    "UTC": "UTC",
}

TIME_FIRST_PATTERN = re.compile(
    r"^(?P<time>.+?)\s+to\s+(?P<task>.+)$",
    re.IGNORECASE,
)
TASK_FIRST_PATTERN = re.compile(r"^to\s+(?P<body>.+)$", re.IGNORECASE)
REMIND_PREFIX_PATTERN = re.compile(r"^\s*(?:please\s+)?remind me\s*", re.IGNORECASE)

RECURRENCE_PATTERNS = [
    (re.compile(r"\bevery\s+day\b", re.IGNORECASE), "daily"),
    (re.compile(r"\bevery\s+week\b", re.IGNORECASE), "weekly"),
    (re.compile(r"\bevery\s+hour\b", re.IGNORECASE), "hourly"),
    (re.compile(r"\bevery\s+(\d+)\s+minutes?\b", re.IGNORECASE), "minutes"),
    (re.compile(r"\bevery\s+(\d+)\s+hours?\b", re.IGNORECASE), "hours"),
]

TEMPORAL_HINT_PATTERN = re.compile(
    r"\b(tomorrow|today|tonight|next|in|at|am|pm|minute|minutes|hour|hours|day|days|week|weeks|mon|tue|wed|thu|fri|sat|sun|\d{1,2}(:\d{2})?)\b",
    re.IGNORECASE,
)


def normalize_timezone(timezone_name):
    candidate = (timezone_name or DEFAULT_TIMEZONE).strip()
    candidate = TIMEZONE_ALIASES.get(candidate.upper(), candidate)

    try:
        return pytz.timezone(candidate).zone
    except pytz.UnknownTimeZoneError as exc:
        raise ValueError(
            "Unknown timezone. Use values like Asia/Kolkata, Europe/London, or UTC."
        ) from exc


def _get_dateparser_settings(timezone_name):
    return {
        "TIMEZONE": timezone_name,
        "TO_TIMEZONE": timezone_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
    }


def _ensure_timezone(reminder_time, timezone_name):
    timezone = pytz.timezone(timezone_name)

    if reminder_time.tzinfo is None:
        return timezone.localize(reminder_time.replace(microsecond=0))

    return reminder_time.astimezone(timezone).replace(microsecond=0)


def _remove_matched_fragment(text, fragment):
    match = re.search(re.escape(fragment), text, re.IGNORECASE)
    if not match:
        return text.strip()

    remainder = f"{text[:match.start()]} {text[match.end():]}"
    remainder = re.sub(r"\s+", " ", remainder)
    return remainder.strip(" ,-.")


def _extract_recurrence(text):
    working_text = text

    for pattern, recurrence_kind in RECURRENCE_PATTERNS:
        match = pattern.search(working_text)
        if not match:
            continue

        recurrence = recurrence_kind
        if recurrence_kind in {"minutes", "hours"}:
            recurrence = f"{recurrence_kind}:{int(match.group(1))}"

        cleaned = f"{working_text[:match.start()]} {working_text[match.end():]}"
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned, recurrence

    return working_text, "none"


def _parse_time_fragment(time_text, timezone_name):
    reminder_time = dateparser.parse(
        time_text,
        settings=_get_dateparser_settings(timezone_name),
    )

    if reminder_time is None:
        raise ValueError("I couldn't understand the time. Try 'in 10 minutes' or 'tomorrow at 7pm'.")

    reminder_time = _ensure_timezone(reminder_time, timezone_name)
    if reminder_time <= datetime.now(pytz.timezone(timezone_name)):
        raise ValueError("That time is in the past. Please choose a future time.")

    return reminder_time


def _extract_task_and_time_from_suffix(body, timezone_name):
    tokens = body.split()

    for index in range(len(tokens)):
        time_candidate = " ".join(tokens[index:]).strip(" ,.-")
        task_candidate = " ".join(tokens[:index]).strip(" ,.-")

        if not time_candidate or not task_candidate:
            continue

        if not TEMPORAL_HINT_PATTERN.search(time_candidate):
            continue

        parsed = dateparser.parse(
            time_candidate,
            settings=_get_dateparser_settings(timezone_name),
        )

        if parsed is None:
            continue

        return task_candidate, _ensure_timezone(parsed, timezone_name)

    return None, None


def _strip_remind_prefix(text):
    match = REMIND_PREFIX_PATTERN.match(text)
    if not match:
        return text, False
    return text[match.end():].strip(), True


def _parse_task_first_body(body, timezone_name):
    matches = search_dates(
        body,
        settings=_get_dateparser_settings(timezone_name),
        languages=["en"],
    )

    if not matches:
        task, reminder_time = _extract_task_and_time_from_suffix(body, timezone_name)
        if task is None or reminder_time is None:
            raise ValueError(
                "I couldn't find a time in that message. Try 'drink water in 10 minutes'."
            )
    else:
        matched_text, parsed_time = max(matches, key=lambda item: len(item[0].strip()))
        task = _remove_matched_fragment(body, matched_text)
        reminder_time = _ensure_timezone(parsed_time, timezone_name)

    if not task:
        raise ValueError("Please tell me what to remind you about.")

    if reminder_time <= datetime.now(pytz.timezone(timezone_name)):
        raise ValueError("That time is in the past. Please choose a future time.")

    return reminder_time, task


def _parse_any_phrase(text, timezone_name):
    matches = search_dates(
        text,
        settings=_get_dateparser_settings(timezone_name),
        languages=["en"],
    )

    if not matches:
        raise ValueError(
            "I couldn't find a time in that message. Try 'drink water in 10 minutes'."
        )

    matched_text, parsed_time = max(matches, key=lambda item: len(item[0].strip()))
    task = _remove_matched_fragment(text, matched_text)
    reminder_time = _ensure_timezone(parsed_time, timezone_name)

    if not task:
        raise ValueError("Please tell me what to remind you about.")

    if reminder_time <= datetime.now(pytz.timezone(timezone_name)):
        raise ValueError("That time is in the past. Please choose a future time.")

    return reminder_time, task


def parse_time_text(time_text, timezone_name=DEFAULT_TIMEZONE):
    normalized_timezone = normalize_timezone(timezone_name)
    return _parse_time_fragment(time_text, normalized_timezone)


def parse_reminder_message(text, timezone_name=DEFAULT_TIMEZONE):
    cleaned_text, had_prefix = _strip_remind_prefix(text.strip())
    cleaned_text, recurrence = _extract_recurrence(cleaned_text)
    normalized_timezone = normalize_timezone(timezone_name)

    if had_prefix:
        task_first_match = TASK_FIRST_PATTERN.match(cleaned_text)
        if task_first_match:
            reminder_time, task = _parse_task_first_body(
                task_first_match.group("body").strip(),
                normalized_timezone,
            )
            return reminder_time, task, normalized_timezone, recurrence

        time_first_match = TIME_FIRST_PATTERN.match(cleaned_text)
        if time_first_match:
            reminder_time = _parse_time_fragment(time_first_match.group("time"), normalized_timezone)
            task = time_first_match.group("task").strip()
            if not task:
                raise ValueError("Please tell me what to remind you about.")
            return reminder_time, task, normalized_timezone, recurrence

    reminder_time, task = _parse_any_phrase(cleaned_text, normalized_timezone)
    return reminder_time, task, normalized_timezone, recurrence


def create_reminder_from_text(text, chat_id, timezone_name=DEFAULT_TIMEZONE):
    reminder_time, task, normalized_timezone, recurrence = parse_reminder_message(
        text,
        timezone_name,
    )
    time_str = reminder_time.strftime(DATETIME_FORMAT)
    reminder_id = add_reminder(chat_id, time_str, task, normalized_timezone, recurrence)
    schedule_job(reminder_id, chat_id, reminder_time, task, recurrence, normalized_timezone)
    return reminder_id, reminder_time, task, normalized_timezone, recurrence


def process_message(text, chat_id=0, timezone_name=DEFAULT_TIMEZONE):
    try:
        reminder_id, reminder_time, task, normalized_timezone, recurrence = create_reminder_from_text(
            text,
            chat_id=chat_id,
            timezone_name=timezone_name,
        )
    except ValueError as exc:
        return str(exc)

    display_time = reminder_time.strftime("%Y-%m-%d %I:%M %p %Z")
    if recurrence == "none":
        return f"Saved reminder #{reminder_id} for {display_time}: {task} ({normalized_timezone})"

    if recurrence == "daily":
        recurrence_label = "every day"
    elif recurrence == "weekly":
        recurrence_label = "every week"
    elif recurrence == "hourly":
        recurrence_label = "every hour"
    elif recurrence.startswith("minutes:"):
        recurrence_label = f"every {recurrence.split(':', 1)[1]} minutes"
    elif recurrence.startswith("hours:"):
        recurrence_label = f"every {recurrence.split(':', 1)[1]} hours"
    else:
        recurrence_label = recurrence

    return (
        f"Saved recurring reminder #{reminder_id} for {display_time}: {task} "
        f"({normalized_timezone}, repeat={recurrence_label})"
    )
