"""
Подгружает правки к базе знаний из приватного чата менеджера.
Последние N сообщений из чата добавляются к системному промпту.
"""

import logging
import httpx
from config import TELEGRAM_TOKEN, KB_CHAT_ID, KB_MESSAGES_LIMIT

logger = logging.getLogger(__name__)

# Кэш сообщений — обновляется раз в 5 минут
_cached_updates = ""
_cache_time = 0


async def get_kb_updates() -> str:
    """Возвращает последние правки из чата менеджера."""
    global _cached_updates, _cache_time

    import time
    now = time.time()

    # Кэш на 5 минут — не дёргаем API при каждом сообщении
    if now - _cache_time < 300 and _cached_updates is not None:
        return _cached_updates

    if not KB_CHAT_ID or not TELEGRAM_TOKEN:
        return ""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"limit": 100},
            )
            data = response.json()

        if not data.get("ok"):
            return ""

        # Фильтруем сообщения из нашего чата
        messages = []
        for update in data.get("result", []):
            msg = update.get("message") or update.get("channel_post")
            if not msg:
                continue
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if chat_id != str(KB_CHAT_ID):
                continue
            text = msg.get("text", "").strip()
            if text and not text.startswith("/"):
                messages.append(text)

        # Берём последние N сообщений
        recent = messages[-KB_MESSAGES_LIMIT:] if messages else []

        if recent:
            _cached_updates = "\n\n## Актуальные правки и дополнения от менеджера\n" + "\n".join(f"- {m}" for m in recent)
        else:
            _cached_updates = ""

        _cache_time = now
        return _cached_updates

    except Exception as e:
        logger.error(f"KB updater error: {e}")
        return ""
