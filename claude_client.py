"""
Клиент для работы с Claude API (Anthropic)
"""

import json
import logging
import httpx
from config import ANTHROPIC_API_KEY, CLAUDE_MAX_TOKENS
from knowledge_base import SYSTEM_PROMPT
from kb_updater import get_kb_updates

logger = logging.getLogger(__name__)


async def ask_claude(history: list[dict]) -> tuple[str, bool, str]:
    """
    Отправляет историю диалога в Claude и возвращает ответ.

    Returns:
        (text_response, should_escalate, escalation_reason)
    """
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    # Подгружаем актуальные правки из чата менеджера
    kb_updates = await get_kb_updates()
    full_prompt = SYSTEM_PROMPT + kb_updates

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": CLAUDE_MAX_TOKENS,
        "system": full_prompt,
        "messages": history,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["content"][0]["text"]

            # Проверяем маркер эскалации
            should_escalate = False
            escalation_reason = ""
            clean_text = raw_text

            if '{"escalate": true' in raw_text or '"escalate":true' in raw_text:
                should_escalate = True
                try:
                    start = raw_text.find('{"escalate"')
                    end = raw_text.find('}', start) + 1
                    json_str = raw_text[start:end]
                    meta = json.loads(json_str)
                    escalation_reason = meta.get("reason", "")
                    clean_text = raw_text[:start].strip() + raw_text[end:].strip()
                    clean_text = clean_text.strip()
                except Exception:
                    pass

            return clean_text, should_escalate, escalation_reason

    except httpx.HTTPStatusError as e:
        logger.error(f"Claude API HTTP error: {e.response.status_code} {e.response.text}")
        return "Извините, временные неполадки. Напишите напрямую: @revitserver", False, ""
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "Что-то пошло не так. Напишите нам: @revitserver", False, ""
