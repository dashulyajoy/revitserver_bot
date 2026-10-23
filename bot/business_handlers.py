"""
Ответы в бизнес-чатах Telegram.

Когда бот подключён через «Чат-автоматизацию» в настройках Telegram Business,
сообщения клиентов приходят отдельным типом обновления business_message,
а не обычным message. Поэтому нужны отдельные обработчики.

Бот работает как первая линия: отвечает на общие вопросы и молчит,
когда разговор ушёл в детали. Правила лежат в business_rules.md.

Три причины молчать:
  1. Владелец недавно писал в этот чат - значит он в диалоге
  2. Сообщение содержит явно денежную или документальную тему
  3. Модель сама решила, что вопрос не для первой линии
"""

import asyncio
import logging
import re
import time
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import Message, BusinessConnection

from claude_client import ask_claude
from dialog_manager import dialog_manager
from config import (BUSINESS_ENABLED, BUSINESS_REPLY_DELAY,
                    OWNER_MUTE_MINUTES)

logger = logging.getLogger(__name__)
router = Router()

RULES_FILE = Path(__file__).parent / "business_rules.md"

# Строка, которой модель отвечает, когда вопрос не для первой линии
SILENT_MARKER = "НЕ ОТВЕЧАЮ"

# Темы, на которых бот молчит всегда, не спрашивая модель.
# Список намеренно короткий: только однозначно денежное и документальное.
# Общий вопрос «сколько стоит» сюда не попадает, на него бот отвечает.
HARD_SILENCE = re.compile(
    r"(выстав(ьте|ить|и)\s+счёт|выстав(ьте|ить|и)\s+счет|"
    r"реквизит|оплатил|оплата прошла|оплату отправил|"
    r"акт сверки|закрывающ|верните деньги|возврат средств|"
    r"счёт на оплату|счет на оплату)", re.I)

_pending: dict[int, asyncio.Task] = {}

# id подключения -> id владельца аккаунта.
# Нужно, чтобы не отвечать на собственные сообщения: Telegram присылает
# и входящие от клиента, и ваши исходящие одним типом обновления.
_owners: dict[str, int] = {}

# chat_id -> время последнего сообщения владельца в этом чате
_owner_seen: dict[int, float] = {}


def _load_rules() -> str:
    try:
        return RULES_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        logger.error("business_rules.md не найден, бизнес-правила не применены")
        return ""


BUSINESS_RULES = _load_rules()


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    return text.strip()


def _is_silence(text: str) -> bool:
    """
    Модель решила промолчать. Проверяем с запасом: маркер может прийти
    с точкой, в кавычках или вместе с коротким пояснением.
    """
    if not text:
        return True
    stripped = re.sub(r"[\s«»\"'.!]+", " ", text).strip().upper()
    return stripped.startswith(SILENT_MARKER) or SILENT_MARKER in stripped


@router.business_connection()
async def on_connection(event: BusinessConnection):
    """Срабатывает при подключении и отключении бота к бизнес-аккаунту."""
    _owners[event.id] = event.user.id
    state = "включено" if getattr(event, "is_enabled", True) else "выключено"
    logger.info("Бизнес-подключение %s: владелец %s, %s",
                event.id, event.user.id, state)


def _is_own_message(message: Message) -> bool:
    """Сообщение написано владельцем аккаунта, а не клиентом."""
    if not message.from_user:
        return False
    owner = _owners.get(message.business_connection_id)
    if owner is not None:
        return message.from_user.id == owner
    # Подключение могло произойти до запуска бота, и его id мы не видели.
    # Запасной признак: в личной переписке у клиента id чата совпадает
    # с его собственным id, у владельца - нет.
    return message.from_user.id != message.chat.id


def _owner_is_active(chat_id: int) -> bool:
    seen = _owner_seen.get(chat_id)
    if seen is None:
        return False
    return (time.time() - seen) < OWNER_MUTE_MINUTES * 60


@router.business_message(F.text)
async def on_business_message(message: Message, bot: Bot):
    if not BUSINESS_ENABLED:
        return

    chat_id = message.chat.id

    # Владелец написал сам: запоминаем время и уходим.
    # Заодно снимаем ответ, который бот уже собирался отправить.
    if _is_own_message(message):
        _owner_seen[chat_id] = time.time()
        task = _pending.pop(chat_id, None)
        if task:
            task.cancel()
            logger.info("Чат %s: владелец ответил сам, ответ бота отменён", chat_id)
        dialog_manager.add_assistant_message(chat_id, message.text.strip())
        return

    text = message.text.strip()
    dialog_manager.add_user_message(chat_id, text)

    if _owner_is_active(chat_id):
        logger.info("Чат %s: владелец в диалоге, бот молчит", chat_id)
        return

    if HARD_SILENCE.search(text):
        logger.info("Чат %s: денежная тема, бот молчит", chat_id)
        return

    if chat_id in _pending:
        _pending[chat_id].cancel()
        del _pending[chat_id]

    async def delayed():
        try:
            await asyncio.sleep(BUSINESS_REPLY_DELAY)
            _pending.pop(chat_id, None)

            # За время паузы владелец мог ответить сам
            if _owner_is_active(chat_id):
                logger.info("Чат %s: владелец ответил за время паузы", chat_id)
                return

            await bot.send_chat_action(
                chat_id, "typing",
                business_connection_id=message.business_connection_id,
            )

            history = dialog_manager.get_history(chat_id)
            answer, _, _ = await ask_claude(history, extra_system=BUSINESS_RULES)
            answer = _clean(answer)

            if _is_silence(answer):
                logger.info("Чат %s: вопрос не для первой линии, бот молчит", chat_id)
                return

            dialog_manager.add_assistant_message(chat_id, answer)
            await message.answer(answer)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Ошибка ответа в бизнес-чате %s: %s", chat_id, e)

    _pending[chat_id] = asyncio.create_task(delayed())
