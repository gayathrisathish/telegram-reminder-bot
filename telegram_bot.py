from datetime import datetime
import os

import pytz
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import scheduler
from db import (
    create_table,
    delete_reminder,
    get_pending_reminders_for_chat,
    get_reminder,
    get_user_timezone,
    set_user_timezone,
    update_reminder_task,
    update_reminder_time,
)
from logic import DATETIME_FORMAT, normalize_timezone, parse_time_text, process_message

load_dotenv(override=True)
BOT_TOKEN = os.getenv("BOT_TOKEN")

HELP_TEXT = (
    "Send a message like 'remind me tomorrow at 7pm to study'\n"
    "or 'remind me to stretch in 15 minutes'.\n"
    "Recurring examples:\n"
    "- remind me every day at 7pm to review notes\n"
    "- remind me to drink water every 30 minutes\n\n"
    "Commands:\n"
    "/list - show your pending reminders\n"
    "/cancel <id> - delete one reminder\n"
    "/timezone [Region/City] - show or set your timezone\n"
    "/myid - show your Telegram chat id"
)

PENDING_EDITS = {}
PENDING_EDIT_CONFIRMATIONS = {}
NEXT_CONFIRM_ID = 1


def _format_recurrence(recurrence):
    if recurrence == "none":
        return "one-time"
    if recurrence == "daily":
        return "every day"
    if recurrence == "weekly":
        return "every week"
    if recurrence == "hourly":
        return "every hour"
    if recurrence.startswith("minutes:"):
        return f"every {recurrence.split(':', 1)[1]} minutes"
    if recurrence.startswith("hours:"):
        return f"every {recurrence.split(':', 1)[1]} hours"
    return recurrence


def _reminder_row_text(reminder_id, time_str, task, timezone_name, recurrence):
    timezone = pytz.timezone(timezone_name)
    reminder_time = timezone.localize(datetime.strptime(time_str, DATETIME_FORMAT))
    return (
        f"#{reminder_id} - {reminder_time.strftime('%Y-%m-%d %I:%M %p %Z')} - "
        f"{task} ({_format_recurrence(recurrence)})"
    )


def _reminder_actions_keyboard(reminder_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Edit task", callback_data=f"edittask:{reminder_id}"),
                InlineKeyboardButton("Edit time", callback_data=f"edittime:{reminder_id}"),
            ],
            [InlineKeyboardButton("Delete", callback_data=f"delask:{reminder_id}")],
        ]
    )


def _delete_confirmation_keyboard(reminder_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirm delete", callback_data=f"delconfirm:{reminder_id}"),
                InlineKeyboardButton("Cancel", callback_data=f"delcancel:{reminder_id}"),
            ]
        ]
    )


def _edit_confirmation_keyboard(confirm_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Apply", callback_data=f"editapply:{confirm_id}"),
                InlineKeyboardButton("Discard", callback_data=f"editcancel:{confirm_id}"),
            ]
        ]
    )


def _next_confirm_id():
    global NEXT_CONFIRM_ID
    current = NEXT_CONFIRM_ID
    NEXT_CONFIRM_ID += 1
    return current


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    timezone_name = get_user_timezone(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Reminder bot is ready. Current timezone: {timezone_name}\n\n{HELP_TEXT}",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=HELP_TEXT)


async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=f"Your chat_id is: {chat_id}")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reminders = get_pending_reminders_for_chat(chat_id)

    if not reminders:
        await context.bot.send_message(chat_id=chat_id, text="You have no pending reminders.")
        return

    for reminder_id, time_str, task, timezone_name, recurrence in reminders:
        await context.bot.send_message(
            chat_id=chat_id,
            text=_reminder_row_text(reminder_id, time_str, task, timezone_name, recurrence),
            reply_markup=_reminder_actions_keyboard(reminder_id),
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="Usage: /cancel <reminder_id>")
        return

    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await context.bot.send_message(chat_id=chat_id, text="Reminder id must be a number.")
        return

    reminder = get_reminder(reminder_id, chat_id=chat_id)
    if reminder is None or reminder[6] == 1:
        await context.bot.send_message(chat_id=chat_id, text="No pending reminder found with that id.")
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Delete reminder #{reminder_id}?",
        reply_markup=_delete_confirmation_keyboard(reminder_id),
    )


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not context.args:
        current_timezone = get_user_timezone(chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"Current timezone: {current_timezone}\n"
                "Set a new one with /timezone Region/City, for example /timezone Europe/London"
            ),
        )
        return

    requested_timezone = " ".join(context.args)
    try:
        normalized_timezone = normalize_timezone(requested_timezone)
    except ValueError as exc:
        await context.bot.send_message(chat_id=chat_id, text=str(exc))
        return

    set_user_timezone(chat_id, normalized_timezone)
    await context.bot.send_message(chat_id=chat_id, text=f"Timezone updated to {normalized_timezone}.")


async def _apply_pending_edit_input(update: Update):
    chat_id = update.effective_chat.id
    pending = PENDING_EDITS.get(chat_id)
    if pending is None:
        return False

    message_text = (update.message.text or "").strip()
    if not message_text:
        await update.message.reply_text("Please send a valid value.")
        return True

    reminder_id = pending["reminder_id"]
    field = pending["field"]
    timezone_name = pending["timezone"]

    if field == "task":
        confirm_text = (
            f"Apply this task update to reminder #{reminder_id}?\n"
            f"New task: {message_text}"
        )
        payload_value = message_text
    else:
        try:
            parsed_dt = parse_time_text(message_text, timezone_name)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return True

        payload_value = parsed_dt.strftime(DATETIME_FORMAT)
        confirm_text = (
            f"Apply this time update to reminder #{reminder_id}?\n"
            f"New time: {parsed_dt.strftime('%Y-%m-%d %I:%M %p %Z')}"
        )

    confirm_id = _next_confirm_id()
    PENDING_EDIT_CONFIRMATIONS[confirm_id] = {
        "chat_id": chat_id,
        "reminder_id": reminder_id,
        "field": field,
        "value": payload_value,
    }
    del PENDING_EDITS[chat_id]

    await update.message.reply_text(
        confirm_text,
        reply_markup=_edit_confirmation_keyboard(confirm_id),
    )
    return True


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    chat_id = update.effective_chat.id

    if await _apply_pending_edit_input(update):
        return

    timezone_name = get_user_timezone(chat_id)
    response = process_message(update.message.text, chat_id=chat_id, timezone_name=timezone_name)
    await update.message.reply_text(response)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.data is None:
        return

    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("delask:"):
        reminder_id = int(data.split(":", 1)[1])
        await query.edit_message_reply_markup(reply_markup=_delete_confirmation_keyboard(reminder_id))
        return

    if data.startswith("delcancel:"):
        reminder_id = int(data.split(":", 1)[1])
        await query.edit_message_reply_markup(reply_markup=_reminder_actions_keyboard(reminder_id))
        return

    if data.startswith("delconfirm:"):
        reminder_id = int(data.split(":", 1)[1])
        deleted = delete_reminder(reminder_id, chat_id=chat_id)
        scheduler.cancel_job(reminder_id)
        if deleted:
            await query.edit_message_text(f"Reminder #{reminder_id} deleted.")
        else:
            await query.edit_message_text("Reminder was already removed.")
        return

    if data.startswith("edittask:"):
        reminder_id = int(data.split(":", 1)[1])
        reminder = get_reminder(reminder_id, chat_id=chat_id)
        if reminder is None or reminder[6] == 1:
            await query.edit_message_text("Reminder was not found.")
            return
        PENDING_EDITS[chat_id] = {
            "reminder_id": reminder_id,
            "field": "task",
            "timezone": reminder[4],
        }
        await query.message.reply_text(f"Send the new task text for reminder #{reminder_id}.")
        return

    if data.startswith("edittime:"):
        reminder_id = int(data.split(":", 1)[1])
        reminder = get_reminder(reminder_id, chat_id=chat_id)
        if reminder is None or reminder[6] == 1:
            await query.edit_message_text("Reminder was not found.")
            return
        PENDING_EDITS[chat_id] = {
            "reminder_id": reminder_id,
            "field": "time",
            "timezone": reminder[4],
        }
        await query.message.reply_text(
            f"Send the new time for reminder #{reminder_id} (for example: tomorrow 7pm)."
        )
        return

    if data.startswith("editcancel:"):
        confirm_id = int(data.split(":", 1)[1])
        PENDING_EDIT_CONFIRMATIONS.pop(confirm_id, None)
        await query.edit_message_text("Edit cancelled.")
        return

    if data.startswith("editapply:"):
        confirm_id = int(data.split(":", 1)[1])
        payload = PENDING_EDIT_CONFIRMATIONS.pop(confirm_id, None)
        if payload is None or payload["chat_id"] != chat_id:
            await query.edit_message_text("This edit request is no longer valid.")
            return

        reminder = get_reminder(payload["reminder_id"], chat_id=chat_id)
        if reminder is None or reminder[6] == 1:
            await query.edit_message_text("Reminder was not found.")
            return

        reminder_id = payload["reminder_id"]
        if payload["field"] == "task":
            updated = update_reminder_task(reminder_id, chat_id, payload["value"])
            if updated:
                scheduler.schedule_job(
                    reminder_id=reminder_id,
                    chat_id=chat_id,
                    run_dt=pytz.timezone(reminder[4]).localize(datetime.strptime(reminder[2], DATETIME_FORMAT)),
                    task=payload["value"],
                    recurrence=reminder[5],
                    timezone_name=reminder[4],
                )
                await query.edit_message_text(f"Reminder #{reminder_id} task updated.")
            else:
                await query.edit_message_text("Could not update the reminder task.")
            return

        updated = update_reminder_time(reminder_id, chat_id, payload["value"])
        if updated:
            run_dt = pytz.timezone(reminder[4]).localize(datetime.strptime(payload["value"], DATETIME_FORMAT))
            scheduler.schedule_job(
                reminder_id=reminder_id,
                chat_id=chat_id,
                run_dt=run_dt,
                task=reminder[3],
                recurrence=reminder[5],
                timezone_name=reminder[4],
            )
            await query.edit_message_text(f"Reminder #{reminder_id} time updated.")
        else:
            await query.edit_message_text("Could not update the reminder time.")
        return

    if data.startswith("snooze:"):
        _, reminder_id_text, minutes_text = data.split(":")
        reminder_id = int(reminder_id_text)
        minutes = int(minutes_text)
        reminder = get_reminder(reminder_id, chat_id=chat_id)
        if reminder is None:
            await query.message.reply_text("Reminder was not found.")
            return

        new_id, run_dt = scheduler.create_snoozed_reminder(
            reminder_id=reminder_id,
            chat_id=chat_id,
            task=reminder[3],
            timezone_name=reminder[4],
            minutes=minutes,
        )
        await query.message.reply_text(
            f"Snoozed as reminder #{new_id} until {run_dt.strftime('%Y-%m-%d %I:%M %p %Z')}."
        )
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"[bot] Handler error: {context.error}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Add it to your .env file before starting the bot.")

    create_table()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    scheduler.init_job_queue(application.job_queue)
    scheduler.load_and_schedule_pending()
    scheduler.start_scheduler()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("timezone", timezone_command))
    application.add_handler(CommandHandler("myid", show_id))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
