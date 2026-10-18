import json
import os
import subprocess
import time

import httpx
from PySide6.QtCore import QThread, Signal

from ssh_tools import base_ssh_args, extract_agent_text, fetch_server_status


class FastChatThread(QThread):
    token = Signal(str)
    done = Signal(float, bool, int)
    failed = Signal(str)

    def __init__(self, cfg, messages, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.messages = messages
        self.output_chars = 0

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
        interrupted = False
        try:
            with httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
                with client.stream("POST", url, json=body) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if self.isInterruptionRequested():
                            interrupted = True
                            break
                        if not line or not line.startswith("data:"):
                            continue
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
                        text = ((choices[0].get("delta") or {}).get("content") or "")
                        if text:
                            self.output_chars += len(text)
                            self.token.emit(text)
            self.done.emit(time.perf_counter() - start, interrupted, self.output_chars)
        except Exception as exc:
            if self.isInterruptionRequested():
                self.done.emit(time.perf_counter() - start, True, self.output_chars)
            else:
                self.failed.emit(str(exc))


class AgentChatThread(QThread):
    done = Signal(str, float, bool)
    failed = Signal(str)

    def __init__(self, cfg, message, session_key, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.message = message
        self.session_key = session_key
        self.proc = None

    def _build_remote(self):
        import base64

        payload = base64.b64encode(self.message.encode("utf-8")).decode("ascii")
        safe_session = "".join(
            ch for ch in self.session_key if ch.isalnum() or ch in "-_"
        )[:80]
        safe_agent = "".join(
            ch for ch in self.cfg.openclaw_agent if ch.isalnum() or ch in "-_"
        )[:40] or "main"
        return (
            f'MSG="$(printf %s \'{payload}\' | base64 -d)"; '
            f'OPENCLAW="$HOME/.npm-global/bin/openclaw"; '
            f'if [ ! -x "$OPENCLAW" ]; then echo \'OpenClaw introuvable\' >&2; exit 127; fi; '
            f'"$OPENCLAW" agent --agent {safe_agent} --session-key {safe_session} '
            f'--message "$MSG" --timeout {int(self.cfg.agent_timeout_seconds)} --json'
        )

    def run(self):
        start = time.perf_counter()
        try:
            args = base_ssh_args(self.cfg) + [self._build_remote()]
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            while self.proc.poll() is None:
                if self.isInterruptionRequested():
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.proc.kill()
                    self.done.emit("", time.perf_counter() - start, True)
                    return
                time.sleep(0.2)

            stdout, stderr = self.proc.communicate()
            stdout = (stdout or "").strip()
            stderr = (stderr or "").strip()
            if not stdout:
                raise RuntimeError(
                    stderr or f"OpenClaw n'a renvoyé aucune donnée (code {self.proc.returncode})."
                )

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                a, b = stdout.find("{"), stdout.rfind("}")
                if a >= 0 and b > a:
                    data = json.loads(stdout[a : b + 1])
                else:
                    raise RuntimeError(f"Sortie OpenClaw non JSON :\n{stdout}\n{stderr}")

            if self.proc.returncode != 0 or data.get("ok") is False:
                err = data.get("error")
                msg = (
                    err.get("message")
                    if isinstance(err, dict)
                    else str(err or stderr or "Erreur OpenClaw")
                )
                raise RuntimeError(msg)

            self.done.emit(
                extract_agent_text(data), time.perf_counter() - start, False
            )
        except Exception as exc:
            if self.isInterruptionRequested():
                self.done.emit("", time.perf_counter() - start, True)
            else:
                self.failed.emit(str(exc))
        finally:
            self.proc = None


class StatusThread(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg

    def run(self):
        try:
            self.done.emit(fetch_server_status(self.cfg))
        except Exception as exc:
            self.failed.emit(str(exc))
