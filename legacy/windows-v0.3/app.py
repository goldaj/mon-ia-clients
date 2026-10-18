
import html
import sys
from pathlib import Path

import markdown
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QSplitter, QTextBrowser, QTextEdit, QToolBar, QVBoxLayout, QWidget
)

from config import AppConfig, load_config, save_config
from storage import list_conversations, new_conversation, save_conversation, delete_conversation
from ssh_tools import SshTunnel, SshError
from workers import FastChatThread, AgentChatThread


APP_STYLE = """
QMainWindow, QWidget {
    background: #111318;
    color: #e7eaf0;
    font-size: 14px;
}
QToolBar {
    background: #171a21;
    border: none;
    spacing: 8px;
    padding: 6px;
}
QPushButton {
    background: #242936;
    border: 1px solid #343b4d;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton:hover { background: #2d3444; }
QPushButton:disabled { color: #707786; background: #1b1e25; }
QComboBox, QLineEdit, QSpinBox, QTextEdit {
    background: #171a21;
    border: 1px solid #343b4d;
    border-radius: 8px;
    padding: 7px;
}
QTextBrowser {
    background: #0d0f13;
    border: none;
    padding: 12px;
}
QListWidget {
    background: #15181e;
    border: none;
    padding: 4px;
}
QListWidget::item {
    padding: 9px;
    margin: 2px;
    border-radius: 7px;
}
QListWidget::item:selected { background: #293042; }
#statusLabel {
    color: #aeb6c6;
    padding: 0 8px;
}
"""

CHAT_CSS = """
<style>
body { background:#0d0f13; color:#e7eaf0; font-family:'Segoe UI'; font-size:14px; }
.msg { margin:10px 4px; padding:12px 14px; border-radius:12px; }
.user { background:#243044; margin-left:70px; }
.assistant { background:#171b23; margin-right:70px; }
.meta { color:#8b95a7; font-size:11px; margin-top:6px; }
pre { background:#0a0c10; padding:10px; border-radius:8px; overflow:auto; }
code { font-family:Consolas, monospace; }
h1,h2,h3 { color:#ffffff; }
a { color:#8db8ff; }
</style>
"""


def visible_model_text(raw: str) -> str:
    """Masque les blocs de raisonnement <think>...</think> renvoyés par LFM Thinking."""
    if not raw:
        return ""
    s = raw
    while True:
        start = s.find("<think>")
        if start == -1:
            break
        end = s.find("</think>", start + len("<think>"))
        if end == -1:
            # Raisonnement encore en cours : n'afficher que ce qui précédait <think>.
            s = s[:start]
            break
        s = s[:start] + s[end + len("</think>"):]
    return s.strip()

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
        form.addRow("Utilisateur SSH", self.user)
        form.addRow("Clé privée (optionnel)", key_row)
        form.addRow("Port local llama.cpp", self.local_port)
        form.addRow("Port distant llama.cpp", self.remote_port)
        form.addRow("Nom du modèle", self.model)
        form.addRow("Agent OpenClaw", self.agent)
        form.addRow("Timeout Agent (s)", self.timeout)

        buttons = QHBoxLayout()
        cancel = QPushButton("Annuler")
        save = QPushButton("Enregistrer")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        form.addRow(buttons)

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
        self.setWindowTitle("Local AI Client")
        self.resize(1180, 760)
        self.cfg = load_config()
        self.tunnel = SshTunnel(self.cfg)
        self.current = None
        self.worker = None
        self.streaming_text = ""
        self.generation_started = None
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(500)
        self.elapsed_timer.timeout.connect(self.update_elapsed)

        self.build_ui()
        self.reload_conversations()
        if not self.cfg.ssh_host:
            QTimer.singleShot(250, self.open_settings)
        else:
            QTimer.singleShot(350, self.auto_connect)

    def build_ui(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.mode = QComboBox()
        self.mode.addItem("⚡ Rapide", "fast")
        self.mode.addItem("🛠 Agent", "agent")
        self.mode.currentIndexChanged.connect(self.mode_changed)
        toolbar.addWidget(QLabel("Mode :"))
        toolbar.addWidget(self.mode)

        toolbar.addSeparator()

        self.connect_btn = QPushButton("Connecter")
        self.connect_btn.clicked.connect(self.toggle_tunnel)
        toolbar.addWidget(self.connect_btn)

        self.status = QLabel("Déconnecté")
        self.status.setObjectName("statusLabel")
        toolbar.addWidget(self.status)

        toolbar.addSeparator()
        new_btn = QPushButton("Nouvelle conversation")
        new_btn.clicked.connect(self.create_conversation)
        toolbar.addWidget(new_btn)

        settings_action = QAction("Paramètres", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        splitter = QSplitter()
        self.setCentralWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.addWidget(QLabel("Conversations"))
        self.conv_list = QListWidget()
        self.conv_list.currentRowChanged.connect(self.select_conversation)
        left_layout.addWidget(self.conv_list)
        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self.delete_current)
        left_layout.addWidget(delete_btn)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 6, 6, 6)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        right_layout.addWidget(self.chat, 1)

        self.input = QTextEdit()
        self.input.setPlaceholderText("Écris ton message…  Ctrl+Entrée pour envoyer")
        self.input.setMaximumHeight(120)
        self.input.installEventFilter(self)
        right_layout.addWidget(self.input)

        bottom = QHBoxLayout()
        self.info = QLabel("")
        bottom.addWidget(self.info)
        bottom.addStretch()
        self.stop_btn = QPushButton("Arrêter")
        self.stop_btn.setDisabled(True)
        self.stop_btn.clicked.connect(self.stop_generation)
        bottom.addWidget(self.stop_btn)

        self.send_btn = QPushButton("Envoyer")
        self.send_btn.clicked.connect(self.send_message)
        bottom.addWidget(self.send_btn)
        right_layout.addLayout(bottom)

        splitter.addWidget(right)
        splitter.setSizes([260, 920])

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    return super().eventFilter(obj, event)
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def auto_connect(self):
        try:
            self.ensure_tunnel()
            self.info.setText("Prêt")
        except Exception as exc:
            self.info.setText("SSH non connecté")

    def update_elapsed(self):
        if self.generation_started is None:
            return
        import time
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
            was_running = self.tunnel.is_running()
            if was_running:
                self.tunnel.stop()
            dlg.apply()
            self.tunnel = SshTunnel(self.cfg)
            self.update_connection_state()

    def update_connection_state(self):
        if self.tunnel.is_running():
            self.status.setText("Tunnel SSH actif")
            self.connect_btn.setText("Déconnecter")
        else:
            self.status.setText("Déconnecté")
            self.connect_btn.setText("Connecter")

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
        selected_row = 0
        for i, conv in enumerate(conversations):
            prefix = "⚡ " if conv.get("mode") == "fast" else "🛠 "
            self.conv_list.addItem(prefix + conv.get("title", "Conversation"))
            self.conv_list.item(i).setData(Qt.UserRole, conv)
            if select_id and conv.get("id") == select_id:
                selected_row = i
        self.conv_list.blockSignals(False)

        if conversations:
            self.conv_list.setCurrentRow(selected_row)
            self.select_conversation(selected_row)
        else:
            self.create_conversation()

    def create_conversation(self):
        mode = self.mode.currentData() or "fast"
        conv = new_conversation(mode)
        self.reload_conversations(conv["id"])

    def delete_current(self):
        if not self.current:
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
        mode = self.current.get("mode", "fast")
        idx = self.mode.findData(mode)
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
            role = msg.get("role")
            content = msg.get("content", "")
            cls = "user" if role == "user" else "assistant"
            label = "Vous" if role == "user" else "IA"
            rendered = markdown.markdown(content, extensions=["fenced_code", "tables"])
            blocks.append(
                f'<div class="msg {cls}"><b>{label}</b><br>{rendered}</div>'
            )
        if pending_text is not None:
            rendered = markdown.markdown(pending_text or "…", extensions=["fenced_code"])
            blocks.append(
                f'<div class="msg assistant"><b>IA</b><br>{rendered}</div>'
            )
        self.chat.setHtml("\n".join(blocks))
        bar = self.chat.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_busy(self, busy, info=""):
        import time
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
            # Rapide a besoin du tunnel HTTP. Agent utilise SSH directement,
            # mais tester le tunnel ici garantit aussi que les identifiants SSH sont bons.
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
            api_messages = [
                {
                    "role": "system",
                    "content": "Tu es un assistant utile. Réponds en français sauf demande contraire. Sois clair et concis."
                }
            ] + [
                {"role": m["role"], "content": m["content"]}
                for m in self.current["messages"]
            ]
            self.streaming_text = ""
            self.render_chat(pending_text="")
            self.worker = FastChatThread(self.cfg, api_messages, self)
            self.worker.token.connect(self.fast_token)
            self.worker.done.connect(self.fast_done)
            self.worker.failed.connect(self.worker_failed)
            self.worker.start()
        else:
            self.render_chat(pending_text="Agent en cours…")
            session_key = "desktop-" + self.current["id"].replace("-", "")[:24]
            self.worker = AgentChatThread(self.cfg, text, session_key, self)
            self.worker.done.connect(self.agent_done)
            self.worker.failed.connect(self.worker_failed)
            self.worker.start()

    def fast_token(self, token):
        self.streaming_text += token
        self.render_chat(pending_text=visible_model_text(self.streaming_text))

    def fast_done(self, seconds, interrupted):
        visible = visible_model_text(self.streaming_text)
        if visible:
            if interrupted:
                visible += "\n\n_[génération interrompue]_"
            self.current["messages"].append({"role": "assistant", "content": visible})
            save_conversation(self.current)
        self.worker = None
        label = "interrompu" if interrupted else f"{seconds:.1f} s"
        self._set_busy(False, f"Rapide • {label}")
        self.reload_conversations(self.current["id"])

    def agent_done(self, text, seconds, interrupted):
        if text.strip():
            self.current["messages"].append({"role": "assistant", "content": text.strip()})
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
        self.tunnel.stop()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LocalAIClient")
    app.setStyleSheet(APP_STYLE)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
