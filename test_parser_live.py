import asyncio
import logging
from app.config import settings
from app.parser import fetch_channel_html, parse_html, HEADERS
import httpx

logging.basicConfig(level=logging.INFO)

async def main():
    if not settings.channels:
        print("Список CHANNELS пуст. Добавь каналы в .env")
        return
        
    test_channel = settings.channels[0]
    print(f"Тестируем канал: {test_channel}")
    
    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
        # 1. Скачиваем HTML
        html = await fetch_channel_html(client, test_channel)
        
        if not html:
            print("Не удалось скачать HTML. Возможно, канал закрыт или ошибка сети.")
            return
            
        print(f"HTML скачан, длина: {len(html)} символов.")
        
        # 2. Парсим
        messages = parse_html(html, test_channel)
        print(f"Найдено сообщений: {len(messages)}")
        
        # 3. Показываем последнее (самое свежее) сообщение
        if messages:
            last_msg = messages[-1]
            print("\n--- Тестовое сообщение ---")
            print(f"ID: {last_msg['id']}")
            print(f"Канал: {last_msg['channel_username']}")
            print(f"Ссылки: {last_msg['links']}")
            print(f"Текст (первые 200 символов):\n{last_msg['text'][:200]}...")
        else:
            print("Сообщений не найдено. Возможно, изменилась верстка Telegram.")

if __name__ == "__main__":
    asyncio.run(main())
