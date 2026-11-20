import asyncio
import json
import logging
from typing import Optional

from telethon.tl.custom.message import Message as TgMessage

from app.db import is_duplicate, save_message
from app.filters import (
    normalize_text,
    make_hash,
    extract_links_from_text,
    extract_links_from_buttons,
    extract_features,
)
from app.models import Message, MessageStatus
from app.scoring import calculate_score, is_relevant
from app.profile import profile

logger = logging.getLogger(__name__)

# Очередь для передачи релевантных сообщений в notifier.py
notification_queue: asyncio.Queue = asyncio.Queue()


async def process_message(message: TgMessage, chat_title: str) -> Optional[int]:
    """
    Обрабатывает одно сообщение из Telegram-канала.
    Возвращает ID сохранённого сообщения или None, если сообщение пропущено.
    """
    try:
        # 1. Нормализация
        normalized = normalize_text(message.message or "")
        if not normalized:
            logger.debug("Пустое сообщение, пропуск.")
            return None

        # 3. Хэш и дедупликация
        msg_hash = make_hash(normalized)
        if await is_duplicate(msg_hash):
            logger.debug(f"Дубликат пропущен: {msg_hash[:8]}...")
            return None

        # 4. Извлечение ссылок и признаков
        links = extract_links_from_text(normalized)
        links.extend(extract_links_from_buttons(message))
        # Убираем дубли ссылок, сохраняя порядок
        links = list(dict.fromkeys(links))

        features = extract_features(normalized)

        # 4. Скоринг
        score = calculate_score(normalized, features, profile.data)

        # 5. Сохраняем в БД (все сообщения, не только релевантные)
        msg = Message(
            source_tg_id=message.chat_id,
            tg_message_id=message.id,
            text=normalized,
            links=json.dumps(links, ensure_ascii=False),
            features=json.dumps(features, ensure_ascii=False),
            score=score,
            hash=msg_hash,
            status=MessageStatus.NEW,
        )
        msg_id = await save_message(msg)

        # 6. Если релевантно — ставим в очередь на уведомление
        if is_relevant(score):
            logger.info(
                f"🔥 Релевантное сообщение (score={score}) из «{chat_title}», id={msg_id}"
            )
            await notification_queue.put(msg_id)
        else:
            logger.debug(f"Сообщение отклонено (score={score}), id={msg_id}")

        return msg_id

    except Exception as e:
        logger.exception(f"Ошибка в pipeline.process_message: {e}")
        return None

