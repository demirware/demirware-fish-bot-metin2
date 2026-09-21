"""Pure command authorization, scheduling and report helpers."""
import math
import time


COMMANDS = {"/start", "/stop", "/karakterat", "/kanal", "/durum", "/istatistik", "/pm", "/help"}


def command_from_update(update, owner_id, username, enabled_at, now=None):
    """Only fresh, original messages from the configured private-chat owner."""
    message = update.get("message", {})
    chat, sender = message.get("chat", {}), message.get("from", {})
    now = time.time() if now is None else now
    date = message.get("date", 0)
    if (chat.get("type") != "private" or str(chat.get("id")) != str(owner_id)
            or str(sender.get("id")) != str(owner_id) or sender.get("is_bot")
            or message.get("forward_origin") or message.get("forward_date")
            or not isinstance(date, (int, float)) or date <= enabled_at
            or now - date > 60 or date > now + 5):
        return None
    text = message.get("text", "")
    if not isinstance(text, str) or not text.startswith("/"):
        return None
    pieces = text.split(maxsplit=1)
    name, _, target = pieces[0].partition("@")
    if target and target.lower() != username.lower():
        return None
    if name not in COMMANDS:
        return ("/help", "")
    return name, pieces[1][:500] if len(pieces) > 1 else ""


class Countdown:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.deadline = None
        self.seconds = 0

    def arm(self, minutes):
        minutes = float(str(minutes).replace(",", "."))
        if not math.isfinite(minutes) or not 0 < minutes <= 10080:
            raise ValueError("Süre 0'dan büyük, en fazla 10080 dakika olmalıdır.")
        self.seconds = minutes * 60
        self.deadline = self.clock() + self.seconds

    def cancel(self):
        self.deadline = None

    def remaining(self):
        return max(0, self.deadline - self.clock()) if self.deadline is not None else None

    def due(self):
        if self.deadline is not None and self.clock() >= self.deadline:
            self.deadline = None  # one shot, even if the next action fails
            return True
        return False


def format_duration(seconds):
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def stats_report(elapsed, records, active, listener_seconds):
    lines = ["Demirware durum", f"Telegram açık: {format_duration(listener_seconds)}",
             f"Balık oturumu: {format_duration(elapsed)}", f"Aktif istemci: {active}"]
    lines.extend([
        f"Kullanılan yem (tahmini): {sum(r.get('bait_used', 0) for r in records)}",
        f"Kalan yem (tahmini): {sum(max(0, r.get('bait', 0)) for r in records)}",
        f"Tamamlanan tur: {sum(r.get('games', 0) for r in records)}",
    ])
    if records and all(r.get("fish_measured") for r in records):
        lines.append(f"Tutulan balık (görsel doğrulama): {sum(r.get('fish', 0) for r in records)}")
    else:
        lines.append("Tutulan balık: ölçülmüyor / eksik kapsam; başarı görseli gerekli.")
    return "\n".join(lines)
