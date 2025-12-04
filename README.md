🕒 Telegram Reminder Bot
A simple, lightweight reminder bot built using Python, APScheduler, and the python-telegram-bot library.
The bot understands natural-language commands and schedules reminders that are delivered directly to your Telegram chat.

🚀 Features
⏰ Create reminders using natural language
“remind me in 10 minutes to drink water”
“remind me tomorrow at 7pm to study”

🌍 Timezone-aware scheduling (India Standard Time — IST)
💾 SQLite database stores reminders safely
🔄 Bot restarts do NOT lose reminders
🔔 Reliable notifications delivered via Telegram

🧠 Smart NLP:
Understands “in X minutes/hours”

Understands time + task mixed formats

🧩 Project Structure
telegram-reminder-bot/
│
├── telegram_bot.py      # Main Telegram bot handler
├── logic.py             # NLP and reminder parsing
├── scheduler.py         # APScheduler scheduling + sending reminders
├── utils.py             # Send-message utilities
├── db.py                # SQLite database management
├── requirements.txt     # Python dependencies
├── test_send.py         # Manual send-message test
├── test_schedule.py     # Scheduling test script
└── README.md
