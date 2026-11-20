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
    score = 0
    lower_text = text.lower()

    # 1. Базовые признаки
    if features.get("paid"):
        score += 30

    focus_group_keywords = ["фокус-группа", "фокус группа", "глубинное интервью", "интервью"]
    if any(word in lower_text for word in focus_group_keywords):
        score += 20

    # 2. Город
    profile_city = profile_data.get("personal", {}).get("city", "").lower()
    found_cities = features.get("cities", [])
    if found_cities:
        if profile_city in found_cities or "вся россия" in found_cities or "онлайн" in found_cities:
            score += 40
        else:
            score -= 50

    # 3. Возраст
    profile_age = profile_data.get("personal", {}).get("age")
    age_min = features.get("age_min")
    age_max = features.get("age_max")
    if profile_age is not None and (age_min is not None or age_max is not None):
        in_range = True
        if age_min is not None and profile_age < age_min:
            in_range = False
        if age_max is not None and profile_age > age_max:
            in_range = False
        if in_range:
            score += 30
        else:
            score -= 50

    # 4. Пол
    profile_gender = profile_data.get("personal", {}).get("gender")
    ad_gender = features.get("gender")
    if profile_gender and ad_gender:
        if profile_gender == ad_gender:
            score += 20
        else:
            score -= 50

    # 5. Интересы
    profile_interests = profile_data.get("interests", [])
    keyword_interests = KEYWORDS.get("interests", [])
    all_interests = profile_interests + keyword_interests

    matched = set()
    for word in all_interests:
        if word.lower() in lower_text:
            matched.add(word.lower())
    score += 20 * len(matched)

    # 6. Стоп-слова
    profile_dislikes = profile_data.get("dislikes", [])
    keyword_stops = KEYWORDS.get("stop_topics", [])
    all_stops = profile_dislikes + keyword_stops

    for word in all_stops:
        w = word.lower()
        if len(w) <= 3:
            if re.search(r'\b' + re.escape(w) + r'\b', lower_text):
                score -= 100
                break
        else:
            if w in lower_text:
                score -= 100
                break

    return score


def is_relevant(score: int) -> bool:
    return score >= settings.score_threshold