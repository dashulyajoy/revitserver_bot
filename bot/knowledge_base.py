"""
База знаний бота.

Сам текст лежит в соседнем файле knowledge_base.md — обычный текст,
его можно править прямо на GitHub, не трогая код.

Остальной код по-прежнему импортирует отсюда SYSTEM_PROMPT,
поэтому менять больше ничего не нужно.
"""

from pathlib import Path

KB_FILE = Path(__file__).parent / "knowledge_base.md"

# Запасной вариант на случай, если файл не найден: бот не должен молча
# отвечать с пустой базой, лучше честно сказать, что справочник недоступен.
_FALLBACK = (
    "Ты — помощник компании RevitServer.ru. Общаешься в Telegram от лица компании.\n"
    "Файл базы знаний не найден, поэтому фактами ты сейчас не располагаешь.\n"
    "Отвечай кратко, на «Вы», без markdown, и на любой содержательный вопрос "
    "говори, что уточнишь информацию у коллег."
)


def load_knowledge_base() -> str:
    try:
        text = KB_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return _FALLBACK
    return text or _FALLBACK


SYSTEM_PROMPT = load_knowledge_base()
