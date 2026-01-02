from pathlib import Path
import yaml

def load_settings(path: str = "prbot/config.yaml") -> dict:
    p = Path(path).resolve()
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_loaded_from"] = str(p)
    return cfg

def save_settings(cfg: dict, path: str = "prbot/config.yaml") -> None:
    p = Path(path).resolve()
    # remove debug field if present
    cfg.pop("_loaded_from", None)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
