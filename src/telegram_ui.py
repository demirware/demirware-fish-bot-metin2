"""Turkish Telegram setup UI with background requests and OS credential storage."""
import json
import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QInputDialog)
from telegram_service import perform, validate_token, validate_chat, TelegramError
from session_runtime import atomic_json

SERVICE = "DemirwareFishBotMetin2.Telegram"


class RequestWorker(QThread):
    result = Signal(str, object)

    def __init__(self, token, action, chat, parent):
        super().__init__(parent)
        self.token, self.action, self.chat = token, action, chat

    def run(self):
        try:
            self.result.emit(self.action, perform(self.token, self.action, self.chat))
        except TelegramError as exc:
            self.result.emit("error", str(exc))
        except Exception:
            self.result.emit("error", "İşlem tamamlanamadı. Ayarları kontrol edin.")
        finally:
            self.token = ""


class TelegramTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".config")))
        self.settings_path = base / "DemirwareFishBotMetin2" / "telegram.json"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        guide = QGroupBox("1. Telegram botu oluştur")
        guide_layout = QVBoxLayout(guide)
        text = QLabel(
            'Telegram’da doğrulanmış <a href="https://t.me/BotFather">@BotFather</a> hesabını açın.<br>'
            '1. <b>/newbot</b> yazın; botunuza bir ad verin.<br>'
            '2. Sonu <b>bot</b> ile biten bir kullanıcı adı seçin.<br>'
            '3. Verilen token’ı aşağıdaki alana yapıştırın.<br>'
            '4. Kendi botunuzun sohbetini açıp <b>/start</b> gönderin.<br>'
            '5. <b>Sohbetleri bul</b> düğmesine basıp kendi sohbetinizi seçin.')
        text.setWordWrap(True)
        text.setOpenExternalLinks(True)
        guide_layout.addWidget(text)
        layout.addWidget(guide)
        settings = QGroupBox("2. Bot ayarları")
        form = QFormLayout(settings)
        form.setSpacing(12)
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText("BotFather token’ı")
        self.chat = QLineEdit()
        self.chat.setPlaceholderText("Örneğin: 123456789")
        form.addRow("Bot token’ı", self.token)
        form.addRow("Sohbet kimliği", self.chat)
        layout.addWidget(settings)
        actions = QHBoxLayout()
        self.buttons = []
        for label, callback in [
            ("Bağlantıyı kontrol et", lambda: self.request("check")),
            ("Sohbetleri bul", lambda: self.request("chats")),
            ("Test mesajı gönder", lambda: self.request("test")),
            ("Kaydet", self.save), ("Kaydı sil", self.forget),
        ]:
            button = QPushButton(label)
            button.setMinimumHeight(36)
            button.clicked.connect(callback)
            actions.addWidget(button)
            self.buttons.append(button)
        layout.addLayout(actions)
        self.status = QLabel("Henüz bağlantı kontrol edilmedi.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        note = QLabel("Token yalnızca Windows Kimlik Bilgileri Yöneticisi’nde saklanır; profillere eklenmez. "
                      "Test mesajı seçtiğiniz sohbete gönderilir. Bu sürümde otomatik bildirim ve uzaktan kontrol yoktur. "
                      "Sohbet bulunamazsa botunuza yeni bir mesaj gönderip tekrar deneyin.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.load()

    def vault(self):
        # Explicit OS backend: never fall back to plaintext keyring plugins.
        if os.name != "nt":
            raise RuntimeError("Windows credential storage required")
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()

    def load(self):
        try:
            if self.settings_path.exists():
                self.chat.setText(str(json.loads(self.settings_path.read_text(encoding="utf-8")).get("chat_id", "")))
            self.token.setText(self.vault().get_password(SERVICE, "bot_token") or "")
        except Exception:
            self.status.setText("Kayıtlı ayarlar okunamadı. Token’ı bu oturum için girebilirsiniz.")

    def save(self):
        try:
            token, chat = validate_token(self.token.text()), validate_chat(self.chat.text())
            self.vault().set_password(SERVICE, "bot_token", token)
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(self.settings_path, {"chat_id": chat})
            self.status.setText("Ayarlar kaydedildi. Bağlantıyı ayrıca kontrol edebilirsiniz.")
        except TelegramError as exc:
            self.status.setText(str(exc))
        except Exception:
            self.status.setText("Ayarlar kaydedilemedi. Windows kimlik deposunu ve kurulum bağımlılıklarını kontrol edin.")

    def forget(self):
        try:
            vault = self.vault()
            if vault.get_password(SERVICE, "bot_token"):
                vault.delete_password(SERVICE, "bot_token")
            self.settings_path.unlink(missing_ok=True)
            self.token.clear()
            self.chat.clear()
            self.status.setText("Kayıtlı Telegram ayarları silindi.")
        except Exception:
            self.status.setText("Kayıt tamamen silinemedi. Windows kimlik deposunu kontrol edin.")

    def busy(self):
        return self.worker is not None and self.worker.isRunning()

    def request(self, action):
        if self.busy():
            return
        try:
            token = validate_token(self.token.text())
            chat = validate_chat(self.chat.text()) if action == "test" else self.chat.text()
        except TelegramError as exc:
            self.status.setText(str(exc))
            return
        self.status.setText("Telegram yanıtı bekleniyor…")
        for widget in [*self.buttons, self.token, self.chat]:
            widget.setEnabled(False)
        self.worker = RequestWorker(token, action, chat, self)
        self.worker.result.connect(self.result)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
        for widget in [*self.buttons, self.token, self.chat]:
            widget.setEnabled(True)

    def result(self, action, value):
        if action == "chats":
            if not value:
                self.status.setText("Özel sohbet bulunamadı. Botunuza /start gönderip yeniden deneyin.")
                return
            choices = [f"{name} ({chat})" for chat, name in value.items()]
            selected, ok = QInputDialog.getItem(self, "Sohbet seç", "Mesajın gönderileceği sohbet", choices, 0, False)
            if ok:
                self.chat.setText(list(value)[choices.index(selected)])
            self.status.setText("Sohbet seçildi. Kaydedebilir veya test mesajı gönderebilirsiniz." if ok else "Sohbet seçimi iptal edildi.")
        else:
            self.status.setText(str(value))
