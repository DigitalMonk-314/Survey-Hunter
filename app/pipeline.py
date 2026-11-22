import json
import logging
import asyncio
from typing import Optional, Dict, Any

from app.db import is_duplicate, save_message
from app.filters import (
    normalize_text,
    make_hash,
    extract_links_from_text,
    extract_features,
)
from app.models import Message, MessageStatus
from app.scoring import calculate_score, is_relevant
from app.profile import profile

logger = logging.getLogger(__name__)

# Очередь для передачи релевантных сообщений в notifier.py
notification_queue: asyncio.Queue = asyncio.Queue()


async def process_message(msg_data: Dict[str, Any]) -> Optional[int]:
    """
    Обрабатывает одно сообщение, полученное от HTTP-парсера.
    Принимает словарь с ключами: id, text, links, channel_username.
    Возвращает ID сохранённого сообщения или None, если сообщение пропущено.
    """
    try:
        # 1. Извлекаем данные из словаря
        raw_text = msg_data.get("text", "")
        channel_username = msg_data.get("channel_username", "unknown")
        msg_id = msg_data.get("id", 0)
        raw_links = msg_data.get("links", [])

        # 2. Нормализация текста
        normalized = normalize_text(raw_text)
        if not normalized:
            logger.debug(f"Пустое сообщение из {channel_username}, пропуск.")
            return None

        # 3. Хэш и дедупликация
        msg_hash = make_hash(normalized)
        if await is_duplicate(msg_hash):
            logger.debug(f"Дубликат пропущен: {msg_hash[:8]}...")
            return None

        # 4. Извлечение ссылок и признаков
        # Берем ссылки из текста через regex
        text_links = extract_links_from_text(normalized)
        # Ссылки из парсера (теги <a>) добавляем к найденным
        all_links = list(dict.fromkeys(text_links + raw_links))

        features = extract_features(normalized)

        # 5. Скоринг
        score = calculate_score(normalized, features, profile.data)

        # 6. Сохраняем в БД (все сообщения, не только релевантные)
        msg = Message(
            source_tg_id=channel_username,  # Теперь тут строка (username)
            tg_message_id=msg_id,           # ID поста из веб-версии
            text=normalized,
            links=json.dumps(all_links, ensure_ascii=False),
            features=json.dumps(features, ensure_ascii=False),
            score=score,
            hash=msg_hash,
            status=MessageStatus.NEW,
        )
        saved_id = await save_message(msg)

        # 7. Если релевантно — ставим в очередь на уведомление
        if is_relevant(score):
            logger.info(
                f"🔥 Релевантное сообщение (score={score}) из «{channel_username}», id={saved_id}"
            )
            await notification_queue.put(saved_id)
        else:
            logger.debug(f"Сообщение отклонено (score={score}), id={saved_id}")

        return saved_id

    except Exception as e:
        logger.exception(f"Ошибка в pipeline.process_message: {e}")
        return None