"""
settings.py - Persistencia simple de preferencias de TagFil.
"""
import json
from pathlib import Path

from config import APP_DIR


DEFAULTS = {
    "sync_explorer_metadata": True,
    "encrypt_backup": False,
    "audit_retention": 5000,
}


class Settings:
    def __init__(self, path: Path):
        self.path = path
        self.data = {**DEFAULTS, **self._load()}

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def get_settings() -> Settings:
    return Settings(APP_DIR / "settings.json")
