from datetime import datetime, timedelta

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import (
	DEFAULT_TIMEZONE,
	add_reminder,
	get_pending_reminders,
	mark_sent,
	update_reminder_time,
)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
JOB_NAME_PREFIX = "reminder-"

_job_queue = None


def _job_name(reminder_id):
	return f"{JOB_NAME_PREFIX}{reminder_id}"


def init_job_queue(job_queue):
	global _job_queue
	_job_queue = job_queue


def _interval_from_recurrence(recurrence):
	if recurrence == "none":
		return None
	if recurrence == "hourly":
		return timedelta(hours=1)
	if recurrence == "daily":
		return timedelta(days=1)
	if recurrence == "weekly":
		return timedelta(weeks=1)

	if recurrence.startswith("minutes:"):
		minutes = int(recurrence.split(":", 1)[1])
		return timedelta(minutes=max(1, minutes))

	if recurrence.startswith("hours:"):
		hours = int(recurrence.split(":", 1)[1])
		return timedelta(hours=max(1, hours))

	return None


def _next_occurrence(run_dt, recurrence):
	interval = _interval_from_recurrence(recurrence)
	if interval is None:
		return None

	now = datetime.now(run_dt.tzinfo)
	next_dt = run_dt
	while next_dt <= now:
		next_dt = next_dt + interval
	return next_dt


def _send_keyboard(reminder_id):
	return InlineKeyboardMarkup(
		[
			[
				InlineKeyboardButton("Snooze 10m", callback_data=f"snooze:{reminder_id}:10"),
				InlineKeyboardButton("Snooze 1h", callback_data=f"snooze:{reminder_id}:60"),
			],
			[InlineKeyboardButton("Delete", callback_data=f"delask:{reminder_id}")],
		]
	)


async def _run_reminder(context):
	payload = context.job.data
	reminder_id = payload["reminder_id"]
	chat_id = payload["chat_id"]
	task = payload["task"]
	recurrence = payload["recurrence"]
	timezone_name = payload["timezone"]
	run_time = payload["run_time"]

	if not isinstance(chat_id, int) or chat_id <= 0:
		mark_sent(reminder_id)
		print(f"[scheduler] Skipping reminder {reminder_id}: invalid chat_id={chat_id}")
		return

	await context.bot.send_message(
		chat_id=chat_id,
		text=f"Reminder: {task}",
		reply_markup=_send_keyboard(reminder_id),
	)

	if recurrence == "none":
		mark_sent(reminder_id)
		return

	timezone = pytz.timezone(timezone_name)
	run_dt = timezone.localize(datetime.strptime(run_time, DATETIME_FORMAT))
	next_dt = _next_occurrence(run_dt, recurrence)

	if next_dt is None:
		mark_sent(reminder_id)
		return

	next_time_str = next_dt.strftime(DATETIME_FORMAT)
	update_reminder_time(reminder_id, chat_id, next_time_str)
	schedule_job(
		reminder_id=reminder_id,
		chat_id=chat_id,
		run_dt=next_dt,
		task=task,
		recurrence=recurrence,
		timezone_name=timezone_name,
	)


def schedule_job(reminder_id, chat_id, run_dt, task, recurrence="none", timezone_name=DEFAULT_TIMEZONE):
	if _job_queue is None:
		return

	timezone = pytz.timezone(timezone_name or DEFAULT_TIMEZONE)
	if run_dt.tzinfo is None:
		run_dt = timezone.localize(run_dt)
	else:
		run_dt = run_dt.astimezone(timezone)

	cancel_job(reminder_id)
	_job_queue.run_once(
		callback=_run_reminder,
		when=run_dt,
		name=_job_name(reminder_id),
		data={
			"reminder_id": reminder_id,
			"chat_id": chat_id,
			"task": task,
			"recurrence": recurrence,
			"timezone": timezone.zone,
			"run_time": run_dt.strftime(DATETIME_FORMAT),
		},
	)
	print(f"[scheduler] Scheduled reminder id={reminder_id} at {run_dt} ({recurrence})")


def load_and_schedule_pending():
	reminders = get_pending_reminders()
	print(f"[scheduler] Loading {len(reminders)} pending reminders...")

	for reminder_id, chat_id, time_str, task, timezone_name, recurrence in reminders:
		try:
			if chat_id <= 0:
				mark_sent(reminder_id)
				print(f"[scheduler] Marked reminder {reminder_id} as sent (invalid chat_id={chat_id}).")
				continue

			timezone = pytz.timezone(timezone_name or DEFAULT_TIMEZONE)
			run_dt = timezone.localize(datetime.strptime(time_str, DATETIME_FORMAT))
			now = datetime.now(timezone)

			if run_dt <= now and recurrence != "none":
				next_dt = _next_occurrence(run_dt, recurrence)
				if next_dt is None:
					mark_sent(reminder_id)
					continue
				run_dt = next_dt
				update_reminder_time(reminder_id, chat_id, run_dt.strftime(DATETIME_FORMAT))

			if run_dt <= now and recurrence == "none":
				mark_sent(reminder_id)
				print(f"[scheduler] Marked reminder {reminder_id} as sent (past one-time reminder).")
				continue

			schedule_job(
				reminder_id=reminder_id,
				chat_id=chat_id,
				run_dt=run_dt,
				task=task,
				recurrence=recurrence,
				timezone_name=timezone.zone,
			)
		except Exception as exc:
			print(f"[scheduler] Error loading reminder {reminder_id}: {exc}")


def start_scheduler():
	return


def cancel_job(reminder_id):
	if _job_queue is None:
		return False

	jobs = _job_queue.get_jobs_by_name(_job_name(reminder_id))
	if not jobs:
		return False

	for job in jobs:
		job.schedule_removal()
	return True


def create_snoozed_reminder(reminder_id, chat_id, task, timezone_name, minutes):
	timezone = pytz.timezone(timezone_name or DEFAULT_TIMEZONE)
	run_dt = datetime.now(timezone) + timedelta(minutes=minutes)
	time_str = run_dt.strftime(DATETIME_FORMAT)
	new_id = add_reminder(
		chat_id=chat_id,
		time_str=time_str,
		task=task,
		timezone=timezone.zone,
		recurrence="none",
	)
	schedule_job(
		reminder_id=new_id,
		chat_id=chat_id,
		run_dt=run_dt,
		task=task,
		recurrence="none",
		timezone_name=timezone.zone,
	)
	return new_id, run_dt
