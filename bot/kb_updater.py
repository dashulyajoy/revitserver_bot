"""
Правки к базе знаний.

Хранятся в закреплённом сообщении приватного канала в Telegram.
Это решает две проблемы старой схемы:
  1. Файл на диске стирался при каждом передеплое на Railway и Render
  2. Правки было не видно, приходилось верить команде /kblist

Теперь всё видно прямо в канале: закреплённое сообщение - действующий список
правок, обычные сообщения ниже - журнал с полным контекстом каждой правки.
"""

import logging
import re
from datetime import datetime, timezone, timedelta

from config import KB_CHANNEL_ID, KB_MESSAGES_LIMIT

logger = logging.getLogger(__name__)

HEADER = "ПРАВКИ К БАЗЕ ЗНАНИЙ"
TG_LIMIT = 4000          # с запасом от телеграмного лимита в 4096
MSK = timezone(timedelta(hours=3))

# Кэш в памяти. Источник истины - закреплённое сообщение в канале,
# но дёргать API на каждый запрос к Claude слишком расточительно.
_corrections: list[str] = []
_pinned_id: int | None = None
_loaded = False


def _render(items: list[str]) -> str:
    stamp = datetime.now(MSK).strftime("%d.%m.%Y %H:%M")
    lines = [HEADER, f"Обновлено {stamp} МСК", ""]
    lines += [f"{i}. {t}" for i, t in enumerate(items, 1)]
    text = "\n".join(lines)
    # если не влезаем в лимит, отбрасываем самые старые правки
    while len(text) > TG_LIMIT and len(items) > 1:
        items.pop(0)
        lines = [HEADER, f"Обновлено {stamp} МСК", ""]
        lines += [f"{i}. {t}" for i, t in enumerate(items, 1)]
        text = "\n".join(lines)
    return text


def _parse(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\.\s+(.*\S)\s*$", line)
        if m:
            out.append(m.group(1))
    return out


async def load_corrections(bot) -> None:
    """Читает правки из закреплённого сообщения. Вызывается один раз при старте."""
    global _corrections, _pinned_id, _loaded
    _loaded = True
    if not KB_CHANNEL_ID:
        logger.warning("KB_CHANNEL_ID не задан - правки к базе знаний отключены")
        return
    try:
        chat = await bot.get_chat(KB_CHANNEL_ID)
    except Exception as e:
        logger.error("Не удалось прочитать канал правок: %s", e)
        return

    pinned = getattr(chat, "pinned_message", None)
    if not pinned or not (pinned.text or "").startswith(HEADER):
        logger.info("Закреплённого списка правок пока нет, начинаем с чистого листа")
        return

    _pinned_id = pinned.message_id
    _corrections = _parse(pinned.text)
    logger.info("Загружено правок: %d", len(_corrections))


async def add_correction(bot, correction: str, question: str = "",
                         wrong_answer: str = "", author: str = "") -> int:
    """Добавляет правку, обновляет закреплённый список и пишет в журнал."""
    global _corrections, _pinned_id

    correction = correction.strip()
    if not correction:
        return len(_corrections)

    _corrections.append(correction)
    if len(_corrections) > KB_MESSAGES_LIMIT:
        _corrections = _corrections[-KB_MESSAGES_LIMIT:]

    if not KB_CHANNEL_ID:
        logger.warning("Правка принята только в память: KB_CHANNEL_ID не задан")
        return len(_corrections)

    text = _render(_corrections)
    try:
        if _pinned_id:
            await bot.edit_message_text(chat_id=KB_CHANNEL_ID,
                                        message_id=_pinned_id, text=text)
        else:
            msg = await bot.send_message(KB_CHANNEL_ID, text)
            _pinned_id = msg.message_id
            await bot.pin_chat_message(KB_CHANNEL_ID, _pinned_id,
                                       disable_notification=True)
    except Exception as e:
        logger.error("Не удалось обновить закреплённый список правок: %s", e)

    # журнал: полный контекст, чтобы потом было видно, на чём бот споткнулся
    parts = ["НОВАЯ ПРАВКА", ""]
    if author:
        parts.append(f"Автор: {author}")
    if question:
        parts.append(f"Вопрос был: {question[:600]}")
    if wrong_answer:
        parts.append(f"Бот ответил: {wrong_answer[:900]}")
    parts.append(f"Правильно: {correction}")
    try:
        await bot.send_message(KB_CHANNEL_ID, "\n\n".join(parts))
    except Exception as e:
        logger.error("Не удалось записать правку в журнал: %s", e)

    return len(_corrections)


def get_corrections() -> list[str]:
    return list(_corrections)


async def get_kb_updates() -> str:
    """
    Блок, который приклеивается к базе знаний при каждом запросе.

    Важно: правки идут с явным указанием приоритета. Без него свежая правка
    спорит на равных с основным текстом базы и обычно проигрывает ему,
    потому что основной текст длиннее и выглядит авторитетнее.
    """
    if not _corrections:
        return ""
    body = "\n".join(f"- {t}" for t in _corrections)
    return (
        "\n\n## Уточнения, внесённые позже\n\n"
        "Эти уточнения добавлены после составления базы знаний выше. "
        "Если они противоречат чему-то в основном тексте, верны они, "
        "а основной текст устарел.\n\n"
        f"{body}\n"
    )
