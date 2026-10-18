
import json
import uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QStandardPaths

APP_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
APP_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_PATH = APP_DIR / "history.json"

def _load_all():
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_all(conversations):
    HISTORY_PATH.write_text(
        json.dumps(conversations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def list_conversations():
    return _load_all()

def new_conversation(mode="fast"):
    conv = {
        "id": str(uuid.uuid4()),
        "title": "Nouvelle conversation",
        "mode": mode,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "messages": [],
    }
    conversations = _load_all()
    conversations.insert(0, conv)
    _save_all(conversations)
    return conv

def save_conversation(conv):
    conversations = _load_all()
    found = False
    for i, existing in enumerate(conversations):
        if existing.get("id") == conv.get("id"):
            conversations[i] = conv
            found = True
            break
    if not found:
        conversations.insert(0, conv)
    _save_all(conversations)

def delete_conversation(conv_id):
    conversations = [c for c in _load_all() if c.get("id") != conv_id]
    _save_all(conversations)
