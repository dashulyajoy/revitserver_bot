"""
Менеджер диалогов — хранит историю переписки для каждого пользователя
"""

from collections import defaultdict
from config import MAX_HISTORY_MESSAGES


class DialogManager:
    def __init__(self):
        # chat_id -> list of {"role": "user"/"assistant", "content": "..."}
        self._histories: dict[int, list[dict]] = defaultdict(list)
        # chat_id -> bool (эскалирован ли диалог)
        self._escalated: dict[int, bool] = defaultdict(bool)
        # chat_id -> количество сообщений
        self._message_counts: dict[int, int] = defaultdict(int)

    def add_user_message(self, chat_id: int, text: str):
        self._histories[chat_id].append({"role": "user", "content": text})
        self._message_counts[chat_id] += 1
        self._trim(chat_id)

    def add_assistant_message(self, chat_id: int, text: str):
        self._histories[chat_id].append({"role": "assistant", "content": text})
        self._trim(chat_id)

    def get_history(self, chat_id: int) -> list[dict]:
        return list(self._histories[chat_id])

    def get_message_count(self, chat_id: int) -> int:
        return self._message_counts[chat_id]

    def mark_escalated(self, chat_id: int):
        self._escalated[chat_id] = True

    def is_escalated(self, chat_id: int) -> bool:
        return self._escalated[chat_id]

    def reset(self, chat_id: int):
        self._histories[chat_id] = []
        self._escalated[chat_id] = False
        self._message_counts[chat_id] = 0

    def _trim(self, chat_id: int):
        """Оставляем только последние N сообщений"""
        history = self._histories[chat_id]
        if len(history) > MAX_HISTORY_MESSAGES:
            self._histories[chat_id] = history[-MAX_HISTORY_MESSAGES:]


# Глобальный экземпляр
dialog_manager = DialogManager()
