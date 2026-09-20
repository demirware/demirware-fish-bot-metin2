"""Eight-client session layer around the upstream fishing implementation."""
from copy import deepcopy
import threading
import time

import numpy as np
from mss import mss

from fishing_bot import FishingBot
from session_runtime import DEFAULT_OPERATIONS, SessionMetrics
from utils import input_lock
from visual_workflow import DesktopWorkflowPort, WorkflowError, WorkflowRunner
from window_manager import WindowActivationError


class GuardedInput:
    """Check cancellation between input events, including inventory sequences."""
    def __init__(self, wrapped, bot):
        self.wrapped, self.bot = wrapped, bot

    def __getattr__(self, name):
        value = getattr(self.wrapped, name)
        if name not in {"move_to", "click", "mouse_down", "key_press", "tap_key"}:
            return value  # Releases must remain possible after cancellation.
        def guarded(*args, **kwargs):
            if self.bot._halt.is_set() or not self.bot.running or self.bot.paused:
                raise WorkflowError("Giriş iptal edildi")
            self.bot.window_manager.activate_window()
            return value(*args, **kwargs)
        return guarded


class ManagedFishingBot(FishingBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operations = deepcopy(DEFAULT_OPERATIONS)
        self.operations.update(deepcopy(self.config.get("operations", {})))
        self.metrics = SessionMetrics(self.bot_id)
        self._halt = threading.Event()
        self.human = GuardedInput(self.human, self)
        self._managed_active = False
        self._round_deadline = None
        self._session_started = None
        self._jigsaw_deadline = None
        self._last_jigsaw_round = -1
        self._recovery_count = 0
        self._port = DesktopWorkflowPort(self, self._halt.is_set)

    def _status(self, message, state=None, error=False):
        self.metrics.update(state=state, message=message, error=error)
        if self.on_status_update:
            self.on_status_update(f"[W{self.bot_id + 1}] {message}")

    def _notify_bot_stop_once(self):
        # A recovery is part of the same session; only its final exit reaches Qt.
        if not self._managed_active:
            super()._notify_bot_stop_once()

    def _capture(self, area):
        with input_lock:
            if self._halt.is_set():
                raise WorkflowError("Oturum durduruldu")
            try:
                self.window_manager.activate_window()
                left, top, width, height = self.window_manager.get_window_rect()
                if area == "inventory":
                    left += width - self._inventory_width
                    top += self._inventory_y_offset
                    width, height = self._inventory_width, height - self._inventory_y_offset - 30
                elif area == "region" and self.region:
                    left += self.region.left
                    top += self.region.top
                    width, height = self.region.width, self.region.height
                if min(width, height) <= 0:
                    raise WorkflowError("Pencere görüntü boyutu geçersiz")
                if self.sct is None:
                    self.sct = mss()
                shot = self.sct.grab(dict(left=left, top=top, width=width, height=height))
                frame = np.ascontiguousarray(np.asarray(shot, dtype=np.uint8)[:, :, :3])
                if frame.size == 0 or int(frame.max()) == 0:
                    raise WorkflowError("Siyah/boş pencere görüntüsü; işlem kesildi")
                return frame
            except Exception as exc:
                self._status(str(exc), "Görüntü hatası", error=True)
                self._stop_bot("capture_error")
                raise

    def capture_full_window(self):
        return self._capture("full")

    def capture_inventory_area(self):
        return self._capture("inventory")

    def capture_screen(self):
        return self._capture("region")

    def adjust_bait_tier(self):
        # Missing minigame is not evidence that 200 bait disappeared.
        self._stop_bot("detection_failed", "Balık ekranı doğrulanamadı; yem tahmini değiştirilmedi")

    def wait_for_minigame_window(self, timeout=6.0):
        self.metrics.update(state="Balık bekleniyor")
        result = super().wait_for_minigame_window(timeout)
        if result:
            self._round_deadline = time.monotonic() + self.operations["minigame_timeout"]
            self.metrics.update(state="Balık tutuyor", progress=True)
        elif self.running:
            self.region_auto_calibrated = False
            self.region = None
            if self.consecutive_failures + 1 >= self.operations["max_detection_failures"]:
                self.metrics.update(error=True)
                self._stop_bot("detection_failed", "Balık ekranı tekrar bulunamadı; oturum kesildi")
        return result

    def atomic_capture_and_click(self):
        self.service_limits()
        if not self.running or self._halt.is_set():
            raise WorkflowError("Oturum durduruldu")
        if self._round_deadline and time.monotonic() > self._round_deadline:
            self.metrics.update(error=True)
            self._stop_bot("minigame_timeout", "Mini oyun süresi aşıldı")
            raise WorkflowError("Mini oyun süresi aşıldı")
        # Bound idle CPU usage. Actual throughput is reported, not inferred from FPS.
        self._halt.wait(self.operations["poll_interval"])
        result = super().atomic_capture_and_click()
        if not result[0]:
            self._round_deadline = None
            self.metrics.update(progress=True)
        return result

    def bait_and_cast(self):
        self.service_limits()
        if self._halt.is_set() or not self.running or self.paused:
            raise WorkflowError("Oturum durduruldu veya bekletildi")
        self.metrics.update(state="Olta atılıyor")
        # Revalidate immediately before the existing input sequence.
        with input_lock:
            self.window_manager.activate_window()
            super().bait_and_cast()

    def service_limits(self):
        minutes = self.operations.get("session_minutes", 0)
        if minutes and self._session_started is not None and time.monotonic() - self._session_started >= minutes * 60:
            self._halt.set()
            self._stop_bot("session_limit", "Planlanan oturum süresi tamamlandı")
        child = getattr(self, "_jigsaw_bot", None)
        if child:
            child.paused = self.paused
            if self._halt.is_set() or (self._jigsaw_deadline and time.monotonic() >= self._jigsaw_deadline):
                child.stop()

    def _run_recipe(self, name):
        recipe = self.operations.get("workflows", {}).get(name)
        if not recipe or not recipe.get("enabled", False):
            raise WorkflowError(f"{name} akışı yapılandırılmamış")
        self._status(f"{name} akışı başladı", "Otomasyon")
        try:
            WorkflowRunner(self._port, self._halt.is_set, lambda: self.paused,
                           status=lambda message: self._status(message)).run(recipe)
        except Exception:
            self._halt.set()
            self._stop_bot("automation_error")
            raise
        self.metrics.update(progress=True)

    def handle_caught_item(self):
        super().handle_caught_item()
        self.metrics.update(progress=True)
        interval = self.operations.get("jigsaw_every_rounds", 0)
        if not self.running or not interval or not self.total_games or self.total_games % interval or self.total_games == self._last_jigsaw_round:
            return
        self._last_jigsaw_round = self.total_games
        from jigsaw_bot import JigsawBot
        if not self.config.get("jigsaw_grid_bounds") or not self.config.get("confirm_button_pos"):
            self._halt.set()
            self._stop_bot("automation_error")
            raise WorkflowError("Otomatik yapboz için tahta ve onay konumları gerekli")
        self._run_recipe("jigsaw_open")
        config = deepcopy(self.config)
        config["external_pause_control"] = True
        child = JigsawBot(self.window_manager, config, bot_id=self.bot_id,
                          on_status_update=self.on_status_update)
        child.human = GuardedInput(child.human, self)
        # Reuse the same focused capture and desktop queue as fishing.
        child.capture_full_window = self.capture_full_window
        child.capture_inventory_area = self.capture_inventory_area
        self._jigsaw_bot = child
        self._jigsaw_deadline = time.monotonic() + self.operations["jigsaw_max_seconds"]
        self.metrics.update(state="Yapboz")
        try:
            child.start()
            self.metrics.update(crates=child.crates_completed, progress=True)
            if time.monotonic() >= self._jigsaw_deadline:
                self._halt.set()
                self._stop_bot("automation_error")
                raise WorkflowError("Yapboz süresi doldu; otomatik devam iptal edildi")
        finally:
            if child.sct:
                child.sct.close()
            child.mouse_backend.close()
            self._jigsaw_bot = None
            self._jigsaw_deadline = None
        self._run_recipe("jigsaw_close")
        self.region_auto_calibrated = False
        self.region = None
        self.metrics.update(state="Balık tutuyor")

    def start(self):
        self._managed_active = True
        self._session_started = time.monotonic()
        try:
            delay = self.bot_id * self.operations["start_spacing_seconds"]
            self.metrics.update(state="Başlatma sırası")
            if self._halt.wait(delay):
                return
            while not self._halt.is_set():
                if self.bait_counter <= 0:
                    self.stop_reason = self.STOP_BAIT_DEPLETED
                else:
                    self.metrics.update(state="Başlıyor")
                    super().start()
                if self._halt.is_set():
                    break
                recipe_name = {self.STOP_BAIT_DEPLETED: "restock", self.STOP_INVENTORY_FULL: "cook",
                               "detection_failed": "reconnect"}.get(self.stop_reason)
                recipe = self.operations.get("workflows", {}).get(recipe_name, {})
                if not recipe_name or not recipe.get("enabled") or self._recovery_count >= self.operations["max_recoveries"]:
                    break
                self._recovery_count += 1
                self.metrics.update(state="İşlem bekleniyor")
                if self._halt.wait(self.operations["recovery_cooldown"]):
                    break
                self.running = True
                self._run_recipe(recipe_name)
                if recipe_name == "restock":
                    # Estimate only; final recipe image must verify replenished hotbar.
                    self.bait_counter = len(self.bait_keys) * self.config.get("bait_quantity", 200)
                    if self.on_bait_update:
                        self.on_bait_update(self.bot_id, self.bait_counter)
                self.metrics.update(recovery=True)
                self.region_auto_calibrated = False
                self.region = None
                self.consecutive_failures = 0
                self.stop_reason = None
        except Exception as exc:
            self.stop_reason = "automation_error"
            self._status(str(exc), "Hata", error=True)
        finally:
            self.running = False
            self._managed_active = False
            self.metrics.update(state="Durduruldu", message=self.stop_reason or "Tamamlandı")
            self.metrics.finish()
            try:
                if self.sct:
                    self.sct.close()
                self.mouse_backend.close()
            finally:
                self._stop_notified = False
                self._notify_bot_stop_once()

    def stop(self):
        self._halt.set()
        super().stop()
