"""Opt-in Telegram command listener. Network work never runs on Qt's UI thread."""
import queue
import threading
import time
from PySide6.QtCore import QThread, Signal
from telegram_service import api_call, TelegramError
from remote_protocol import command_from_update


class TelegramListener(QThread):
    command = Signal(str, str)
    status = Signal(str)

    def __init__(self, token, chat, parent=None):
        super().__init__(parent)
        self.token, self.chat = token, chat
        self.halt = threading.Event()
        self.outgoing = queue.Queue(maxsize=50)
        self.enabled_at = time.time()
        self.ready = False

    def stop(self):
        self.halt.set()

    def send(self, text):
        if not self.halt.is_set():
            try:
                self.outgoing.put_nowait(str(text)[:4000])
            except queue.Full:
                self.status.emit("Telegram gönderim kuyruğu dolu; bildirim atlandı.")

    def run(self):
        offset = None
        try:
            username = api_call(self.token, "getMe").get("username", "")
            # Drain pre-existing updates without executing them. Do not delete webhooks.
            pending = api_call(self.token, "getUpdates", {"offset": -1, "timeout": 0, "limit": 1})
            if pending:
                offset = pending[-1]["update_id"] + 1
            self.enabled_at = time.time()
            self.ready = True
            self.status.emit("Uzaktan kontrol açık. Şimdi Telegram'dan /start veya /durum gönderebilirsiniz.")
            while not self.halt.is_set():
                try:
                    # At most three messages between polls; never block game input.
                    for _ in range(3):
                        try:
                            text = self.outgoing.get_nowait()
                        except queue.Empty:
                            break
                        if self.halt.is_set():
                            break
                        api_call(self.token, "sendMessage", {"chat_id": self.chat, "text": text})
                    payload = {"timeout": 2, "limit": 20, "allowed_updates": ["message"]}
                    if offset is not None:
                        payload["offset"] = offset
                    updates = api_call(self.token, "getUpdates", payload)
                    for update in updates:
                        uid = update.get("update_id")
                        if not isinstance(uid, int) or (offset is not None and uid < offset):
                            continue
                        offset = uid + 1  # consume every update once, including unauthorized ones
                        command = command_from_update(update, self.chat, username, self.enabled_at)
                        if command and not self.halt.is_set():
                            self.command.emit(*command)
                    self.halt.wait(.3)
                except TelegramError as exc:
                    self.status.emit(str(exc))
                    self.halt.wait(5)
        except TelegramError as exc:
            self.status.emit(str(exc))
        except Exception:
            self.status.emit("Telegram dinleyicisi durdu. Bağlantıyı kontrol edin.")
        finally:
            self.ready = False
            self.token = ""
