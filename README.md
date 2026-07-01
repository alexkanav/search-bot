# Marketplace Search Bot
Marketplace Search Bot is a Telegram bot that continuously monitors marketplace listings based on user-defined search criteria and notifies users when new matching items appear.

---
## Features

- Search listings by keyword
- Filter by maximum price
- Filter by region and location
- Continuous monitoring
- Instant Telegram notifications
- Multiple marketplace support
- Async architecture
- Redis caching
- MongoDB storage
- Playwright-based scraping

---
## Tech Stack

- Python 3.10+
- aiogram 3
- Playwright
- MongoDB
- Redis
- Docker
- asyncio

---
## Architecture

The bot consists of:

- Telegram handlers
- Search task manager
- Marketplace scraper
- MongoDB repository
- Redis cache
- Notification service

## Design Decisions

- Async-first architecture using asyncio
- Dependency injection for services
- Repository pattern for persistence
- Redis caching to reduce duplicate processing
- Playwright instead of Selenium for improved reliability
- Background search tasks managed independently of Telegram handlers

---
## Installation

Clone the repository

```bash
git clone https://github.com/alexkanav/search-bot.git
cd search-bot
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```env
TOKEN=
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=
MONGODB_URL=
MONGO_DB_NAME=
MONGODB_COLLECTION=
```

| Variable | Description |
|----------|-------------|
| `TOKEN` | Telegram bot token obtained from BotFather |
| `REDIS_HOST` | Redis server hostname |
| `REDIS_PORT` | Redis server port |
| `REDIS_PASSWORD` | Redis password (leave empty if authentication is disabled) |
| `MONGODB_URL` | MongoDB connection URI |
| `MONGO_DB_NAME` | MongoDB database name |
| `MONGODB_COLLECTION` | Collection used to store user searches |

---
## Run

```bash
python -m app.bot
```

## Usage

1. Start the bot

```
/start
```

2. Choose a marketplace

3. Enter a search query

4. Set the maximum price

5. Select region (optional)

6. Select location (optional)

7. Set the search interval

The bot will continuously monitor new listings and notify you when matching items appear.

---
## Future Improvements

- Additional marketplace support
- Image similarity search
- User search history
- Web dashboard
- Metrics and monitoring

---
## License
MIT — Feel free to use, modify, and share.
