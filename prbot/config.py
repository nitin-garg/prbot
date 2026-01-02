from __future__ import annotations
import yaml
from pathlib import Path

_CONFIG = None

def load_config(path: str | None = None) -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    config_path = Path(path or "prbot/config.yaml")
    print(config_path)
    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f)
    
    return _CONFIG
