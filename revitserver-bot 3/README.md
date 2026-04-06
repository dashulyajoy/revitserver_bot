# 🤖 RevitServer.ru — Telegram Bot

Чат-бот для первой линии поддержки и квалификации лидов. Работает на базе Claude (Anthropic).

## Что умеет

- Отвечает на вопросы о Revit Server и VDI на основе базы знаний
- Квалифицирует лидов (размер команды, версия Revit, задача)
- Уведомляет менеджера в Telegram при горячем лиде или эскалации
- Помнит контекст диалога
- Красивое меню с кнопками при /start

---

## Быстрый старт

### 1. Создать бота в Telegram

Написать [@BotFather](https://t.me/BotFather):
```
/newbot
```
Получить `TELEGRAM_TOKEN`.

### 2. Получить Anthropic API Key

Зарегистрироваться на [console.anthropic.com](https://console.anthropic.com), создать API Key.

### 3. Узнать свой Telegram ID

Написать [@userinfobot](https://t.me/userinfobot) — он пришлёт ваш числовой ID.

### 4. Настроить переменные окружения

```bash
cp .env.example .env
# Открыть .env и заполнить три значения:
# TELEGRAM_TOKEN, ANTHROPIC_API_KEY, MANAGER_CHAT_ID
```

---

## Деплой: вариант 1 — Railway (рекомендуется, бесплатно)

1. Зарегистрироваться на [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo (загрузить этот код)
3. В настройках проекта → Variables → добавить три переменные из `.env`
4. Railway автоматически соберёт Docker-контейнер и запустит бота

---

## Деплой: вариант 2 — VPS / любой Linux сервер

```bash
# Клонировать репозиторий
git clone <your-repo-url>
cd revitserver-bot

# Создать .env
cp .env.example .env
nano .env  # заполнить переменные

# Запустить через Docker
docker build -t revitserver-bot .
docker run -d --name revitserver-bot --env-file .env revitserver-bot

# Или без Docker — напрямую
cd bot
pip install -r ../requirements.txt
python main.py
```

---

## Деплой: вариант 3 — Render.com (бесплатно)

1. Создать аккаунт на [render.com](https://render.com)
2. New → Web Service → Connect to GitHub
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `cd bot && python main.py`
5. Environment Variables: добавить `TELEGRAM_TOKEN`, `ANTHROPIC_API_KEY`, `MANAGER_CHAT_ID`

---

## Структура проекта

```
revitserver-bot/
├── bot/
│   ├── main.py           # Точка входа
│   ├── config.py         # Конфигурация
│   ├── handlers.py       # Обработчики сообщений
│   ├── claude_client.py  # Клиент Claude API
│   ├── dialog_manager.py # Хранение истории диалогов
│   └── knowledge_base.py # База знаний (системный промпт)
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## Как обновить базу знаний

Редактируйте файл `bot/knowledge_base.py` — переменная `SYSTEM_PROMPT`.

Добавьте туда:
- Новые тарифы
- Типичные вопросы из диалогов (FAQ)
- Инструкции по настройке
- Примеры правильных ответов

После изменений — перезапустите бота.

---

## Как добавить диалоги из Telegram в базу знаний

1. В Telegram Desktop: Настройки → Экспорт данных → выбрать нужный чат → JSON формат
2. Запустить скрипт обработки (см. `scripts/process_dialogs.py`)
3. Скопировать полученные FAQ в `knowledge_base.py`

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/help` | Справка |
| `/reset` | Сбросить диалог |
| `/manager` | Связаться с менеджером |

---

## Настройки (config.py)

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `MAX_HISTORY_MESSAGES` | Глубина памяти диалога | 20 |
| `ESCALATION_THRESHOLD` | После N сообщений предложить менеджера | 6 |
| `CLAUDE_MODEL` | Модель Claude | claude-sonnet-4-20250514 |
