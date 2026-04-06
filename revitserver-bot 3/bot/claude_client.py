"""
Клиент для работы с DeepSeek API (совместим с OpenAI-форматом)
"""

import json
import logging
import httpx
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, CLAUDE_MAX_TOKENS
from knowledge_base import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def ask_claude(history: list[dict]) -> tuple[str, bool, str]:
    """
    Отправляет историю диалога в DeepSeek и возвращает ответ.

    Returns:
        (text_response, should_escalate, escalation_reason)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    payload = {
        "model": DEEPSEEK_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]

            # Проверяем, нет ли маркера эскалации в ответе
            should_escalate = False
            escalation_reason = ""
            clean_text = raw_text

            if '{"escalate": true' in raw_text or '"escalate":true' in raw_text:
                should_escalate = True
                # Извлекаем JSON маркер из текста
                try:
                    start = raw_text.find('{"escalate"')
                    end = raw_text.find('}', start) + 1
                    json_str = raw_text[start:end]
                    meta = json.loads(json_str)
                    escalation_reason = meta.get("reason", "")
                    # Убираем JSON из текста для пользователя
                    clean_text = raw_text[:start].strip() + raw_text[end:].strip()
                    clean_text = clean_text.strip()
                except Exception:
                    pass

            return clean_text, should_escalate, escalation_reason

    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP error: {e.response.status_code} {e.response.text}")
        return "Извините, временные технические неполадки. Попробуйте чуть позже или напишите напрямую в @revitserver", False, ""
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Что-то пошло не так. Напишите нам напрямую — @revitserver", False, ""
