"""
Скрипт для обработки выгрузки диалогов из Telegram Desktop (JSON формат)
и извлечения полезных FAQ для базы знаний бота.

Использование:
    python process_dialogs.py --input result.json --output faq_output.txt

Файл result.json — экспорт из Telegram Desktop:
    Настройки → Экспорт данных Telegram → выбрать чат → JSON
"""

import json
import argparse
import sys
from pathlib import Path


def load_telegram_export(path: str) -> list[dict]:
    """Загружает экспорт Telegram Desktop."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    print(f"✅ Загружено {len(messages)} сообщений")
    return messages


def extract_qa_pairs(messages: list[dict]) -> list[dict]:
    """
    Извлекает пары вопрос-ответ из диалога.
    Предполагает что пользователь пишет вопрос, менеджер отвечает.
    """
    pairs = []
    i = 0

    while i < len(messages) - 1:
        msg = messages[i]

        # Пропускаем системные сообщения
        if msg.get("type") != "message":
            i += 1
            continue

        # Получаем текст сообщения
        text = _get_text(msg)
        if not text or len(text) < 10:
            i += 1
            continue

        # Смотрим на следующее сообщение (ответ)
        next_msg = messages[i + 1] if i + 1 < len(messages) else None
        if next_msg and next_msg.get("type") == "message":
            reply_text = _get_text(next_msg)
            if reply_text and len(reply_text) > 20:
                # Разные отправители = диалог
                if msg.get("from_id") != next_msg.get("from_id"):
                    pairs.append({
                        "question": text.strip(),
                        "answer": reply_text.strip(),
                    })
        i += 1

    print(f"✅ Найдено {len(pairs)} пар вопрос-ответ")
    return pairs


def _get_text(msg: dict) -> str:
    """Извлекает текст из сообщения (с учётом форматирования Telegram)."""
    text = msg.get("text", "")
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        # Telegram хранит форматированный текст как список
        parts = []
        for part in text:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", ""))
        return "".join(parts)
    return ""


def format_for_knowledge_base(pairs: list[dict], max_pairs: int = 50) -> str:
    """Форматирует пары для добавления в knowledge_base.py."""
    lines = [
        "# ─────────────────────────────────────────────",
        "# FAQ из реальных диалогов",
        "# Добавьте этот блок в SYSTEM_PROMPT в knowledge_base.py",
        "# ─────────────────────────────────────────────",
        "",
        "## Реальные вопросы клиентов и ответы",
        "",
    ]

    # Берём первые max_pairs пар
    for i, pair in enumerate(pairs[:max_pairs]):
        q = pair["question"]
        a = pair["answer"]

        # Пропускаем слишком короткие или нерелевантные
        if len(q) < 15 or len(a) < 15:
            continue

        lines.append(f"**Вопрос:** {q}")
        lines.append(f"**Ответ:** {a}")
        lines.append("")

    return "\n".join(lines)


def save_output(text: str, path: str):
    """Сохраняет результат."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✅ Сохранено в {path}")


def main():
    parser = argparse.ArgumentParser(description="Обработка диалогов Telegram для базы знаний")
    parser.add_argument("--input", required=True, help="Путь к result.json из экспорта Telegram")
    parser.add_argument("--output", default="faq_output.txt", help="Куда сохранить результат")
    parser.add_argument("--max", type=int, default=50, help="Максимум пар вопрос-ответ")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"❌ Файл не найден: {args.input}")
        sys.exit(1)

    messages = load_telegram_export(args.input)
    pairs = extract_qa_pairs(messages)

    if not pairs:
        print("⚠️  Не найдено пар вопрос-ответ. Проверьте формат файла.")
        sys.exit(1)

    formatted = format_for_knowledge_base(pairs, max_pairs=args.max)
    save_output(formatted, args.output)

    print(f"\n📋 Инструкция:")
    print(f"1. Откройте {args.output}")
    print(f"2. Просмотрите и отредактируйте FAQ")
    print(f"3. Добавьте содержимое в SYSTEM_PROMPT в bot/knowledge_base.py")
    print(f"4. Перезапустите бота")


if __name__ == "__main__":
    main()
