
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

class SshError(RuntimeError):
    pass

def find_ssh():
    ssh = shutil.which("ssh")
    if not ssh:
        raise SshError(
            "ssh.exe introuvable. Active 'Client OpenSSH' dans les fonctionnalités Windows."
        )
    return ssh

def base_ssh_args(cfg):
    args = [find_ssh()]
    args += [
        "-o", "BatchMode=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-o", "ConnectTimeout=10",
    ]
    if cfg.ssh_key:
        args += ["-i", str(Path(cfg.ssh_key))]
    args.append(f"{cfg.ssh_user}@{cfg.ssh_host}")
    return args

class SshTunnel:
    def __init__(self, cfg):
        self.cfg = cfg
        self.proc = None

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        if self.is_running():
            return
        if not self.cfg.ssh_host.strip():
            raise SshError("Le serveur SSH n'est pas configuré.")

        ssh = find_ssh()
        args = [ssh]
        args += [
            "-N",
            "-T",
            "-o", "BatchMode=yes",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "ConnectTimeout=10",
            "-L",
            f"{self.cfg.local_llama_port}:127.0.0.1:{self.cfg.remote_llama_port}",
        ]
        if self.cfg.ssh_key:
            args += ["-i", str(Path(self.cfg.ssh_key))]
        args.append(f"{self.cfg.ssh_user}@{self.cfg.ssh_host}")

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        time.sleep(0.7)
        if self.proc.poll() is not None:
            err = self.proc.stderr.read().strip() if self.proc.stderr else ""
            raise SshError(err or "Le tunnel SSH n'a pas pu démarrer.")

    def stop(self):
        if self.is_running():
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

def run_openclaw_agent(cfg, message, session_key):
    """
    Exécute OpenClaw sur le VPS via SSH et récupère sa sortie JSON.
    Le message est encodé en base64 pour éviter les problèmes de quoting shell.
    """
    payload = base64.b64encode(message.encode("utf-8")).decode("ascii")
    safe_session = "".join(ch for ch in session_key if ch.isalnum() or ch in "-_")[:80]
    safe_agent = "".join(ch for ch in cfg.openclaw_agent if ch.isalnum() or ch in "-_")[:40] or "main"

    remote = (
        f'MSG="$(printf %s \'{payload}\' | base64 -d)"; '
        f'openclaw agent --agent {safe_agent} '
        f'--session-key {safe_session} '
        f'--message "$MSG" '
        f'--timeout {int(cfg.agent_timeout_seconds)} '
        f'--json'
    )

    args = base_ssh_args(cfg) + [remote]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=cfg.agent_timeout_seconds + 30,
        creationflags=creationflags,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if not stdout:
        raise SshError(stderr or f"OpenClaw n'a renvoyé aucune donnée (code {completed.returncode}).")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        # Dernier filet : si une version du CLI ajoute du bruit autour du JSON.
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(stdout[start:end+1])
        else:
            raise SshError(f"Sortie OpenClaw non JSON :\n{stdout}\n{stderr}")

    if completed.returncode != 0 or data.get("ok") is False:
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or str(err)
        else:
            msg = str(err or stderr or "Erreur OpenClaw")
        raise SshError(msg)

    return data

def extract_agent_text(data):
    # Format gateway courant
    result = data.get("result", data)

    payloads = result.get("payloads") if isinstance(result, dict) else None
    if isinstance(payloads, list):
        texts = []
        for p in payloads:
            if isinstance(p, dict) and p.get("text"):
                texts.append(str(p["text"]))
        if texts:
            return "\n".join(texts)

    # Format agent exec / autres enveloppes
    if isinstance(result, dict) and result.get("final"):
        return str(result["final"])
    if data.get("final"):
        return str(data["final"])

    # Recherche récursive prudente
    def walk(obj):
        if isinstance(obj, dict):
            for key in ("text", "content", "reply", "message"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val
            for val in obj.values():
                found = walk(val)
                if found:
                    return found
        elif isinstance(obj, list):
            for val in obj:
                found = walk(val)
                if found:
                    return found
        return None

    return walk(data) or "(OpenClaw a terminé sans texte exploitable.)"
