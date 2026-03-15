Telegram Reminder Bot

A Telegram reminder bot built with Python, APScheduler, SQLite, and python-telegram-bot.

Features

- Natural-language reminder parsing
- Recurring reminders (daily, weekly, hourly, every N minutes/hours)
- Snooze buttons on reminder delivery (10 minutes and 1 hour)
- Per-user reminder delivery using stored Telegram chat IDs
- Per-user timezone settings
- Persistent reminders stored in SQLite
- Inline edit/delete actions with confirmation buttons
- Telegram commands for listing and cancelling reminders
- Docker-based deployment option

Supported reminder formats

- remind me tomorrow at 7pm to study
- remind me in 10 minutes to drink water
- remind me to submit report on March 20 2030 at 7pm
- remind me every day at 9am to walk
- remind me to drink water every 30 minutes

Telegram commands

- /start
- /help
- /list
- /cancel <id>
- /timezone
- /timezone Europe/London
- /myid

Environment variables

- BOT_TOKEN: required Telegram bot token from BotFather
- REMINDER_DB_NAME: optional SQLite path, defaults to reminders.db

Run locally

1. Create and activate a virtual environment.
2. Install dependencies.
3. Create a .env file.
4. Start the bot.

macOS / Linux commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 telegram_bot.py
```

Example .env:

```env
BOT_TOKEN=your_telegram_bot_token_here
REMINDER_DB_NAME=reminders.db
```

Local CLI mode

This project still includes a local CLI runner for quick parsing and database checks:

```bash
python3 app.py
```

This mode stores reminders with chat_id=0 and is mainly for local development. Telegram delivery requires running telegram_bot.py.

Run tests

```bash
pytest
```

Docker deployment

Build the image:

```bash
docker build -t telegram-reminder-bot .
```

Run the container:

```bash
docker run --env-file .env -v "$PWD/data:/app/data" -e REMINDER_DB_NAME=/app/data/reminders.db telegram-reminder-bot
```

Project structure

- app.py: local CLI entrypoint
- db.py: SQLite schema and CRUD operations
- logic.py: reminder parsing and validation
- scheduler.py: Telegram JobQueue scheduling and recurring rescheduling
- telegram_bot.py: Telegram command and message handlers
- utils.py: Telegram send-message wrapper
- tests/: parser and database tests

Notes

- Timezones are stored per Telegram chat.
- Pending reminders are reloaded on startup.
- Cancelling reminders is scoped to the requesting chat.
- Reminder notifications include inline Snooze and Delete buttons.
test