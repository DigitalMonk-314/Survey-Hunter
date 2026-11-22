import asyncio
import logging
import random
from typing import List, Dict, Any

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.pipeline import process_message

logger = logging.getLogger(__name__)

# Создаем базовые заголовки, чтобы Telegram не блокировал нас как бота
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def fetch_channel_html(client: httpx.AsyncClient, username: str) -> str | None:
    """
    Скачивает HTML-страницу публичного канала (веб-превью).
    Возвращает HTML-текст или None в случае ошибки.
    """
    url = f"https://t.me/s/{username}"
    try:
        response = await client.get(url)
        response.raise_for_status() # Проверяем на ошибки 404, 500 и т.д.
        return response.text
    except httpx.RequestError as e:
        logger.error(f"Сетевая ошибка при запросе {url}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP {e.response.status_code} при запросе {url}")
        return None

def parse_html(html: str, username: str) -> List[Dict[str, Any]]:
    """
    Принимает HTML-код и имя канала.
    Возвращает список словарей с данными сообщений.
    """
    soup = BeautifulSoup(html, "html.parser")
    messages = []

    # Находим все блоки сообщений на странице
    message_blocks = soup.find_all("div", class_="tgme_widget_message_wrap")
    
    for block in message_blocks:
        # 1. Ищем сам блок с данными
        msg_div = block.find("div", class_="tgme_widget_message")
        if not msg_div:
            continue
            
        # 2. Извлекаем ID сообщения из атрибута data-post="channel/123"
        data_post = msg_div.get("data-post", "")
        if not data_post:
            continue
        
        try:
            msg_id = int(data_post.split("/")[-1])
        except ValueError:
            continue

        # 3. Извлекаем текст сообщения
        text_div = block.find("div", class_="tgme_widget_message_text")
        text = text_div.get_text(separator="\n") if text_div else ""

        # 4. Извлекаем ссылки из текста (все теги <a> внутри блока текста)
        links = []
        if text_div:
            for a_tag in text_div.find_all("a", href=True):
                links.append(a_tag["href"])

        # Формируем структуру, которую ждет pipeline.py
        messages.append({
            "id": msg_id,
            "text": text,
            "links": links,
            "channel_username": username
        })

    return messages

async def run_parser():
    """
    Главный цикл парсера.
    Бесконечно опрашивает каналы с заданным интервалом.
    """
    logger.info("Запуск HTTP-парсера Telegram...")
    
    # Создаем асинхронный клиент на все время работы
    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
        while True:
            try:
                for username in settings.channels:
                    logger.info(f"Проверка канала: {username}")
                    
                    # 1. Скачиваем HTML
                    html = await fetch_channel_html(client, username)
                    if not html:
                        continue
                    
                    # 2. Парсим сообщения
                    messages = parse_html(html, username)
                    logger.debug(f"Найдено {len(messages)} сообщений в {username}")
                    
                    # 3. Передаем в пайплайн
                    for msg_data in messages:
                        await process_message(msg_data)
                    
                    # Пауза между запросами к разным каналам, чтобы не забанили
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    
            except asyncio.CancelledError:
                logger.info("Парсер остановлен.")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка в цикле парсера: {e}")
                
            # Ждем перед следующим проходом по каналам
            logger.info(f"Ожидание {settings.poll_interval_seconds} секунд перед следующим опросом...")
            await asyncio.sleep(settings.poll_interval_seconds)    