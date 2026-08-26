"""
Приём правок к базе знаний без команд.

Два способа, оба без ввода команд вручную:
  1. Кнопка «поправить» под каждым ответом бота
  2. Ответ реплаем на любое сообщение бота

Плюс служебный обработчик: если написать в канале слово «id»,
бот пришлёт туда идентификатор канала, чтобы не искать его вручную.
"""

import logging

from aiogram import Router, F, Bot
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)

from config import KB_EDITORS
from kb_updater import add_correction

logger = logging.getLogger(__name__)
router = Router()

# message_id ответа бота -> (вопрос пользователя, ответ бота)
_answers: dict[int, tuple[str, str]] = {}

# user_id -> message_id ответа, к которому пишется правка
_awaiting: dict[int, int] = {}

FIX_PREFIX = "fix:"


def fix_keyboard(message_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="поправить",
                             callback_data=f"{FIX_PREFIX}{message_id}")
    ]])


def may_edit(user_id: int) -> bool:
    """Пустой список KB_EDITORS означает, что править может кто угодно."""
    return not KB_EDITORS or user_id in KB_EDITORS


def remember(message_id: int, question: str, answer: str) -> None:
    _answers[message_id] = (question, answer)
    # не копим бесконечно
    if len(_answers) > 500:
        for k in list(_answers)[:200]:
            _answers.pop(k, None)


def is_awaiting(user_id: int) -> bool:
    return user_id in _awaiting


@router.callback_query(F.data.startswith(FIX_PREFIX))
async def cb_fix(callback: CallbackQuery):
    if not may_edit(callback.from_user.id):
        await callback.answer("Правки может вносить только администратор",
                              show_alert=True)
        return
    try:
        target = int(callback.data[len(FIX_PREFIX):])
    except ValueError:
        await callback.answer()
        return

    _awaiting[callback.from_user.id] = target
    await callback.answer()
    await callback.message.answer(
        "Напишите, как правильно. Следующее ваше сообщение я запомню как правку "
        "и учту в дальнейших ответах."
    )


async def consume_correction(message: Message, bot: Bot) -> bool:
    """
    Забирает сообщение как правку, если бот её ждёт или это реплай на его ответ.
    Возвращает True, если сообщение обработано и дальше его вести не нужно.
    """
    user_id = message.from_user.id
    if not may_edit(user_id):
        return False

    target = _awaiting.pop(user_id, None)

    # реплай на сообщение бота тоже считаем правкой
    if target is None:
        reply = message.reply_to_message
        if reply and reply.from_user and reply.from_user.is_bot:
            target = reply.message_id
        else:
            return False

    question, wrong = _answers.get(target, ("", ""))
    author = message.from_user.full_name or str(user_id)

    total = await add_correction(
        bot,
        correction=message.text.strip(),
        question=question,
        wrong_answer=wrong,
        author=author,
    )
    await message.answer(f"Записал. Всего действующих правок: {total}")
    return True


@router.channel_post(F.text.lower().strip() == "id")
async def channel_id_helper(message: Message):
    """Подсказка при настройке: пишем «id» в канале, получаем его номер."""
    await message.answer(
        f"Идентификатор этого канала: {message.chat.id}\n\n"
        f"Впишите его в переменную KB_CHANNEL_ID в настройках бота."
    )
