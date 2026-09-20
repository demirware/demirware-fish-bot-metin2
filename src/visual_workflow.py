"""Bounded, declarative workflows. No eval, shell commands or account secrets."""
from pathlib import Path
import math
import time


class WorkflowError(RuntimeError):
    pass


def validate_workflow(recipe):
    if not isinstance(recipe, dict):
        raise ValueError("Akış bir JSON nesnesi olmalı")
    steps = recipe.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 40:
        raise ValueError("Akış 1–40 adım içermeli")
    if not isinstance(steps[-1], dict) or steps[-1].get("action") != "expect":
        raise ValueError("Son adım sonucu doğrulayan 'expect' olmalı")
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("Her adım bir nesne olmalı")
        action = step.get("action")
        if action not in {"expect", "click", "right_click", "key", "drag"}:
            raise ValueError(f"Desteklenmeyen adım: {action}")
        for field in ("template", "target") if action == "drag" else ("template",):
            value = step.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                raise ValueError(f"{action}: {field} görseli gerekli")
        if action == "key" and step.get("key") not in {
            "space", "enter", "esc", "1", "2", "3", "4", "f1", "f2", "f3", "f4", "i"
        }:
            raise ValueError("Desteklenmeyen tuş")
        for field, default, low, high in (("timeout", 8, 0.1, 60), ("threshold", .92, .8, 1),
                                          ("settle", .2, 0, 5)):
            value = step.get(field, default)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{field}: {low}–{high} aralığında olmalı")
    return recipe


class WorkflowRunner:
    """Port.attempt must focus, capture, match and act under the desktop lock.

    Missing/ambiguous images are retried until timeout; mutations are never
    automatically repeated once the port confirms it sent the action.
    """
    def __init__(self, port, cancelled=lambda: False, paused=lambda: False,
                 clock=time.monotonic, sleep=time.sleep, status=lambda _: None):
        self.port, self.cancelled, self.paused = port, cancelled, paused
        self.clock, self.sleep, self.status = clock, sleep, status

    def run(self, recipe, max_seconds=180):
        validate_workflow(recipe)
        deadline = self.clock() + max_seconds
        for index, step in enumerate(recipe["steps"]):
            step_deadline = self.clock() + step.get("timeout", 8)
            self.status(f"Adım {index + 1}/{len(recipe['steps'])}: {step['action']}")
            while True:
                if self.cancelled():
                    raise WorkflowError("İşlem durduruldu")
                now = self.clock()
                if now >= deadline or now >= step_deadline:
                    raise WorkflowError(f"Adım {index + 1}: görsel doğrulanamadı veya süre doldu")
                if self.paused():
                    self.sleep(.05)
                    continue
                if self.port.attempt(step):
                    break
                self.sleep(.1)
            settle_end = self.clock() + step.get("settle", .2)
            while self.clock() < settle_end:
                if self.cancelled() or self.clock() >= deadline:
                    raise WorkflowError("İşlem durduruldu veya süre doldu")
                self.sleep(min(.05, settle_end - self.clock()))


class TemplateMatcher:
    def __init__(self):
        self._cache = {}

    def load(self, path):
        import cv2
        import numpy as np
        path = Path(path).resolve()
        key = (str(path), path.stat().st_mtime_ns)
        if key not in self._cache:
            template = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if template is None or min(template.shape[:2]) < 6 or float(template.std()) < 3:
                raise WorkflowError("Şablon okunamıyor, çok küçük veya ayırt edici değil")
            self._cache = {k: v for k, v in self._cache.items() if k[0] != key[0]}
            self._cache[key] = template
        return self._cache[key]

    def locate(self, frame, path, threshold=.92):
        import cv2
        template = self.load(path)
        h, w = template.shape[:2]
        if h > frame.shape[0] or w > frame.shape[1]:
            return None
        scores = cv2.matchTemplate(frame, template, cv2.TM_SQDIFF_NORMED)
        low, _, loc, _ = cv2.minMaxLoc(scores)
        if not math.isfinite(low) or 1 - low < threshold:
            return None
        # Reject a second equally good instance instead of clicking an arbitrary item.
        x, y = loc
        scores[max(0, y - h // 2):y + h // 2 + 1, max(0, x - w // 2):x + w // 2 + 1] = 1
        second = float(scores.min())
        if 1 - second >= threshold and second - low < .02:
            return None
        return x + w // 2, y + h // 2


class DesktopWorkflowPort:
    def __init__(self, bot, cancelled=lambda: False):
        self.bot = bot
        self.cancelled = cancelled
        self.matcher = TemplateMatcher()

    def attempt(self, step):
        from utils import input_lock
        from pynput.keyboard import Key
        with input_lock:
            if self.cancelled() or self.bot.paused:
                return False
            self.bot.window_manager.activate_window()
            frame = self.bot.capture_full_window()
            threshold = step.get("threshold", .92)
            position = self.matcher.locate(frame, step["template"], threshold)
            if position is None:
                return False
            action = step["action"]
            if action == "expect":
                return True
            target = None
            if action == "drag":
                target = self.matcher.locate(frame, step["target"], threshold)
                if target is None:
                    return False
            if self.cancelled() or self.bot.paused:
                return False
            self.bot.window_manager.activate_window()
            left, top, _, _ = self.bot.window_manager.get_window_rect()
            if action == "key":
                key = step["key"]
                self.bot.human.tap_key(getattr(Key, key, key), hold=.03)
            else:
                self.bot.human.move_to(left + position[0], top + position[1])
                if action == "drag":
                    try:
                        self.bot.mouse_backend.mouse_down()
                        self.bot.human.move_to(left + target[0], top + target[1])
                    finally:
                        self.bot.mouse_backend.mouse_up()
                else:
                    self.bot.human.click(button="right" if action == "right_click" else "left")
            return True
