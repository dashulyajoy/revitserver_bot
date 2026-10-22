"""
Клиент к языковой модели. Работает с DeepSeek по OpenAI-совместимому формату.

История диалога внутри бота хранится в формате Anthropic (блоки content
с типами text и image). Здесь она конвертируется в формат OpenAI, поэтому
handlers.py и dialog_manager.py трогать не нужно.
"""

import logging
import httpx

from config import (DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL,
                    LLM_MAX_TOKENS, LLM_TIMEOUT)
from knowledge_base import SYSTEM_PROMPT
from kb_updater import get_kb_updates

logger = logging.getLogger(__name__)


def _to_openai(history: list[dict]) -> tuple[list[dict], bool]:
    """
    Переводит историю из формата Anthropic в формат OpenAI.
    Вторым значением возвращает признак, что в истории есть картинки.
    """
    out = []
    has_image = False

    for msg in history:
        content = msg.get("content")
        role = msg.get("role", "user")

        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue

        parts = []
        for block in content or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append({"type": "text", "text": block.get("text", "")})
            elif block.get("type") == "image":
                src = block.get("source", {})
                media = src.get("media_type", "image/jpeg")
                data = src.get("data", "")
                has_image = True
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media};base64,{data}"},
                })
        if parts:
            out.append({"role": role, "content": parts})

    return out, has_image


async def ask_claude(history: list[dict]) -> tuple[str, bool, str]:
    """
    Имя функции оставлено прежним, чтобы не менять handlers.py.
    Возвращает тройку (текст ответа, признак эскалации, причина) -
    эскалация больше не используется и всегда False.
    """
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY не задан")
        return "Не настроен ключ доступа к модели.", False, ""

    kb_updates = await get_kb_updates()
    messages, has_image = _to_openai(history)
    messages = [{"role": "system", "content": SYSTEM_PROMPT + kb_updates}] + messages

    payload = {
        "model": DEEPSEEK_MODEL,
        "max_tokens": LLM_MAX_TOKENS,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            logger.error("Пустой ответ модели: %s", data)
            return "Модель вернула пустой ответ. Попробуйте повторить.", False, ""

        text = (choices[0].get("message") or {}).get("content") or ""
        return text.strip(), False, ""

    except httpx.HTTPStatusError as e:
        body = e.response.text[:500]
        logger.error("Ошибка API: %s %s", e.response.status_code, body)

        # Модель без поддержки картинок отвечает отказом на запрос с изображением.
        # Говорим об этом прямо, а не прячем за общей фразой про неполадки.
        if has_image and e.response.status_code in (400, 415, 422):
            return ("Эта модель не умеет читать картинки. Опишите проблему текстом "
                    "или перечислите, что написано на скриншоте."), False, ""

        if e.response.status_code == 401:
            return "Ключ доступа к модели не принят. Проверьте DEEPSEEK_API_KEY.", False, ""
        if e.response.status_code == 402:
            return "На счёте модели закончились средства.", False, ""
        if e.response.status_code == 429:
            return "Слишком много запросов подряд. Подождите немного.", False, ""

        return "Временные неполадки на стороне модели. Попробуйте повторить.", False, ""

    except httpx.TimeoutException:
        logger.error("Таймаут запроса к модели")
        return "Модель не ответила вовремя. Попробуйте повторить.", False, ""
    except Exception as e:
        logger.error("Ошибка запроса к модели: %s", e)
        return "Что-то пошло не так при обращении к модели.", False, ""
