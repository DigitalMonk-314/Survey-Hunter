import asyncio
import logging
import signal
import sys

from app.config import settings
from app.db import init_db
from app.parser import client, run_parser
from app.notifier import dp, bot, notification_worker

# Настраиваем логирование в файл и консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("survey_hunter.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Флаг для корректной остановки
shutdown_event = asyncio.Event()

def handle_sigint(sig, frame):
    logger.info("Получен сигнал завершения (Ctrl+C). Останавливаем...")
    shutdown_event.set()

async def main():
    logger.info("Запуск Survey Hunter...")
    
    # 1. Инициализируем БД
    await init_db()
    logger.info("БД инициализирована.")

    # 2. Запускаем бота (aiogram polling) как фоновую задачу
    logger.info("Запуск Telegram-бота (aiogram)...")
    bot_task = asyncio.create_task(dp.start_polling(bot))

    # 3. Запускаем воркер очереди (отправка уведомлений)
    logger.info("Запуск воркера уведомлений...")
    worker_task = asyncio.create_task(notification_worker())

    # 4. Запускаем парсер (Telethon) как фоновую задачу
    logger.info("Запуск парсера (Telethon)...")
    parser_task = asyncio.create_task(run_parser())

    # 5. Ждем сигнала завершения
    await shutdown_event.wait()
    logger.info("Начинаем корректное завершение...")

    # --- Корректное завершение ---
    
    # Отменяем задачи
    bot_task.cancel()
    worker_task.cancel()
    parser_task.cancel()

    # Закрываем клиенты
    await bot.session.close()
    if client.is_connected():
        await client.disconnect()

    logger.info("Survey Hunter остановлен.")
    sys.exit(0)

if __name__ == "__main__":
    # Подписываемся на Ctrl+C
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
