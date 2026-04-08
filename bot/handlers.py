"""
Обработчики сообщений Telegram бота
"""

import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from claude_client import ask_claude
from dialog_manager import dialog_manager
from config import MANAGER_CHAT_ID, ESCALATION_THRESHOLD

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    chat_id = message.chat.id
    dialog_manager.reset(chat_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Тарифы", callback_data="info_prices"),
            InlineKeyboardButton(text="🆓 Тест-драйв", callback_data="info_trial"),
        ],
        [
            InlineKeyboardButton(text="🖥 Revit Server", callback_data="info_rs"),
            InlineKeyboardButton(text="💻 Виртуальное рабочее место", callback_data="info_vdi"),
        ],
        [
            InlineKeyboardButton(text="👨‍💼 Связаться с менеджером", callback_data="escalate_manual"),
        ],
    ])

    await message.answer(
        "Привет! 👋 Я помощник RevitServer.ru\n\n"
        "Помогу разобраться с совместной работой в Revit, подберу тариф "
        "и отвечу на вопросы по поддержке.\n\n"
        "Что вас интересует?",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────
# /reset — сбросить диалог
# ─────────────────────────────────────────────

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    dialog_manager.reset(message.chat.id)
    await message.answer("Диалог сброшен. Начнём сначала! Чем могу помочь?")


# ─────────────────────────────────────────────
# /help
# ─────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 *RevitServer.ru — бот поддержки*\n\n"
        "Я могу помочь с:\n"
        "• Вопросами о Revit Server и VDI\n"
        "• Подбором тарифа под вашу команду\n"
        "• Технической поддержкой\n"
        "• Оформлением тест-драйва\n\n"
        "Просто напишите ваш вопрос или используйте /start для меню.\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/reset — начать диалог заново\n"
        "/manager — связаться с менеджером",
    )


# ─────────────────────────────────────────────
# /kbstatus — проверить правки из чата
# ─────────────────────────────────────────────

@router.message(Command("kbstatus"))
async def cmd_kbstatus(message: Message, bot: Bot):
    from kb_updater import get_kb_updates
    from config import KB_CHAT_ID
    updates = await get_kb_updates()
    if not KB_CHAT_ID:
        await message.answer("KB_CHAT_ID не задан в переменных окружения.")
        return
    if updates:
        await message.answer(f"Правки загружены из чата {KB_CHAT_ID}:\n\n{updates[:1000]}")
    else:
        await message.answer(f"Чат {KB_CHAT_ID} подключён, но правок пока нет.")

# ─────────────────────────────────────────────
# /testlead — тест уведомления менеджеру
# ─────────────────────────────────────────────

@router.message(Command("testlead"))
async def cmd_testlead(message: Message, bot: Bot):
    from config import MANAGER_CHAT_ID
    await message.answer(f"Отправляю тест на MANAGER_CHAT_ID: {MANAGER_CHAT_ID}")
    if not MANAGER_CHAT_ID:
        await message.answer("❌ MANAGER_CHAT_ID не задан в переменных окружения!")
        return
    try:
        await bot.send_message(
            MANAGER_CHAT_ID,
            "✅ Тест уведомления работает! Бот может писать менеджеру."
        )
        await message.answer("✅ Сообщение отправлено менеджеру — проверьте тот аккаунт")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ─────────────────────────────────────────────
# /manager — ручная эскалация
# ─────────────────────────────────────────────

@router.message(Command("manager"))
async def cmd_manager(message: Message, bot: Bot):
    await _escalate(message, bot, reason="Пользователь запросил менеджера вручную")


# ─────────────────────────────────────────────
# Inline кнопки
# ─────────────────────────────────────────────

@router.callback_query(F.data == "info_prices")
async def cb_prices(callback):
    await callback.answer()
    await callback.message.answer(
        "Тарифы Revit Server:\n\n"
        "- 2–4 чел. — 8 900 руб/мес\n"
        "- 5–8 чел. — 11 200 руб/мес\n"
        "- 9–15 чел. — 14 600 руб/мес\n"
        "- от 15 чел. — от 17 500 руб/мес\n\n"
        "Виртуальное рабочее место (VDI):\n\n"
        "- BIM-Start — 10 500 руб/мес\n"
        "- BIM-Standart — 12 500 руб/мес\n"
        "- BIM-Pro — 16 000 руб/мес\n\n"
        "Сколько человек в команде — подберу подходящий вариант.",
    )


@router.callback_query(F.data == "info_trial")
async def cb_trial(callback):
    await callback.answer()
    await callback.message.answer(
        "Бесплатный тест — 7 дней, без предоплаты.\n\n"
        "Напишите сколько человек в команде и версию Revit — оформим доступ за 1-2 часа.",
    )


@router.callback_query(F.data == "info_rs")
async def cb_revit_server(callback):
    await callback.answer()
    await callback.message.answer(
        "Revit Server — сервер для совместной работы над BIM-моделями.\n\n"
        "Готово за 1-2 часа после оплаты. Бэкапы, VPN, сетевой диск — включены.\n\n"
        "Сколько человек в команде?",
    )


@router.callback_query(F.data == "info_vdi")
async def cb_vdi(callback):
    await callback.answer()
    await callback.message.answer(
        "Виртуальное рабочее место — Windows в облаке с Revit и AutoCAD.\n\n"
        "Подходит для удалённых команд или если слабое железо на местах. От 10 500 руб/мес.\n\n"
        "Расскажите о вашей задаче — подберём конфигурацию.",
    )


@router.callback_query(F.data == "escalate_manual")
async def cb_escalate_manual(callback, bot: Bot):
    await callback.answer()
    await _escalate(callback.message, bot, reason="Пользователь нажал кнопку 'Связаться с менеджером'",
                    user_id=callback.from_user.id,
                    username=callback.from_user.username,
                    full_name=callback.from_user.full_name)


# ─────────────────────────────────────────────
# Основной обработчик сообщений
# ─────────────────────────────────────────────

@router.message(F.text)
async def handle_message(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_text = message.text.strip()

    # Если уже эскалирован — не отвечаем (менеджер ведёт диалог)
    if dialog_manager.is_escalated(chat_id):
        return

    # Добавляем сообщение пользователя в историю
    dialog_manager.add_user_message(chat_id, user_text)

    # Показываем "печатает..."
    await bot.send_chat_action(chat_id, "typing")

    # Запрашиваем ответ у Claude
    history = dialog_manager.get_history(chat_id)
    response_text, should_escalate, escalation_reason = await ask_claude(history)

    # Сохраняем ответ ассистента
    dialog_manager.add_assistant_message(chat_id, response_text)

    # Отправляем ответ пользователю
    if response_text:
        await message.answer(response_text)

    # Эскалация по решению Claude
    if should_escalate:
        await _escalate(
            message, bot,
            reason=escalation_reason,
            notify_user=not bool(response_text),  # если Claude уже написал про менеджера
        )
        return

    # Предлагаем менеджера после N сообщений
    count = dialog_manager.get_message_count(chat_id)
    if count == ESCALATION_THRESHOLD:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👨‍💼 Поговорить с менеджером", callback_data="escalate_manual"),
        ]])
        await message.answer(
            "Если хотите — могу передать вас живому специалисту, "
            "который ответит на все вопросы и поможет с оформлением.",
            reply_markup=keyboard,
        )


# ─────────────────────────────────────────────
# Вспомогательная функция эскалации
# ─────────────────────────────────────────────

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

    uid = user_id or message.from_user.id if message.from_user else chat_id
    uname = username or (message.from_user.username if message.from_user else None)
    fname = full_name or (message.from_user.full_name if message.from_user else "Неизвестно")

    # Уведомляем пользователя
    if notify_user:
        await message.answer(
            "Передаю вас менеджеру, он свяжется в ближайшее время.\n\n"
            "Можете также написать напрямую: @revitserver"
        )

    # Уведомляем менеджера
    if MANAGER_CHAT_ID:
        history = dialog_manager.get_history(chat_id)
        history_text = "\n".join(
            f"{'👤' if m['role'] == 'user' else '🤖'} {m['content']}"
            for m in history[-10:]  # последние 10 сообщений
        )

        user_link = f"@{uname}" if uname else f"[{fname}](tg://user?id={uid})"

        manager_msg = (
            f"🔔 *Горячий лид / Эскалация*\n\n"
            f"👤 Пользователь: {user_link}\n"
            f"🆔 ID: `{uid}`\n"
            f"📋 Причина: {reason}\n\n"
            f"*Последний диалог:*\n"
            f"```\n{history_text}\n```"
        )

        try:
            await bot.send_message(
                MANAGER_CHAT_ID,
                manager_msg,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to notify manager: {e}")
