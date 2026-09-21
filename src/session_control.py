"""Qt-thread orchestration for remote commands and verified desktop transitions."""
from copy import deepcopy
from pathlib import Path
import threading
import time
from PySide6.QtCore import QObject, QTimer, Signal, QThread
from PySide6.QtWidgets import (QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QLabel, QHBoxLayout, QFileDialog)
from remote_protocol import Countdown, format_duration, stats_report
from visual_workflow import validate_workflow, WorkflowRunner


def checked_recipe(config, action):
    recipe = deepcopy(config.get("operations", {}).get("workflows", {}).get(action, {}))
    if not recipe.get("enabled"):
        raise ValueError("Önce Oturumlar > Görsel akışlar bölümünde ilgili geçiş akışını hazırlayıp etkinleştirin.")
    validate_workflow(recipe)
    if recipe["steps"][-1]["template"] == recipe["steps"][0]["template"]:
        raise ValueError("Son doğrulama görseli başlangıç ekranından farklı olmalıdır.")
    # A generic game background cannot certify character/channel switching.
    if not any(s["action"] == "click" for s in recipe["steps"]):
        raise ValueError("Geçiş akışında menü düğmesine tıklama adımı gerekli.")
    if action == "character_select" and not any(s["action"] == "key" and s.get("key") == "esc" for s in recipe["steps"]):
        raise ValueError("Karakter geçişinde ESC adımı gerekli.")
    for step in recipe["steps"]:
        for key in ("template", "target"):
            if key in step and not Path(step[key]).is_file():
                raise ValueError("Geçiş akışındaki bir görsel dosyası bulunamadı.")
    return recipe


class TransitionWorker(QThread):
    completed = Signal(bool, str)

    def __init__(self, targets, config, recipe, action, parent=None):
        super().__init__(parent)
        self.targets, self.config, self.recipe, self.action = targets, config, recipe, action
        self.halt = threading.Event()

    def stop(self):
        self.halt.set()

    def run(self):
        results = []
        success = True
        try:
            from managed_bot import ManagedFishingBot
            from window_manager import WindowManager
            for index, window in self.targets:
                if self.halt.is_set():
                    raise RuntimeError("İşlem iptal edildi")
                worker = None
                try:
                    wm = WindowManager()
                    wm.selected_window = window
                    worker = ManagedFishingBot(None, deepcopy(self.config), wm, bot_id=index)
                    worker.running = True
                    # Cancellation guards every keyboard/mouse step, including focus races.
                    worker._halt = self.halt
                    worker._port.cancelled = self.halt.is_set
                    WorkflowRunner(worker._port, self.halt.is_set).run(self.recipe, max_seconds=180)
                    if self.halt.is_set():
                        raise RuntimeError("İşlem iptal edildi")
                    result = "Karakter atımı başarılı; karakter seçim ekranı doğrulandı." if self.action == "character_select" else "Kanal değişimi başarılı; hedef kanal görseli doğrulandı."
                    results.append(f"W{index + 1}: {result}")
                except Exception as exc:
                    success = False
                    results.append(f"W{index + 1}: Geçiş doğrulanamadı: {exc}")
                    break  # no blind retries or actions on remaining clients
                finally:
                    if worker:
                        worker.running = False
                        if worker.sct:
                            worker.sct.close()
                        worker.mouse_backend.close()
        except Exception as exc:
            success = False
            results.append(f"Geçiş tamamlanamadı: {exc}")
        self.completed.emit(success and not self.halt.is_set(), "\n".join(results))


class TimerPanel(QGroupBox):
    def __init__(self, controller):
        super().__init__("Süre sonunda yapılacak işlem")
        self.controller = controller
        form = QFormLayout(self)
        self.minutes = QLineEdit()
        self.minutes.setPlaceholderText("Örneğin 60 (dakika)")
        self.action = QComboBox()
        self.action.addItem("Karakter seçim ekranına dön", "character_select")
        self.action.addItem("Kanal değiştir", "channel_change")
        self.resume = QCheckBox("Kanal geçişi doğrulanınca balık tutmaya devam et")
        self.repeat = QCheckBox("Başarılı kanal geçişinden sonra sayacı tekrarla")
        self.action.currentIndexChanged.connect(self.update_options)
        self.resume.toggled.connect(self.update_options)
        self.fish_template = QLineEdit(controller.owner.config.get("catch_success_template", ""))
        self.fish_template.setPlaceholderText("İsteğe bağlı: balık yakalandı sonucunun görseli")
        pick = QPushButton("Başarı görseli seç")
        pick.clicked.connect(self.pick_success)
        form.addRow("Süre (dakika)", self.minutes)
        form.addRow("İşlem", self.action)
        form.addRow(self.resume)
        form.addRow(self.repeat)
        row = QHBoxLayout()
        row.addWidget(self.fish_template)
        row.addWidget(pick)
        form.addRow("Balık sayımı", row)
        self.fish_template.editingFinished.connect(self.save_template)
        buttons = QHBoxLayout()
        start = QPushButton("Sayacı başlat")
        start.clicked.connect(controller.arm)
        cancel = QPushButton("Sayacı iptal et")
        cancel.clicked.connect(controller.cancel_timer)
        configure = QPushButton("Geçiş akışlarını düzenle")
        configure.clicked.connect(self.edit_workflows)
        for button in (start, cancel, configure):
            buttons.addWidget(button)
        form.addRow(buttons)
        self.status = QLabel("Sayaç kapalı. Süre, Sayacı başlat düğmesine bastığınızda başlar.")
        self.status.setWordWrap(True)
        form.addRow(self.status)
        note = QLabel("İşlem o anda seçili istemcilere uygulanır. Önce görsel akışları kalibre edin. "
                      "Karakter geçişi karakter seçim ekranında durur. Kanal geçişinin son görseli hedef kanalı ayırt etmelidir. "
                      "F8 veya /stop geçişi ve sayacı iptal eder.")
        note.setWordWrap(True)
        form.addRow(note)
        self.update_options()

    def update_options(self):
        channel = self.action.currentData() == "channel_change"
        self.resume.setEnabled(channel)
        if not channel:
            self.resume.setChecked(False)
        self.repeat.setEnabled(channel and self.resume.isChecked())
        if not self.repeat.isEnabled():
            self.repeat.setChecked(False)

    def edit_workflows(self):
        if self.controller.busy():
            self.status.setText("Önce geçişin tamamlanmasını bekleyin.")
            return
        from operations_ui import WorkflowEditor
        WorkflowEditor(self.controller.owner).exec()

    def pick_success(self):
        path, _ = QFileDialog.getOpenFileName(self, "Balık yakalama başarı görseli", "", "Görsel (*.png *.jpg)")
        if path:
            self.fish_template.setText(path)
            self.save_template()

    def save_template(self):
        self.controller.owner.config["catch_success_template"] = self.fish_template.text().strip()
        self.controller.owner.save_config()


class SessionControl(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.countdown = Countdown()
        self.pending = None
        self.worker = None
        self.cancelled = False
        self.history = {}
        self.started = None
        self.elapsed = 0
        self.timer_plan = None
        self.restart_plan = None
        self.panel = TimerPanel(self)
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def busy(self):
        return self.pending is not None or self.worker is not None

    def notify(self, text):
        self.panel.status.setText(text)
        self.owner.telegram_tab.send_remote(text)

    def arm(self):
        self.countdown.cancel()
        try:
            if self.busy():
                raise ValueError("Devam eden geçişi bekleyin.")
            action = self.panel.action.currentData()
            checked_recipe(self.owner.config, action)
            if not self.owner.selected_window_names():
                raise ValueError("Önce İstemciler sekmesinden pencere seçin.")
            self.countdown.arm(self.panel.minutes.text())
            self.timer_plan = (action, self.panel.resume.isChecked(), self.panel.repeat.isChecked())
        except (ValueError, TypeError) as exc:
            self.panel.status.setText(str(exc))

    def cancel_timer(self):
        self.countdown.cancel()
        self.timer_plan = None
        if self.restart_plan:
            self.restart_plan["repeat"] = False
        if self.pending:
            self.pending["repeat"] = False
        self.panel.status.setText("Sayaç iptal edildi.")

    def cancel_all(self):
        self.cancel_timer()
        self.cancelled = True
        self.pending = None
        self.restart_plan = None
        if self.worker:
            self.worker.stop()

    def session_started(self):
        if self.started is None:
            self.started = time.monotonic()

    def record_stop(self, index, bot):
        if bot:
            old = self.history.get(index, {})
            self.history[index] = {
                "games": old.get("games", 0) + bot.total_games,
                "bait_used": old.get("bait_used", 0) + bot.total_games,
                "bait": max(0, bot.bait_counter),
                "fish": old.get("fish", 0) + getattr(bot, "confirmed_fish", 0),
                "fish_measured": old.get("fish_measured", True) and getattr(bot, "fish_measurement_ok", False),
            }

    def report(self):
        records = deepcopy(self.history)
        for i, bot in self.owner.bots.items():
            old = records.get(i, {})
            records[i] = {"games": old.get("games", 0) + bot.total_games,
                          "bait_used": old.get("bait_used", 0) + bot.total_games,
                          "bait": bot.bait_counter,
                          "fish": old.get("fish", 0) + getattr(bot, "confirmed_fish", 0),
                          "fish_measured": old.get("fish_measured", True) and getattr(bot, "fish_measurement_ok", False)}
        for i, row in enumerate(self.owner.dashboard.window_rows):
            if row.selectedWindow() and i not in records:
                records[i] = {"bait": self.owner.window_stats[i]["bait"]}
        duration = self.elapsed + (time.monotonic() - self.started if self.started is not None else 0)
        listener = self.owner.telegram_tab.listener
        seconds = max(0, time.time() - listener.enabled_at) if listener else 0
        return stats_report(duration, list(records.values()), sum(b.running for b in self.owner.bots.values()), seconds)

    def command(self, name, argument):
        if name == "/stop":
            threads = self.input_threads()
            self.owner.stop_all_bots()
            self.owner.telegram_tab.send_remote("Durdurma istendi; tüm işçiler durduğunda bildireceğim.")
            self.pending = {"kind": "stop", "deadline": time.monotonic() + 30,
                            "threads": threads}
        elif name in {"/durum", "/istatistik"}:
            self.owner.telegram_tab.send_remote(self.report())
        elif name == "/start":
            if self.busy():
                self.owner.telegram_tab.send_remote("Geçiş veya durdurma sürüyor. Tamamlanmasını bekleyin.")
            elif self.owner.bots:
                if any(b.paused for b in self.owner.bots.values()):
                    self.owner.toggle_pause_all()
                    self.owner.telegram_tab.send_remote("Balık oturumuna devam ediliyor.\n" + self.report())
                else:
                    self.owner.telegram_tab.send_remote("Balık oturumu zaten açık.\n" + self.report())
            else:
                try:
                    self.owner.start_all_bots(remote=True)
                    message = "Balık oturumu başlatıldı." if self.owner.bots else "Başlatılamadı; oyun pencerelerini ve ayarları kontrol edin."
                except Exception as exc:
                    self.owner.stop_all_bots()
                    message = "Başlatılamadı: " + str(exc)
                self.owner.telegram_tab.send_remote(message)
        elif name in {"/karakterat", "/kanal"}:
            self.transition("character_select" if name == "/karakterat" else "channel_change")
        elif name == "/pm":
            self.owner.telegram_tab.send_remote("/pm yanıt metni: oyun içi PM ekran örnekleri henüz eklenmedi. Mesaj gönderilmedi; eski yanıtlar bekletilip sonradan gönderilmez.")
        else:
            self.owner.telegram_tab.send_remote("/start — balık botunu başlat\n/stop — botu, sayacı ve geçişi durdur\n/karakterat — karakter seçim ekranına dön\n/kanal — kalibre edilmiş hedef kanala geç\n/durum veya /istatistik — oturum bilgileri\n/pm yanıt — PM görsel entegrasyonu bekleniyor")

    def input_threads(self):
        threads = list(self.owner.bot_threads.values())
        if self.owner._jigsaw_dialog:
            threads.extend(self.owner._jigsaw_dialog._threads.values())
        return threads

    def transition(self, action, resume=False, repeat=False):
        if self.busy():
            self.notify("Başka bir geçiş/durdurma sürüyor; yeni istek uygulanmadı.")
            return
        threads = self.input_threads()
        self.owner.stop_all_bots(cancel_actions=False)
        try:
            recipe = checked_recipe(self.owner.config, action)
            from window_manager import WindowManager
            windows = dict(WindowManager.get_all_windows())
            names = self.owner.selected_window_names()
            if len(set(names)) != len(names):
                raise ValueError("Aynı oyun penceresi birden fazla istemciye atanmış.")
            targets = [(i, windows[row.selectedWindow()]) for i, row in enumerate(self.owner.dashboard.window_rows) if row.selectedWindow()]
            if not targets:
                raise ValueError("Oyun penceresi seçilmedi.")
            self.cancelled = False
            self.pending = dict(kind=action, deadline=time.monotonic() + 30, threads=threads,
                                targets=targets, config=deepcopy(self.owner.config), recipe=recipe,
                                names=list(self.owner.selected_window_names()),
                                resume=resume, repeat=repeat)
            self.notify("Balık botu durduruluyor. Geçiş başlamadan önce tüm işçiler beklenecek.")
        except Exception as exc:
            self.countdown.cancel()
            self.notify("Geçiş başlatılamadı; bot için durdurma istendi. " + str(exc))

    def tick(self):
        if self.started is not None and not self.owner.bots:
            self.elapsed += time.monotonic() - self.started
            self.started = None
        remaining = self.countdown.remaining()
        if remaining is not None:
            self.panel.status.setText("Kalan süre: " + format_duration(remaining))
        if self.countdown.due() and self.timer_plan:
            self.transition(*self.timer_plan)
        if self.pending:
            pending = self.pending
            if time.monotonic() >= pending["deadline"]:
                self.pending = None
                self.notify("İşçiler zamanında durmadı; geçiş ve otomatik devam iptal edildi.")
                return
            if self.owner.bots or any(t.is_alive() for t in pending["threads"]) or self.worker:
                return
            child = self.owner._jigsaw_dialog
            if child and child.is_running():
                return
            self.pending = None
            if pending["kind"] == "stop":
                self.notify("Bot durduruldu.\n" + self.report())
                return
            self.restart_plan = pending
            self.worker = TransitionWorker(pending["targets"], pending["config"], pending["recipe"], pending["kind"], self)
            self.worker.completed.connect(self.transition_result)
            self.worker.finished.connect(self.transition_finished)
            self.worker.start()

    def transition_result(self, success, text):
        if self.cancelled:
            success, text = False, "Geçiş iptal edildi; otomatik devam yapılmadı."
        if self.restart_plan:
            self.restart_plan["success"] = success
        self.notify(text + "\n" + self.report())

    def transition_finished(self):
        worker, self.worker = self.worker, None
        if worker:
            worker.deleteLater()
        plan, self.restart_plan = self.restart_plan, None
        if not self.cancelled and plan and plan.get("success") and plan["resume"]:
            try:
                if list(self.owner.selected_window_names()) != plan["names"]:
                    raise ValueError("Pencere seçimi değişti; otomatik devam iptal edildi.")
                self.owner.start_all_bots(remote=True)
                if not self.owner.bots:
                    raise ValueError("Balık oturumu başlatılamadı.")
                self.notify("Kanal geçişinden sonra balık oturumu yeniden başlatıldı.")
                if plan["repeat"]:
                    self.countdown.arm(self.countdown.seconds / 60)
            except Exception as exc:
                self.owner.stop_all_bots()
                self.notify("Geçiş tamamlandı ancak devam başlatılamadı: " + str(exc))
