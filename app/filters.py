import re
import hashlib
from typing import List, Dict, Any, Optional

# --- 1. Нормализация и хеширование ---

def normalize_text(text: Optional[str], caption: Optional[str] = None) -> str:
    """Склеивает текст и подпись, убирает лишние пробелы."""
    parts = []
    if text:
        parts.append(text)
    if caption:
        parts.append(caption)
    
    full_text = " ".join(parts)
    # Убираем множественные пробелы и переносы строк
    return re.sub(r'\s+', ' ', full_text).strip()

def make_hash(text: str) -> str:
    """Создает SHA-256 хеш из нормализованного текста для дедупликации."""
    # Приводим к нижнему регистру, чтобы регистр не влиял на дубли
    return hashlib.sha256(text.lower().encode('utf-8')).hexdigest()

# --- 2. Извлечение ссылок ---

def extract_links_from_text(text: str) -> List[str]:
    """Ищет URL в тексте сообщения."""
    # Простой regex для поиска http/https ссылок
    url_pattern = r'https?://[^\s]+'
    return re.findall(url_pattern, text)

def extract_links_from_buttons(message) -> List[str]:
    """Достает URL из inline-кнопок (reply_markup) сообщения Telethon."""
    links = []
    rm = getattr(message, "reply_markup", None)
    if rm and hasattr(rm, "rows"):
        for row in rm.rows:
            for btn in row.buttons:
                url = getattr(btn, "url", None)
                if url:
                    links.append(url)
    return links

# --- 3. Извлечение признаков (Feature Extraction) ---

def extract_features(text: str) -> Dict[str, Any]:
    """Пытается вытащить город, возраст, пол, оплату и время из текста."""
    features = {
        "cities": [],
        "age_min": None,
        "age_max": None,
        "gender": None,
        "paid": False,
        "minutes": None,
    }

    lower_text = text.lower()

    # 1. Оплата
    paid_keywords = ["оплата", "вознаграждение", "руб", "перевод на карту", "сертификат", "деньги"]
    if any(word in lower_text for word in paid_keywords):
        features["paid"] = True

    # 2. Длительность
    minutes_match = re.search(r'(\d+)\s*(минут|мин)', lower_text)
    if minutes_match:
        features["minutes"] = int(minutes_match.group(1))

    # 3. Возраст
    age_range = re.search(r'(?:от\s*)?(\d{2})\s*[-–—]\s*(\d{2})', lower_text)
    if age_range:
        features["age_min"] = int(age_range.group(1))
        features["age_max"] = int(age_range.group(2))
    else:
        age_from_to = re.search(r'от\s*(\d{2})\s*до\s*(\d{2})', lower_text)
        if age_from_to:
            features["age_min"] = int(age_from_to.group(1))
            features["age_max"] = int(age_from_to.group(2))
        else:
            age_plus = re.search(r'(?:от\s*)?(\d{2})\s*\+', lower_text)
            if age_plus:
                features["age_min"] = int(age_plus.group(1))
            else:
                age_to = re.search(r'до\s*(\d{2})', lower_text)
                if age_to:
                    features["age_max"] = int(age_to.group(1))

    # 4. Пол
    if re.search(r'\bмужчин|только\s+мужчин', lower_text):
        features["gender"] = "male"
    if re.search(r'\bженщин|только\s+женщин', lower_text):
        features["gender"] = "female"

    # 5. Города
    known_cities = ["москва", "санкт-петербург", "вся россия", "онлайн"]
    for city in known_cities:
        if city in lower_text:
            features["cities"].append(city)

    return features