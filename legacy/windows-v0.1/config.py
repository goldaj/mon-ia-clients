
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from PySide6.QtCore import QStandardPaths

APP_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DIR / "config.json"

@dataclass
class AppConfig:
    ssh_host: str = ""
    ssh_user: str = "ubuntu"
    ssh_key: str = ""
    local_llama_port: int = 18080
    remote_llama_port: int = 8080
    model_name: str = "lfm-thinking"
    openclaw_agent: str = "main"
    agent_timeout_seconds: int = 900

def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg = AppConfig()
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg
    except Exception:
        return AppConfig()

def save_config(cfg: AppConfig) -> None:
    CONFIG_PATH.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
