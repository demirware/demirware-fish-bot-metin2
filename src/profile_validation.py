"""Validate portable profiles before mutating live application state."""
from copy import deepcopy
import math
from visual_workflow import validate_workflow


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name}: {low}–{high} aralığında sayı gerekli")


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("Profil bir JSON nesnesi olmalı")
    profile = deepcopy(profile)
    for key, value in profile.items():
        if key.endswith("_pos") and value is not None:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError(f"{key}: iki koordinat gerekli")
            for coordinate in value:
                number(coordinate, key, 0, 32768)
        if key.startswith("timing_"):
            number(value, key, 0, 10)
    keys = profile.get("bait_keys", ["1"])
    if not isinstance(keys, list) or not 1 <= len(keys) <= 4 or any(k not in ["1", "2", "3", "4", "F1", "F2", "F3", "F4"] for k in keys) or len(set(keys)) != len(keys):
        raise ValueError("Yem tuşları geçersiz veya tekrarlı")
    number(profile.get("bait_quantity", 200), "bait_quantity", 1, 10000)
    if not isinstance(profile.get("bait_quantity", 200), int):
        raise ValueError("Yem miktarı tam sayı olmalı")
    actions = profile.get("fish_actions", {})
    if not isinstance(actions, dict) or any(v not in {"keep", "open", "drop", ""} for v in actions.values()):
        raise ValueError("Balık işlemleri geçersiz")
    ops = profile.get("operations", {})
    if not isinstance(ops, dict):
        raise ValueError("Oturum ayarları geçersiz")
    ranges = {"start_spacing_seconds": (0, 10), "session_minutes": (0, 1440),
              "poll_interval": (.01, 1), "minigame_timeout": (15, 120),
              "max_detection_failures": (1, 10), "max_recoveries": (0, 100),
              "recovery_cooldown": (1, 300), "jigsaw_every_rounds": (0, 1000),
              "jigsaw_max_seconds": (30, 600)}
    for key, limits in ranges.items():
        if key in ops:
            number(ops[key], key, *limits)
    for key in ("max_detection_failures", "max_recoveries", "jigsaw_every_rounds"):
        if key in ops and not isinstance(ops[key], int):
            raise ValueError(f"{key}: tam sayı gerekli")
    recipes = ops.get("workflows", {})
    if not isinstance(recipes, dict):
        raise ValueError("Akışlar bir nesne olmalı")
    for key, recipe in recipes.items():
        if key not in {"restock", "cook", "reconnect", "jigsaw_open", "jigsaw_close", "character_select", "channel_change"} or not isinstance(recipe, dict):
            raise ValueError("Akış adı veya içeriği geçersiz")
        if not isinstance(recipe.get("enabled", False), bool):
            raise ValueError("Akış etkinliği doğru/yanlış olmalı")
        if recipe.get("enabled") or recipe.get("steps"):
            validate_workflow(recipe)
    if ops.get("jigsaw_every_rounds", 0):
        if not all(recipes.get(key, {}).get("enabled") for key in ("jigsaw_open", "jigsaw_close")):
            raise ValueError("Otomatik yapboz için açılış ve dönüş akışları gerekli")
        if not profile.get("jigsaw_grid_bounds") or not profile.get("confirm_button_pos"):
            raise ValueError("Otomatik yapboz için tahta ve onay konumları gerekli")
    return profile
