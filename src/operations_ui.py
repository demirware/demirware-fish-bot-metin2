"""Turkish operations dashboard and visual workflow editor."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)
from session_runtime import DEFAULT_OPERATIONS
from visual_workflow import validate_workflow


RECIPE_NAMES = {"restock": "Yem yenileme", "cook": "Envanter / pişirme",
                "reconnect": "Yeniden giriş", "jigsaw_open": "Yapbozu aç",
                "jigsaw_close": "Yapbozdan balığa dön"}
ACTIONS = {"expect": "Görseli doğrula", "click": "Sol tıkla", "right_click": "Sağ tıkla",
           "key": "Tuşa bas", "drag": "Görsele sürükle"}


def button(text, callback):
    widget = QPushButton(text)
    widget.setMinimumHeight(30)
    widget.clicked.connect(callback)
    return widget


class CropCanvas(QLabel):
    def __init__(self, pixmap):
        super().__init__()
        self.original = pixmap
        self.scaled = pixmap.scaled(900, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(self.scaled)
        self.setFixedSize(self.scaled.size())
        self.selection = QRect()
        self.anchor = QPoint()

    def mousePressEvent(self, event):
        self.anchor = event.position().toPoint()
        self.selection = QRect(self.anchor, self.anchor)
        self.update()

    def mouseMoveEvent(self, event):
        self.selection = QRect(self.anchor, event.position().toPoint()).normalized().intersected(self.rect())
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#60d5bc"), 2))
        painter.drawRect(self.selection)

    def cropped(self):
        if min(self.selection.width(), self.selection.height()) < 6:
            return None
        sx = self.original.width() / self.width()
        sy = self.original.height() / self.height()
        return self.original.copy(QRect(int(self.selection.x() * sx), int(self.selection.y() * sy),
                                       int(self.selection.width() * sx), int(self.selection.height() * sy)))


class CropDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayırt edici bir düğme veya simgeyi seç")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Fareyle alan seç. Küçük, tekil ve değişmeyen bir görüntü kullan."))
        self.canvas = CropCanvas(pixmap)
        layout.addWidget(self.canvas)
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)


class WorkflowEditor(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.recipes = deepcopy(owner.config.get("operations", {}).get("workflows", {}))
        self.setWindowTitle("Görsel otomasyon akışları")
        self.resize(880, 680)
        self.steps = []
        self.key = "restock"
        layout = QVBoxLayout(self)
        hint = QLabel("Her adım kendi ekranını tanır. Son adım sonucu doğrular. Görsel bulunamazsa işlem durur.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        top = QHBoxLayout()
        self.kind = QComboBox()
        for key, label in RECIPE_NAMES.items():
            self.kind.addItem(label, key)
        self.enabled = QCheckBox("Bu akışı etkinleştir")
        top.addWidget(self.kind)
        top.addWidget(self.enabled)
        top.addStretch()
        layout.addLayout(top)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["İşlem", "Görsel", "Hedef / tuş"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 330)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        form = QFormLayout()
        self.action = QComboBox()
        for key, label in ACTIONS.items():
            self.action.addItem(label, key)
        form.addRow("İşlem", self.action)
        self.template = QLineEdit()
        template_row = QHBoxLayout()
        template_row.addWidget(self.template)
        template_row.addWidget(button("Görsel seç", lambda: self.pick(self.template)))
        template_row.addWidget(button("Oyundan yakala", self.capture))
        form.addRow("Aranacak görsel", template_row)
        self.target = QLineEdit()
        target_row = QHBoxLayout()
        target_row.addWidget(self.target)
        target_row.addWidget(button("Hedef görsel", lambda: self.pick(self.target)))
        form.addRow("Sürükleme hedefi", target_row)
        self.key_choice = QComboBox()
        self.key_choice.addItems(["space", "enter", "esc", "1", "2", "3", "4", "f1", "f2", "f3", "f4", "i"])
        form.addRow("Tuş", self.key_choice)
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(.1, 60)
        self.timeout.setValue(8)
        form.addRow("En fazla bekleme (sn)", self.timeout)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(.8, 1)
        self.threshold.setSingleStep(.01)
        self.threshold.setValue(.92)
        form.addRow("Görsel eşleşme eşiği", self.threshold)
        layout.addLayout(form)
        actions = QHBoxLayout()
        actions.addWidget(button("Adım ekle", self.add_step))
        actions.addWidget(button("Seçileni sil", self.remove_step))
        actions.addWidget(button("Yukarı", lambda: self.move(-1)))
        actions.addWidget(button("Aşağı", lambda: self.move(1)))
        layout.addLayout(actions)
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self.save)
        box.rejected.connect(self.reject)
        layout.addWidget(box)
        self.kind.currentIndexChanged.connect(self.switch)
        self.load_current()

    def pick(self, field):
        path, _ = QFileDialog.getOpenFileName(self, "Görsel seç", "", "Görseller (*.png *.jpg *.bmp)")
        if path:
            field.setText(path)

    def capture(self):
        if self.owner.bots:
            QMessageBox.information(self, "Görsel yakalama", "Önce çalışan oturumları durdur.")
            return
        from window_manager import WindowManager
        from utils import input_lock
        import numpy as np
        from mss import mss
        names = self.owner.selected_window_names()
        windows = dict(WindowManager.get_all_windows())
        if not names or names[0] not in windows:
            QMessageBox.warning(self, "Pencere gerekli", "İstemciler sekmesinden oyun penceresini seç.")
            return
        try:
            wm = WindowManager()
            wm.selected_window = windows[names[0]]
            with input_lock:
                wm.activate_window()
                x, y, w, h = wm.get_window_rect()
                with mss() as screen:
                    rgb = np.ascontiguousarray(np.asarray(screen.grab(dict(left=x, top=y, width=w, height=h)))[:, :, 2::-1])
                image = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()
            dialog = CropDialog(QPixmap.fromImage(image), self)
            if dialog.exec() == QDialog.Accepted:
                cropped = dialog.canvas.cropped()
                if cropped is not None:
                    path, _ = QFileDialog.getSaveFileName(self, "Şablonu kaydet", "template.png", "PNG (*.png)")
                    if path:
                        if not cropped.save(path, "PNG"):
                            raise OSError("Görsel kaydedilemedi")
                        self.template.setText(str(Path(path).resolve()))
        except Exception as exc:
            QMessageBox.warning(self, "Görsel alınamadı", str(exc))

    def store_current(self):
        self.recipes[self.key] = {"enabled": self.enabled.isChecked(), "steps": deepcopy(self.steps)}

    def switch(self):
        self.store_current()
        self.key = self.kind.currentData()
        self.load_current()

    def load_current(self):
        recipe = self.recipes.get(self.key, {})
        self.enabled.setChecked(recipe.get("enabled", False))
        self.steps = deepcopy(recipe.get("steps", []))
        self.redraw()

    def redraw(self):
        self.table.setRowCount(len(self.steps))
        for i, step in enumerate(self.steps):
            for j, value in enumerate((ACTIONS.get(step["action"], step["action"]),
                                        Path(step["template"]).name, step.get("key", Path(step.get("target", "")).name))):
                self.table.setItem(i, j, QTableWidgetItem(value))

    def add_step(self):
        step = dict(action=self.action.currentData(), template=self.template.text().strip(),
                    timeout=self.timeout.value(), threshold=self.threshold.value())
        if step["action"] == "drag":
            step["target"] = self.target.text().strip()
        if step["action"] == "key":
            step["key"] = self.key_choice.currentText()
        try:
            validate_workflow({"steps": [step, dict(action="expect", template=step["template"])]})
        except ValueError as exc:
            QMessageBox.warning(self, "Adım", str(exc))
            return
        self.steps.append(step)
        self.redraw()

    def remove_step(self):
        row = self.table.currentRow()
        if row >= 0:
            self.steps.pop(row)
            self.redraw()

    def move(self, direction):
        row = self.table.currentRow()
        target = row + direction
        if row >= 0 and 0 <= target < len(self.steps):
            self.steps[row], self.steps[target] = self.steps[target], self.steps[row]
            self.redraw()
            self.table.selectRow(target)

    def save(self):
        self.store_current()
        try:
            for key, recipe in self.recipes.items():
                if recipe["enabled"]:
                    validate_workflow(recipe)
                    for step in recipe["steps"]:
                        for field in ("template", "target"):
                            if field in step and not Path(step[field]).is_file():
                                raise ValueError(f"{RECIPE_NAMES[key]}: görsel bulunamadı: {step[field]}")
            self.owner.config.setdefault("operations", {})["workflows"] = self.recipes
            self.owner.save_config()
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Akış kaydedilemedi", str(exc))


class OperationsTab(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.history = {}
        self.rows = []
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        title = QLabel("OTURUM MERKEZİ")
        title.setStyleSheet("font-size:22px; font-weight:700; color:#60d5bc")
        layout.addWidget(title)
        self.summary = QLabel("Sekiz istemci · ortak giriş sırası · yerel kayıt")
        layout.addWidget(self.summary)
        self.table = QTableWidget(8, 9)
        self.table.setHorizontalHeaderLabels(["İstemci", "Durum", "Tur", "Tur/sa", "Yem*", "Hata", "Dönüş", "Beklet", "Durdur"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setFixedHeight(330)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget {background:#13171b; alternate-background-color:#181e23; border:1px solid #2a363b; border-radius:6px;} QHeaderView::section {background:#20292e; color:#9bacb6; padding:8px; border:0; font-weight:600;} QTableWidget::item {padding:6px;}")
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(1, 175)
        for col in range(2, 9):
            self.table.setColumnWidth(col, 72)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(8):
            self.table.setItem(i, 0, QTableWidgetItem(f"W{i + 1:02}"))
            self.table.setCellWidget(i, 7, button("II / >", lambda checked=False, n=i: self.pause(n)))
            self.table.setCellWidget(i, 8, button("Dur", lambda checked=False, n=i: self.stop(n)))
        layout.addWidget(self.table)
        caption = QLabel("Tur sayısı yakalanan balık sayısı değildir. *Yem değeri tahmindir. F5: beklet/devam · F8: tümünü durdur")
        caption.setWordWrap(True)
        layout.addWidget(caption)
        group = QGroupBox("Otomasyon ve oturum sınırları")
        form = QGridLayout(group)
        self.inputs = {}
        fields = [("session_minutes", "Oturum süresi (dk, 0: sınırsız)", 0, 1440, 0),
                  ("start_spacing_seconds", "İstemciler arası başlangıç (sn)", 0, 10, .8),
                  ("max_recoveries", "Oturum başına en fazla otomasyon", 0, 100, 2),
                  ("recovery_cooldown", "Otomasyon öncesi bekleme (sn)", 1, 300, 15),
                  ("jigsaw_every_rounds", "Her kaç turda yapboz (0: kapalı)", 0, 1000, 0),
                  ("poll_interval", "Algılama aralığı (sn)", .01, 1, .04)]
        for i, (key, label, low, high, default) in enumerate(fields):
            spin = QDoubleSpinBox() if key in ("start_spacing_seconds", "poll_interval") else QSpinBox()
            spin.setRange(low, high)
            spin.setValue(default)
            self.inputs[key] = spin
            form.addWidget(QLabel(label), i // 2, (i % 2) * 2)
            form.addWidget(spin, i // 2, (i % 2) * 2 + 1)
        layout.addWidget(group)
        actions = QHBoxLayout()
        actions.addWidget(button("Ayarları kaydet", self.save))
        actions.addWidget(button("Görsel akışları düzenle", self.edit_workflows))
        actions.addWidget(button("Raporu CSV al", self.export))
        actions.addWidget(button("Profili kaydet", owner.export_profile))
        actions.addWidget(button("Profil yükle", owner.import_profile))
        layout.addLayout(actions)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        self.log.setMinimumHeight(160)
        self.log.setPlaceholderText("Oturum başladığında olaylar burada görünür.")
        layout.addWidget(self.log)
        self.resources = QLabel("")
        layout.addWidget(self.resources)

    def reload(self):
        cfg = self.owner.config.get("operations", DEFAULT_OPERATIONS)
        for key, widget in self.inputs.items():
            widget.setValue(cfg.get(key, DEFAULT_OPERATIONS[key]))

    def save(self):
        if self.owner.bots:
            QMessageBox.information(self, "Oturum çalışıyor", "Ayarları değiştirmek için oturumları durdur.")
            return
        cfg = self.owner.config.setdefault("operations", deepcopy(DEFAULT_OPERATIONS))
        cfg.update({key: widget.value() for key, widget in self.inputs.items()})
        self.owner.save_config()
        self.log.appendPlainText("Oturum ayarları kaydedildi.")

    def edit_workflows(self):
        if self.owner.bots:
            QMessageBox.information(self, "Oturum çalışıyor", "Akış düzenlemek için oturumları durdur.")
            return
        WorkflowEditor(self.owner).exec()

    def pause(self, index):
        bot = self.owner.bots.get(index)
        if bot:
            bot.paused = not bot.paused

    def stop(self, index):
        bot = self.owner.bots.get(index)
        if bot:
            bot.stop()

    def refresh(self):
        from utils import input_lock
        self.rows = []
        for i in range(8):
            bot = self.owner.bots.get(i)
            if bot and hasattr(bot, "metrics"):
                bot.service_limits()
                row = bot.metrics.snapshot(bot.total_games, bot.bait_counter)
                if bot.paused:
                    row["state"] = "Bekletildi"
                self.history[i] = row
            row = self.history.get(i, {"client": i + 1, "state": "Hazır", "rounds": 0, "rounds_per_hour": 0,
                                       "bait_estimate": 0, "errors": 0, "recoveries": 0})
            self.rows.append(dict(row))
            for j, key in enumerate(("state", "rounds", "rounds_per_hour", "bait_estimate", "errors", "recoveries"), 1):
                item = QTableWidgetItem(str(row[key]))
                item.setToolTip(str(row.get("message", "")))
                self.table.setItem(i, j, item)
            for col in (7, 8):
                self.table.cellWidget(i, col).setEnabled(bot is not None)
        snapshot = input_lock.snapshot()
        count = sum(x["acquisitions"] for x in snapshot["threads"].values())
        wait = sum(x["wait_seconds"] for x in snapshot["threads"].values())
        self.summary.setText(f"{len(self.owner.bots)}/8 oturum  ·  Giriş kuyruğu: {snapshot['waiting']}  ·  Ortalama bekleme: {1000 * wait / max(1, count):.1f} ms")
        try:
            import psutil
            ram = psutil.virtual_memory()
            self.resources.setText(f"Bilgisayar CPU: %{psutil.cpu_percent():.0f}    RAM: {ram.used / 2**30:.1f}/{ram.total / 2**30:.1f} GB")
        except ImportError:
            self.resources.setText("Kaynak ölçümü için psutil kurulmalı.")

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Oturum raporu", "oturum-raporu.csv", "CSV (*.csv)")
        if not path:
            return
        fields = ["client", "state", "rounds", "rounds_per_hour", "bait_estimate", "elapsed_seconds", "idle_seconds", "errors", "recoveries", "crates", "message"]
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for row in self.rows:
                    # Spreadsheet-formula injection protection for game/status text.
                    clean = {k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v) for k, v in row.items()}
                    writer.writerow(clean)
        except OSError as exc:
            QMessageBox.warning(self, "Rapor kaydedilemedi", str(exc))
