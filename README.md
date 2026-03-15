# Telegram Reminder Bot

A simple Telegram bot that lets users create and receive reminders.

## Features

- Create one-time and recurring reminders
- Store reminders in SQLite
- List and cancel reminders using Telegram commands
- Supports user timezone settings

## Requirements

- Python 3.10+
- A Telegram bot token from BotFather

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_bot_token_here
REMINDER_DB_NAME=reminders.db
```

## Run

```bash
python3 telegram_bot.py
```

## Useful Commands

- `/start`
- `/help`
- `/list`
- `/cancel <id>`
- `/timezone`

## Run Tests

```bash
pytest
```