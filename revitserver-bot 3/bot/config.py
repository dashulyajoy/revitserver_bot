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
