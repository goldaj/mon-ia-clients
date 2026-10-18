
import json
import time
import httpx
from PySide6.QtCore import QThread, Signal
from ssh_tools import run_openclaw_agent, extract_agent_text

class FastChatThread(QThread):
    token = Signal(str)
    done = Signal(float)
    failed = Signal(str)

    def __init__(self, cfg, messages, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.messages = messages

    def run(self):
        start = time.perf_counter()
        url = f"http://127.0.0.1:{self.cfg.local_llama_port}/v1/chat/completions"
        body = {
            "model": self.cfg.model_name,
            "messages": self.messages,
            "temperature": 0.05,
            "max_tokens": 1024,
            "stream": True,
        }
        try:
            with httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
                with client.stream("POST", url, json=body) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            payload = line[5:].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                data = json.loads(payload)
                            except json.JSONDecodeError:
                                continue
                            choices = data.get("choices") or []
                            if not choices:
                                continue
                            choice = choices[0]
                            delta = choice.get("delta") or {}
                            text = delta.get("content")
                            if text:
                                self.token.emit(text)
            self.done.emit(time.perf_counter() - start)
        except Exception as exc:
            self.failed.emit(str(exc))

class AgentChatThread(QThread):
    done = Signal(str, float)
    failed = Signal(str)

    def __init__(self, cfg, message, session_key, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.message = message
        self.session_key = session_key

    def run(self):
        start = time.perf_counter()
        try:
            data = run_openclaw_agent(self.cfg, self.message, self.session_key)
            text = extract_agent_text(data)
            self.done.emit(text, time.perf_counter() - start)
        except Exception as exc:
            self.failed.emit(str(exc))
