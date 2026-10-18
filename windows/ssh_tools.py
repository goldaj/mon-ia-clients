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
    args = [
        find_ssh(),
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

        args = [
            find_ssh(),
            "-N", "-T",
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

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
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


def extract_agent_text(data):
    result = data.get("result", data)
    payloads = result.get("payloads") if isinstance(result, dict) else None
    if isinstance(payloads, list):
        texts = [
            str(p["text"])
            for p in payloads
            if isinstance(p, dict) and p.get("text")
        ]
        if texts:
            return "\n".join(texts)

    if isinstance(result, dict) and result.get("final"):
        return str(result["final"])
    if isinstance(data, dict) and data.get("final"):
        return str(data["final"])

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


def fetch_server_status(cfg):
    probe = r'''import json, os, socket

def tcp(port):
    s = socket.socket()
    s.settimeout(0.4)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()

m = {}
with open("/proc/meminfo", "r", encoding="utf-8") as f:
    for line in f:
        k, v = line.split(":", 1)
        parts = v.strip().split()
        if parts and parts[0].isdigit():
            m[k] = int(parts[0]) * 1024

swap_total = m.get("SwapTotal", 0)
swap_free = m.get("SwapFree", 0)
mem_total = m.get("MemTotal", 0)
mem_avail = m.get("MemAvailable", 0)
uptime = float(open("/proc/uptime").read().split()[0])
load1 = os.getloadavg()[0]
cpus = os.cpu_count() or 1
print(json.dumps({
    "llama": tcp(8080),
    "openclaw": tcp(18789),
    "mobile": tcp(8090),
    "mem_total": mem_total,
    "mem_used": max(0, mem_total - mem_avail),
    "swap_total": swap_total,
    "swap_used": max(0, swap_total - swap_free),
    "load1": load1,
    "cpus": cpus,
    "uptime": uptime,
}))'''
    payload = base64.b64encode(probe.encode("utf-8")).decode("ascii")
    remote = f'python3 -c "$(printf %s \'{payload}\' | base64 -d)"'
    args = base_ssh_args(cfg) + [remote]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        creationflags=creationflags,
    )
    if completed.returncode != 0:
        raise SshError(completed.stderr.strip() or "Impossible de lire l'état du VPS.")
    try:
        return json.loads(completed.stdout.strip())
    except Exception as exc:
        raise SshError("Réponse d'état VPS invalide.") from exc
