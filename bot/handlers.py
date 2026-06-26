import asyncio
import base64
import httpx
import json
import logging
import re

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from claude_client import ask_claude
from dialog_manager import dialog_manager
from config import MANAGER_CHAT_ID, ESCALATION_THRESHOLD, KB_CHAT_ID
from kb_updater import add_kb_message, get_kb_messages, remove_kb_message, clear_kb

logger = logging.getLogger(__name__)
router = Router()

_pending: dict[int, asyncio.Task] = {}


def clean_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    return text


@router.message(CommandStart())
async def cmd_start(message: Message):
    dialog_manager.reset(message.chat.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Тарифы", callback_data="info_prices"),
            InlineKeyboardButton(text="Тест-драйв", callback_data="info_trial"),
        ],
        [
            InlineKeyboardButton(text="Revit Server", callback_data="info_rs"),
            InlineKeyboardButton(text="Виртуальное рабочее место", callback_data="info_vdi"),
        ],
        [
            InlineKeyboardButton(text="Связаться с менеджером", callback_data="escalate_manual"),
        ],
    ])
    await message.answer(
        "Здравствуйте. Помогу разобраться с совместной работой в Revit, "
        "подберу тариф и отвечу на вопросы по поддержке.\n\nЧто вас интересует?",
        reply_markup=keyboard,
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    dialog_manager.reset(message.chat.id)
    await message.answer("Диалог сброшен. Чем могу помочь?")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Бот поддержки RevitServer.ru\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/reset — начать диалог заново\n"
        "/manager — связаться с менеджером\n"
        "/kb текст — добавить правку в базу знаний\n"
        "/kblist — список правок\n"
        "/kbdel N — удалить правку\n"
        "/kbclear — очистить все правки\n"
        "/kbstatus — статус базы знаний\n"
        "/testlead — тест уведомления менеджеру"
    )


@router.message(Command("manager"))
async def cmd_manager(message: Message, bot: Bot):
    await _escalate(message, bot, reason="Пользователь запросил менеджера")


@router.message(Command("kb"))
async def cmd_kb(message: Message, bot: Bot):
    text = message.text.replace("/kb", "", 1).strip()
    if not text:
        await message.answer("Напишите правку после команды:\n/kb Текст правки")
        return
    add_kb_message(text)
    msgs = get_kb_messages()
    await message.answer(f"Сохранено. Всего правок: {len(msgs)}")


@router.message(Command("kbstatus"))
async def cmd_kbstatus(message: Message, bot: Bot):
    msgs = get_kb_messages()
    if msgs:
        await message.answer(f"Правок: {len(msgs)}")
    else:
        await message.answer("Правок пока нет.")


@router.message(Command("kblist"))
async def cmd_kblist(message: Message, bot: Bot):
    msgs = get_kb_messages()
    if not msgs:
        await message.answer("Правок пока нет.")
        return
    text = "\n".join(f"{i+1}. {m[:100]}" for i, m in enumerate(msgs))
    await message.answer(f"Правок: {len(msgs)}\n\n{text}\n\nУдалить: /kbdel [номер]\nОчистить: /kbclear")


@router.message(Command("kbdel"))
async def cmd_kbdel(message: Message, bot: Bot):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Укажите номер: /kbdel 3")
        return
    if remove_kb_message(int(args[1]) - 1):
        await message.answer(f"Правка {args[1]} удалена.")
    else:
        await message.answer("Правка не найдена.")


@router.message(Command("kbclear"))
async def cmd_kbclear(message: Message, bot: Bot):
    clear_kb()
    await message.answer("Все правки удалены.")


@router.message(Command("testlead"))
async def cmd_testlead(message: Message, bot: Bot):
    await message.answer(f"Отправляю тест на MANAGER_CHAT_ID: {MANAGER_CHAT_ID}")
    if not MANAGER_CHAT_ID:
        await message.answer("MANAGER_CHAT_ID не задан!")
        return
    try:
        await bot.send_message(MANAGER_CHAT_ID, "Тест уведомления работает!")
        await message.answer("Сообщение отправлено менеджеру — проверьте тот аккаунт")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.callback_query(F.data == "info_prices")
async def cb_prices(callback):
    await callback.answer()
    await callback.message.answer(
        "Тарифы Revit Server:\n\n"
        "- 2-4 чел. — 8 900 руб/мес\n"
        "- 5-8 чел. — 12 600 руб/мес\n"
        "- 9-15 чел. — 16 000 руб/мес\n"
        "- от 15 чел. — от 21 500 руб/мес\n\n"
        "Виртуальное рабочее место (VDI):\n\n"
        "- BIM-Start — 12 500 руб/мес\n"
        "- BIM-Standart — 13 800 руб/мес\n"
        "- BIM-Pro — 17 800 руб/мес\n"
        "- BIM-Render (с GPU) — от 28 500 руб/мес\n\n"
        "Сколько человек в команде?"
    )


@router.callback_query(F.data == "info_trial")
async def cb_trial(callback):
    await callback.answer()
    await callback.message.answer(
        "Тест-драйв бесплатно: Revit Server — 7 дней, VDI — 5 дней. Без предоплаты.\n\n"
        "Напишите сколько человек в команде и версию Revit — оформим доступ."
    )


@router.callback_query(F.data == "info_rs")
async def cb_revit_server(callback):
    await callback.answer()
    await callback.message.answer(
        "Revit Server — сервер для совместной работы над BIM-моделями.\n\n"
        "Бэкапы, VPN, сетевой диск — включены. Версии Revit 2019-2027.\n\n"
        "Сколько человек в команде?"
    )


@router.callback_query(F.data == "info_vdi")
async def cb_vdi(callback):
    await callback.answer()
    await callback.message.answer(
        "Виртуальное рабочее место — Windows в облаке с Revit и AutoCAD.\n\n"
        "Полные права администратора, SSH, любой софт. От 12 500 руб/мес.\n\n"
        "Расскажите о вашей задаче."
    )


@router.callback_query(F.data == "escalate_manual")
async def cb_escalate_manual(callback, bot: Bot):
    await callback.answer()
    await _escalate(
        callback.message, bot,
        reason="Пользователь нажал кнопку 'Связаться с менеджером'",
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name
    )


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    chat_id = message.chat.id
    if dialog_manager.is_escalated(chat_id):
        return

    # Группируем фото как и текстовые сообщения
    if chat_id in _pending:
        _pending[chat_id].cancel()
        del _pending[chat_id]

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(file_url)
        image_data = base64.b64encode(resp.content).decode("utf-8")

    caption = message.caption or "Посмотри на этот скриншот и помоги разобраться с проблемой."

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}
            },
            {"type": "text", "text": caption}
        ]
    }

    dialog_manager._histories[chat_id].append(user_message)
    dialog_manager._message_counts[chat_id] += 1

    async def delayed_photo_response():
        try:
            await asyncio.sleep(4)
            if chat_id in _pending:
                del _pending[chat_id]
            await bot.send_chat_action(chat_id, "typing")
            history = dialog_manager.get_history(chat_id)
            response_text, should_escalate, escalation_reason = await ask_claude(history)
            dialog_manager.add_assistant_message(chat_id, response_text)
            if response_text:
                await message.answer(clean_markdown(response_text))
            if should_escalate:
                await _escalate(message, bot, reason=escalation_reason)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(delayed_photo_response())
    _pending[chat_id] = task


@router.message(F.text)
async def handle_message(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_text = message.text.strip()

    if dialog_manager.is_escalated(chat_id):
        return

    dialog_manager.add_user_message(chat_id, user_text)

    if chat_id in _pending:
        _pending[chat_id].cancel()
        del _pending[chat_id]

    async def delayed_response():
        try:
            await asyncio.sleep(4)
            if chat_id in _pending:
                del _pending[chat_id]

            await bot.send_chat_action(chat_id, "typing")

            history = dialog_manager.get_history(chat_id)
            response_text, should_escalate, escalation_reason = await ask_claude(history)
            dialog_manager.add_assistant_message(chat_id, response_text)

            if response_text:
                await message.answer(clean_markdown(response_text))

            if should_escalate:
                await _escalate(message, bot, reason=escalation_reason)
                return

            count = dialog_manager.get_message_count(chat_id)
            if count == ESCALATION_THRESHOLD:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Поговорить с менеджером", callback_data="escalate_manual"),
                ]])
                await message.answer(
                    "Если нужно — могу передать вас менеджеру.",
                    reply_markup=keyboard,
                )
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(delayed_response())
    _pending[chat_id] = task


async def _escalate(
    message: Message,
    bot: Bot,
    reason: str = "",
    notify_user: bool = True,
    user_id: int = None,
    username: str = None,
    full_name: str = None,
):
    chat_id = message.chat.id
    dialog_manager.mark_escalated(chat_id)

    uid = user_id or (message.from_user.id if message.from_user else chat_id)
    uname = username or (message.from_user.username if message.from_user else None)
    fname = full_name or (message.from_user.full_name if message.from_user else "Неизвестно")

    if notify_user:
        await message.answer(
            "Передаю вас менеджеру, он свяжется в ближайшее время.\n\n"
            "Можете также написать напрямую: @revitserver"
        )

    if MANAGER_CHAT_ID:
        history = dialog_manager.get_history(chat_id)

        def get_content_text(m):
            c = m.get('content', '')
            if isinstance(c, str):
                return c[:200]
            if isinstance(c, list):
                texts = [p.get('text', '') for p in c if isinstance(p, dict) and p.get('type') == 'text']
                return ' '.join(texts)[:200] + ' [фото]'
            return str(c)[:200]

        history_lines = []
        for m in history[-10:]:
            icon = 'Клиент' if m['role'] == 'user' else 'Бот'
            history_lines.append(f"{icon}: {get_content_text(m)}")
        history_text = "\n".join(history_lines)

        user_link = f"@{uname}" if uname else f"{fname} (id:{uid})"

        manager_msg = (
            f"Горячий лид / Эскалация\n\n"
            f"Пользователь: {user_link}\n"
            f"ID: {uid}\n"
            f"Причина: {reason}\n\n"
            f"Последний диалог:\n{history_text}"
        )

        try:
            await bot.send_message(MANAGER_CHAT_ID, manager_msg)
        except Exception as e:
            logger.error(f"Failed to notify manager: {e}")
