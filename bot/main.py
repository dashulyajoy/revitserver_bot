"""
RevitServer.ru — Telegram Bot
Первая линия поддержки + квалификация лидов
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from handlers import router
from kb_corrections import router as corrections_router
from kb_updater import load_corrections
from config import TELEGRAM_TOKEN

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(corrections_router)
    dp.include_router(router)

    # правки живут в закреплённом сообщении канала, читаем их один раз при старте
    await load_corrections(bot)

    logger.info("RevitServer bot started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
