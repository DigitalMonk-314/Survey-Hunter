import asyncio
import logging

from telethon import TelegramClient, events
from telethon.errors import RPCError, FloodWaitError

from app.config import settings
from app.pipeline import process_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

client = TelegramClient(
    settings.tg_session_name,
    settings.tg_api_id,
    settings.tg_api_hash,
)


async def run_parser():
    """Запускает клиент Telethon и слушает каналы."""
    logger.info("Запуск парсера Telegram...")

    try:
        await client.start()
    except FloodWaitError as e:
        logger.warning(f"FloodWait: ждём {e.seconds} секунд...")
        await asyncio.sleep(e.seconds)
        await client.start()
    except RPCError as e:
        logger.error(f"Ошибка авторизации Telethon: {e}")
        return

    @client.on(events.NewMessage(chats=settings.channels))
    async def handler(event):
        chat_title = getattr(event.chat, "title", str(event.chat_id))
        await process_message(event.message, chat_title)

    logger.info(f"Парсер слушает {len(settings.channels)} каналов.")
    logger.info("Ожидание новых сообщений (Ctrl+C для выхода)...")

    await client.run_until_disconnected()
    