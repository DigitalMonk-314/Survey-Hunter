import yaml
from pathlib import Path
from typing import Dict, Any, List

class Profile:
    def __init__(self, profile_path: str = "profile.yaml"):
        self.path = Path(profile_path)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Загружает профиль из YAML файла."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"Файл профиля не найден: {self.path.absolute()}"
            )
        
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)
            
        self._validate()

    def _validate(self) -> None:
        """Проверяет наличие обязательных полей."""
        if not self.data or "personal" not in self.data:
            raise ValueError(
                "Некорректный формат profile.yaml: отсутствует раздел 'personal'"
            )

    def get_personal(self) -> Dict[str, Any]:
        """Возвращает личные данные (возраст, город и т.д.)."""
        return self.data.get("personal", {})

    def get_interests(self) -> List[str]:
        """Возвращает список интересов."""
        return self.data.get("interests", [])

    def get_dislikes(self) -> List[str]:
        """Возвращает список нежелательных тем."""
        return self.data.get("dislikes", [])

# Глобальный экземпляр профиля
profile = Profile()