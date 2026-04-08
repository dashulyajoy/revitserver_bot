"""
База знаний из чата менеджера.
Правки сохраняются в файл — не теряются при перезапуске.
"""

import json
import logging
import os
from config import KB_CHAT_ID, KB_MESSAGES_LIMIT

logger = logging.getLogger(__name__)

KB_FILE = "/app/kb_messages.json"

def _load() -> list[str]:
    try:
        if os.path.exists(KB_FILE):
            with open(KB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"KB load error: {e}")
    return []

def _save(messages: list[str]):
    try:
        with open(KB_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"KB save error: {e}")

def add_kb_message(text: str):
    if not text or text.startswith("/"):
        return
    messages = _load()
    messages.append(text)
    if len(messages) > KB_MESSAGES_LIMIT:
        messages = messages[-KB_MESSAGES_LIMIT:]
    _save(messages)
    logger.info(f"KB updated: {text[:50]}...")

def remove_kb_message(index: int) -> bool:
    messages = _load()
    if 0 <= index < len(messages):
        removed = messages.pop(index)
        _save(messages)
        logger.info(f"KB removed: {removed[:50]}...")
        return True
    return False

def clear_kb():
    _save([])

def get_kb_messages() -> list[str]:
    return _load()

async def get_kb_updates() -> str:
    messages = _load()
    if not messages:
        return ""
    return "\n\n## Актуальные правки и дополнения от менеджера\n" + "\n".join(f"- {m}" for m in messages)
