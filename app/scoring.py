import yaml
import re
from pathlib import Path
from typing import Dict, Any, List

from app.config import settings

KEYWORDS_PATH = Path("keywords.yaml")

def load_keywords() -> Dict[str, List[str]]:
    """Загружает keywords.yaml (чипсы, кошки и т.д.)."""
    if not KEYWORDS_PATH.exists():
        return {"interests": [], "stop_topics": []}
    with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"interests": [], "stop_topics": []}

KEYWORDS = load_keywords()

def calculate_score(text: str, features: Dict[str, Any], profile_data: Dict[str, Any]) -> int:
    """Считает релевантность опроса по всем правилам."""
    score = 0
    lower_text = text.lower()
    
    # --- 1. Базовые признаки ---
    if features.get("paid"):
        score += 30  # Оплата - всегда плюс
        
    # Если это фокус-группа или интервью - это дорогой и качественный опрос
    focus_group_keywords = ["фокус-группа", "фокус группа", "глубинное интервью", "интервью"]
    if any(word in lower_text for word in focus_group_keywords):
        score += 20

    # --- 2. Проверка города (из profile.yaml) ---
    profile_city = profile_data.get("personal", {}).get("city", "").lower()
    found_cities = features.get("cities", [])
    
    if found_cities:
        if profile_city in found_cities or "вся россия" in found_cities or "онлайн" in found_cities:
            score += 40  # Город совпал или онлайн
        else:
            score -= 50  # Город не совпал
    # Если город не найден (пустой список) - ничего не меняем (неизвестность)

    # --- 3. Интересы и Стоп-слова (объединяем оба YAML) ---
    # Берем интересы из profile.yaml (IT, Финансы)
    profile_interests = profile_data.get("interests", [])
    # Берем интересы из keywords.yaml (Чипсы, Кошки)
    keyword_interests = KEYWORDS.get("interests", [])
    
    # Ищем совпадения по всем интересам
    all_interests = profile_interests + keyword_interests
    matched_interests = [word for word in all_interests if word.lower() in lower_text]
    score += 20 * len(matched_interests)  # +20 за каждое совпадение

    # Берем стоп-слова из profile.yaml (Медицина, Дети)
    profile_dislikes = profile_data.get("dislikes", [])
    # Берем стоп-слова из keywords.yaml (Предприниматели)
    keyword_stops = KEYWORDS.get("stop_topics", [])
    
    all_stops = profile_dislikes + keyword_stops
    matched_stops = []
    for word in all_stops:
        # Ищем слово как отдельное слово (с границами \b), чтобы не штрафовать за "чипсы" из-за "ип"
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        if re.search(pattern, lower_text):
            matched_stops.append(word)
    
    if matched_stops:
        score -= 100  # Жесткий штраф за нежелательную тему
    

    

    return score

def is_relevant(score: int) -> bool:
    return score >= settings.score_threshold



