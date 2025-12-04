📌 AI-Powered Telegram Reminder Bot
A smart natural-language reminder bot built with Python, APScheduler, and Telegram.
It lets you set reminders like:

remind me in 10 minutes to stretch
remind me tomorrow at 6pm to study
remind me on Monday to call mom
The bot saves reminders in a local SQLite database and sends notifications directly to your Telegram chat.


✨ Features
🧠 Natural-language reminder parsing (remind me in 2 hours…)

⏰ Accurate scheduling using APScheduler

💾 SQLite-backed persistent reminders

🔔 Instant Telegram notifications

🕒 Timezone aware (Asia/Kolkata)

🔄 Automatically loads pending reminders on restart


📦 Tech Stack
| Component           | Description                   |
| ------------------- | ----------------------------- |
| Python              | Core language                 |
| APScheduler         | Scheduling reminders          |
| SQLite              | Database storage              |
| python-telegram-bot | Telegram integration          |
| dateparser          | Natural language time parsing |
| pytz                | Timezone support              |


🛠️ Setup Instructions
1️⃣ Clone the repo
git clone https://github.com/<your-username>/telegram-reminder-bot.git
cd telegram-reminder-bot
2️⃣ Create a virtual environment
python3 -m venv venv
source venv/bin/activate
3️⃣ Install dependencies
pip install -r requirements.txt
4️⃣ Create a .env file for your bot token
touch .env
Inside:

BOT_TOKEN=your-secret-token-here
5️⃣ Run the bot
python telegram_bot.py
