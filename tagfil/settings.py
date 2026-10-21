"""
settings.py - Persistencia simple de preferencias de TagFil.

- Lectura tolerante: un settings.json dañado o con otro tipo de dato se ignora.
- Escritura atómica (archivo temporal + os.replace): un corte a mitad no lo trunca.
- Antes de escribir se relee el disco, así dos procesos (la app y el menú
  contextual) no se pisan los cambios del otro.
- get_settings() reutiliza la instancia mientras el archivo no cambie, para que
  operaciones en bloque (importar miles de archivos) no lo relean cada vez.
"""
import json
import os
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

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        # Releer: otro proceso pudo haber cambiado otras claves desde que se cargó
        # (cada set() se guarda al instante, así que el disco siempre manda)
        self.data = {**DEFAULTS, **self._load()}
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)


_cache: tuple[Path, int, Settings] | None = None


def _mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return -1


def get_settings() -> Settings:
    global _cache
    path = APP_DIR / "settings.json"
    stamp = _mtime_ns(path)
    if _cache is None or _cache[0] != path or _cache[1] != stamp:
        _cache = (path, stamp, Settings(path))
    return _cache[2]
