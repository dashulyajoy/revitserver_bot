import os
from dotenv import load_dotenv

load_dotenv()

# === Telegram ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# === Языковая модель (DeepSeek) ===
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# === Уведомления менеджеру ===
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID", "")

# === Настройки бота ===
MAX_HISTORY_MESSAGES = 20
ESCALATION_THRESHOLD = 6
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))

# === Режим Telegram Business ===
# Бот отвечает клиентам в чатах, подключённых через «Чат-автоматизацию».
# Чтобы временно выключить ответы, не трогая код: BUSINESS_ENABLED=0
BUSINESS_ENABLED = os.getenv("BUSINESS_ENABLED", "1") not in ("0", "false", "False", "")
# Пауза перед ответом: клиент часто пишет несколько сообщений подряд
BUSINESS_REPLY_DELAY = float(os.getenv("BUSINESS_REPLY_DELAY", "8"))
# Сколько минут бот молчит в чате после вашего собственного сообщения
OWNER_MUTE_MINUTES = float(os.getenv("OWNER_MUTE_MINUTES", "60"))

# === Правки к базе знаний ===
# Приватный канал, где живут правки. Закреплённое сообщение - действующий
# список, обычные сообщения ниже - журнал с контекстом каждой правки.
# Чтобы узнать номер канала: добавьте бота администратором и напишите там «id».
KB_CHANNEL_ID = os.getenv("KB_CHANNEL_ID", "")

# Сколько правок держать. Самые старые вытесняются.
KB_MESSAGES_LIMIT = int(os.getenv("KB_MESSAGES_LIMIT", "40"))

# Кому можно вносить правки: id через запятую.
# Пустое значение означает, что править может кто угодно.
KB_EDITORS = {
    int(x) for x in os.getenv("KB_EDITORS", "").replace(" ", "").split(",") if x
}
