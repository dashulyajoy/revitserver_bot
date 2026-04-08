import os
from dotenv import load_dotenv

load_dotenv()

# === Telegram ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# === DeepSeek ===
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
# deepseek-chat — быстрая и дешёвая модель (аналог GPT-4o-mini)
# deepseek-reasoner — более мощная, но медленнее и дороже
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# === Уведомления менеджеру ===
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID", "")

# === Настройки бота ===
MAX_HISTORY_MESSAGES = 20
ESCALATION_THRESHOLD = 6
CLAUDE_MAX_TOKENS = 1024

# ID чата с правками к базе знаний (приватная группа менеджера)
KB_CHAT_ID = os.getenv("KB_CHAT_ID", "")
# Сколько последних сообщений из чата брать как правки
KB_MESSAGES_LIMIT = int(os.getenv("KB_MESSAGES_LIMIT", "20"))
