import sys
import time

import markdown
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from config import load_config, save_config
from ssh_tools import SshTunnel
from storage import (
    delete_conversation,
    list_conversations,
    new_conversation,
    rename_conversation,
    save_conversation,
)
from workers import AgentChatThread, FastChatThread, StatusThread


APP_STYLE = """
QMainWindow,QWidget{background:#101217;color:#e8ebf1;font-size:14px}
QToolBar{background:#171a20;border:none;spacing:8px;padding:7px}
QPushButton{background:#232936;border:1px solid #343c4d;border-radius:9px;padding:8px 12px}
QPushButton:hover{background:#2b3342}
QPushButton:disabled{color:#747c8a;background:#1a1d24}
QComboBox,QLineEdit,QSpinBox,QTextEdit{background:#171a20;border:1px solid #343c4d;border-radius:9px;padding:8px}
QTextBrowser{background:#0c0e12;border:none;padding:14px}
QListWidget{background:#14171d;border:none;padding:5px}
QListWidget::item{padding:10px;margin:2px;border-radius:8px}
QListWidget::item:selected{background:#293247}
#muted{color:#98a2b3}
#chipGood{background:#183522;color:#a8e6b8;border-radius:8px;padding:5px 8px}
#chipBad{background:#3a1f24;color:#ffb5bd;border-radius:8px;padding:5px 8px}
"""

CHAT_CSS = """
<style>
body{background:#0c0e12;color:#e8ebf1;font-family:'Segoe UI';font-size:14px}
.msg{margin:12px 5px;padding:13px 15px;border-radius:13px}
.user{background:#253149;margin-left:80px}
.assistant{background:#171b22;margin-right:80px}
pre{background:#090b0f;padding:11px;border-radius:9px;white-space:pre-wrap}
code{font-family:Consolas,monospace}
a{color:#8db8ff}
</style>
"""


def visible_model_text(raw):
    if not raw:
        return ""
    s = raw
    while True:
        start = s.find("<think>")
        if start == -1:
            break
        end = s.find("</think>", start + 7)
        if end == -1:
            s = s[:start]
            break
        s = s[:start] + s[end + 8 :]
    return s.strip()


def human_bytes(v):
    v = float(v or 0)
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if v < 1024:
            return f"{v:.0f} {unit}"
        v /= 1024
    return f"{v:.1f} Po"


def human_uptime(seconds):
    seconds = int(seconds or 0)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d} j {h} h"
    if h:
        return f"{h} h {m} min"
    return f"{m} min"


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres")
        self.cfg = cfg
        form = QFormLayout(self)

        self.host = QLineEdit(cfg.ssh_host)
        self.user = QLineEdit(cfg.ssh_user)
        self.key = QLineEdit(cfg.ssh_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self.key)
        browse = QPushButton("Parcourir…")
        browse.clicked.connect(self.pick_key)
        key_row.addWidget(browse)

        self.local_port = QSpinBox()
        self.local_port.setRange(1024, 65535)
        self.local_port.setValue(cfg.local_llama_port)
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1, 65535)
        self.remote_port.setValue(cfg.remote_llama_port)
        self.model = QLineEdit(cfg.model_name)
        self.agent = QLineEdit(cfg.openclaw_agent)
        self.timeout = QSpinBox()
        self.timeout.setRange(30, 3600)
        self.timeout.setValue(cfg.agent_timeout_seconds)

        form.addRow("Serveur SSH", self.host)
        form.addRow("Utilisateur", self.user)
        form.addRow("Clé privée (optionnel)", key_row)
        form.addRow("Port local", self.local_port)
        form.addRow("Port llama.cpp", self.remote_port)
        form.addRow("Modèle", self.model)
        form.addRow("Agent OpenClaw", self.agent)
        form.addRow("Timeout Agent (s)", self.timeout)

        row = QHBoxLayout()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Enregistrer")
        ok.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(ok)
        form.addRow(row)

    def pick_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir la clé SSH")
        if path:
            self.key.setText(path)

    def apply(self):
        self.cfg.ssh_host = self.host.text().strip()
        self.cfg.ssh_user = self.user.text().strip() or "ubuntu"
        self.cfg.ssh_key = self.key.text().strip()
        self.cfg.local_llama_port = self.local_port.value()
        self.cfg.remote_llama_port = self.remote_port.value()
        self.cfg.model_name = self.model.text().strip() or "lfm-thinking"
        self.cfg.openclaw_agent = self.agent.text().strip() or "main"
        self.cfg.agent_timeout_seconds = self.timeout.value()
        save_config(self.cfg)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mon IA")
        self.resize(1220, 790)
        self.cfg = load_config()
        self.tunnel = SshTunnel(self.cfg)
        self.current = None
        self.worker = None
        self.status_worker = None
        self.streaming_text = ""
        self.generation_started = None
        self.server_status = {}

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(500)
        self.elapsed_timer.timeout.connect(self.update_elapsed)

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(30000)
        self.status_timer.timeout.connect(self.refresh_server_status)

        self.build_ui()
        self.reload_conversations()
        self.status_timer.start()

        if not self.cfg.ssh_host:
            QTimer.singleShot(250, self.open_settings)
        else:
            QTimer.singleShot(350, self.auto_connect)

    def build_ui(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("Mon IA  "))

        self.mode = QComboBox()
        self.mode.addItem("⚡ Rapide", "fast")
        self.mode.addItem("🛠 Agent", "agent")
        self.mode.currentIndexChanged.connect(self.mode_changed)
        toolbar.addWidget(self.mode)

        toolbar.addSeparator()
        self.ssh_chip = QLabel("SSH ●")
        self.ai_chip = QLabel("IA ●")
        self.agent_chip = QLabel("Agent ●")
        for widget in (self.ssh_chip, self.ai_chip, self.agent_chip):
            widget.setObjectName("chipBad")
            toolbar.addWidget(widget)

        toolbar.addSeparator()
        self.connect_btn = QPushButton("Connexion")
        self.connect_btn.clicked.connect(self.toggle_tunnel)
        toolbar.addWidget(self.connect_btn)

        status_action = QAction("État serveur", self)
        status_action.triggered.connect(self.show_status_dialog)
        toolbar.addAction(status_action)

        settings_action = QAction("Paramètres", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        splitter = QSplitter()
        self.setCentralWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        new_btn = QPushButton("＋ Nouvelle conversation")
        new_btn.clicked.connect(self.create_conversation)
        left_layout.addWidget(new_btn)

        self.conv_list = QListWidget()
        self.conv_list.currentRowChanged.connect(self.select_conversation)
        self.conv_list.itemDoubleClicked.connect(lambda _: self.rename_current())
        left_layout.addWidget(self.conv_list, 1)

        row = QHBoxLayout()
        rename_btn = QPushButton("Renommer")
        rename_btn.clicked.connect(self.rename_current)
        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self.delete_current)
        row.addWidget(rename_btn)
        row.addWidget(delete_btn)
        left_layout.addLayout(row)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        right_layout.addWidget(self.chat, 1)

        self.input = QTextEdit()
        self.input.setPlaceholderText(
            "Écris ton message…  Entrée pour envoyer, Maj+Entrée pour une nouvelle ligne"
        )
        self.input.setMaximumHeight(125)
        self.input.installEventFilter(self)
        right_layout.addWidget(self.input)

        bottom = QHBoxLayout()
        self.info = QLabel("Prêt")
        self.info.setObjectName("muted")
        bottom.addWidget(self.info)
        bottom.addStretch()

        self.stop_btn = QPushButton("■ Arrêter")
        self.stop_btn.setDisabled(True)
        self.stop_btn.clicked.connect(self.stop_generation)
        self.send_btn = QPushButton("Envoyer")
        self.send_btn.clicked.connect(self.send_message)
        bottom.addWidget(self.stop_btn)
        bottom.addWidget(self.send_btn)
        right_layout.addLayout(bottom)

        splitter.addWidget(right)
        splitter.setSizes([285, 935])

    def eventFilter(self, obj, event):
        if (
            obj is self.input
            and event.type() == event.Type.KeyPress
            and event.key() in (Qt.Key_Return, Qt.Key_Enter)
        ):
            if event.modifiers() & Qt.ShiftModifier:
                return super().eventFilter(obj, event)
            self.send_message()
            return True
        return super().eventFilter(obj, event)

    def set_chip(self, label, ok):
        label.setObjectName("chipGood" if ok else "chipBad")
        label.style().unpolish(label)
        label.style().polish(label)

    def auto_connect(self):
        try:
            self.ensure_tunnel()
            self.info.setText("Prêt")
        except Exception:
            self.info.setText("SSH non connecté")
        self.refresh_server_status()

    def refresh_server_status(self):
        if not self.cfg.ssh_host:
            return
        if self.status_worker and self.status_worker.isRunning():
            return
        self.status_worker = StatusThread(self.cfg, self)
        self.status_worker.done.connect(self.status_ready)
        self.status_worker.failed.connect(self.status_failed)
        self.status_worker.start()

    def status_ready(self, data):
        self.server_status = data
        self.set_chip(self.ssh_chip, True)
        self.set_chip(self.ai_chip, bool(data.get("llama")))
        self.set_chip(self.agent_chip, bool(data.get("openclaw")))
        self.status_worker = None

    def status_failed(self, _error):
        self.server_status = {}
        self.set_chip(self.ssh_chip, False)
        self.set_chip(self.ai_chip, False)
        self.set_chip(self.agent_chip, False)
        self.status_worker = None

    def show_status_dialog(self):
        self.refresh_server_status()
        data = self.server_status
        if not data:
            QMessageBox.information(
                self,
                "État serveur",
                "État en cours de récupération ou serveur indisponible.",
            )
            return
        text = (
            f"Serveur : en ligne\n"
            f"IA locale : {'disponible' if data.get('llama') else 'indisponible'}\n"
            f"OpenClaw : {'disponible' if data.get('openclaw') else 'indisponible'}\n"
            f"MobileAI : {'disponible' if data.get('mobile') else 'indisponible'}\n\n"
            f"RAM : {human_bytes(data.get('mem_used'))} / {human_bytes(data.get('mem_total'))}\n"
            f"Swap : {human_bytes(data.get('swap_used'))} / {human_bytes(data.get('swap_total'))}\n"
            f"Charge 1 min : {data.get('load1', 0):.2f} sur {data.get('cpus', 1)} vCPU\n"
            f"Uptime : {human_uptime(data.get('uptime'))}"
        )
        QMessageBox.information(self, "État serveur", text)

    def update_elapsed(self):
        if self.generation_started is None:
            return
        elapsed = time.perf_counter() - self.generation_started
        mode = "Rapide" if self.mode.currentData() == "fast" else "Agent"
        self.info.setText(f"{mode} • {elapsed:.1f} s")

    def stop_generation(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.stop_btn.setDisabled(True)
            self.info.setText("Arrêt demandé…")

    def open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            self.tunnel.stop()
            dlg.apply()
            self.tunnel = SshTunnel(self.cfg)
            self.update_connection_state()
            QTimer.singleShot(100, self.auto_connect)

    def update_connection_state(self):
        ok = self.tunnel.is_running()
        self.connect_btn.setText("Déconnecter" if ok else "Connexion")
        self.set_chip(self.ssh_chip, ok)

    def toggle_tunnel(self):
        try:
            if self.tunnel.is_running():
                self.tunnel.stop()
            else:
                self.tunnel.start()
        except Exception as exc:
            QMessageBox.critical(self, "Connexion SSH", str(exc))
        self.update_connection_state()

    def ensure_tunnel(self):
        if not self.tunnel.is_running():
            self.tunnel.start()
            self.update_connection_state()

    def reload_conversations(self, select_id=None):
        conversations = list_conversations()
        self.conv_list.blockSignals(True)
        self.conv_list.clear()
        selected = 0
        for i, conv in enumerate(conversations):
            prefix = "⚡ " if conv.get("mode") == "fast" else "🛠 "
            self.conv_list.addItem(prefix + conv.get("title", "Conversation"))
            self.conv_list.item(i).setData(Qt.UserRole, conv)
            if select_id and conv.get("id") == select_id:
                selected = i
        self.conv_list.blockSignals(False)

        if conversations:
            self.conv_list.setCurrentRow(selected)
            self.select_conversation(selected)
        else:
            self.create_conversation()

    def create_conversation(self):
        conv = new_conversation(self.mode.currentData() or "fast")
        self.reload_conversations(conv["id"])

    def rename_current(self):
        if not self.current:
            return
        title, ok = QInputDialog.getText(
            self,
            "Renommer",
            "Nom de la conversation :",
            text=self.current.get("title", ""),
        )
        if ok and title.strip():
            rename_conversation(self.current["id"], title)
            self.current["title"] = title.strip()[:80]
            self.reload_conversations(self.current["id"])

    def delete_current(self):
        if not self.current:
            return
        result = QMessageBox.question(
            self,
            "Supprimer",
            f"Supprimer « {self.current.get('title', 'Conversation')} » ?",
        )
        if result != QMessageBox.Yes:
            return
        delete_conversation(self.current["id"])
        self.current = None
        self.reload_conversations()

    def select_conversation(self, row):
        if row < 0:
            return
        item = self.conv_list.item(row)
        if not item:
            return
        self.current = item.data(Qt.UserRole)
        idx = self.mode.findData(self.current.get("mode", "fast"))
        if idx >= 0:
            self.mode.blockSignals(True)
            self.mode.setCurrentIndex(idx)
            self.mode.blockSignals(False)
        self.render_chat()

    def mode_changed(self):
        if self.current:
            self.current["mode"] = self.mode.currentData()
            save_conversation(self.current)
            self.reload_conversations(self.current["id"])

    def render_chat(self, pending_text=None):
        if not self.current:
            self.chat.setHtml(CHAT_CSS)
            return
        blocks = [CHAT_CSS]
        for msg in self.current.get("messages", []):
            cls = "user" if msg.get("role") == "user" else "assistant"
            label = "Vous" if msg.get("role") == "user" else "IA"
            rendered = markdown.markdown(
                msg.get("content", ""), extensions=["fenced_code", "tables"]
            )
            blocks.append(
                f'<div class="msg {cls}"><b>{label}</b><br>{rendered}</div>'
            )
        if pending_text is not None:
            rendered = markdown.markdown(
                pending_text or "…", extensions=["fenced_code", "tables"]
            )
            blocks.append(
                f'<div class="msg assistant"><b>IA</b><br>{rendered}</div>'
            )
        self.chat.setHtml("\n".join(blocks))
        bar = self.chat.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_busy(self, busy, info=""):
        self.send_btn.setDisabled(busy)
        self.stop_btn.setDisabled(not busy)
        self.input.setDisabled(busy)
        self.mode.setDisabled(busy)
        if busy:
            self.generation_started = time.perf_counter()
            self.elapsed_timer.start()
        else:
            self.elapsed_timer.stop()
            self.generation_started = None
        if info:
            self.info.setText(info)

    def send_message(self):
        text = self.input.toPlainText().strip()
        if not text or not self.current or self.worker:
            return

        try:
            if self.mode.currentData() == "fast":
                self.ensure_tunnel()
        except Exception as exc:
            QMessageBox.critical(self, "Connexion", str(exc))
            return

        self.input.clear()
        self.current["messages"].append({"role": "user", "content": text})
        if self.current.get("title") == "Nouvelle conversation":
            self.current["title"] = text.replace("\n", " ")[:45]
        save_conversation(self.current)
        self.reload_conversations(self.current["id"])

        mode = self.mode.currentData()
        self._set_busy(True, "Génération…")

        if mode == "fast":
            messages = [
                {
                    "role": "system",
                    "content": "Tu es un assistant utile. Réponds en français sauf demande contraire. Sois clair et concis.",
                }
            ]
            messages += [
                {"role": m["role"], "content": m["content"]}
                for m in self.current["messages"]
            ]
            self.streaming_text = ""
            self.render_chat(pending_text="")
            self.worker = FastChatThread(self.cfg, messages, self)
            self.worker.token.connect(self.fast_token)
            self.worker.done.connect(self.fast_done)
            self.worker.failed.connect(self.worker_failed)
            self.worker.start()
        else:
            self.render_chat(pending_text="Agent en cours…")
            key = "desktop-" + self.current["id"].replace("-", "")[:24]
            self.worker = AgentChatThread(self.cfg, text, key, self)
            self.worker.done.connect(self.agent_done)
            self.worker.failed.connect(self.worker_failed)
            self.worker.start()

    def fast_token(self, token):
        self.streaming_text += token
        self.render_chat(pending_text=visible_model_text(self.streaming_text))

    def fast_done(self, seconds, interrupted, _raw_chars):
        visible = visible_model_text(self.streaming_text)
        if visible:
            if interrupted:
                visible += "\n\n_[génération interrompue]_"
            self.current["messages"].append(
                {"role": "assistant", "content": visible}
            )
            save_conversation(self.current)

        self.worker = None
        approx_tokens = max(1, len(visible) / 4) if visible else 0
        speed = approx_tokens / seconds if seconds > 0 and approx_tokens else 0
        label = (
            "interrompu"
            if interrupted
            else f"{seconds:.1f} s • ≈{speed:.1f} tok/s"
        )
        self._set_busy(False, f"Rapide • {label}")
        self.reload_conversations(self.current["id"])

    def agent_done(self, text, seconds, interrupted):
        if text.strip():
            self.current["messages"].append(
                {"role": "assistant", "content": text.strip()}
            )
            save_conversation(self.current)
        self.worker = None
        label = "interrompu" if interrupted else f"{seconds:.1f} s"
        self._set_busy(False, f"Agent • {label}")
        self.reload_conversations(self.current["id"])

    def worker_failed(self, error):
        self.worker = None
        self._set_busy(False, "Erreur")
        self.render_chat()
        QMessageBox.critical(self, "Erreur", error)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(1500)
        self.tunnel.stop()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LocalAIClient")
    app.setStyleSheet(APP_STYLE)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
