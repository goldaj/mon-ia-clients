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
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
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
    now = datetime.now().isoformat(timespec="seconds")
    conv = {
        "id": str(uuid.uuid4()),
        "title": "Nouvelle conversation",
        "mode": mode,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    conversations = _load_all()
    conversations.insert(0, conv)
    _save_all(conversations)
    return conv


def save_conversation(conv):
    conv["updated_at"] = datetime.now().isoformat(timespec="seconds")
    conversations = _load_all()
    for i, existing in enumerate(conversations):
        if existing.get("id") == conv.get("id"):
            conversations[i] = conv
            break
    else:
        conversations.insert(0, conv)
    conversations.sort(
        key=lambda c: c.get("updated_at", c.get("created_at", "")), reverse=True
    )
    _save_all(conversations)


def rename_conversation(conv_id, title):
    title = (title or "").strip()[:80]
    if not title:
        return
    conversations = _load_all()
    for conv in conversations:
        if conv.get("id") == conv_id:
            conv["title"] = title
            conv["updated_at"] = datetime.now().isoformat(timespec="seconds")
            break
    _save_all(conversations)


def delete_conversation(conv_id):
    _save_all([c for c in _load_all() if c.get("id") != conv_id])
