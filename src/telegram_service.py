"""Telegram API access. Never expose tokens or raw network exceptions."""
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class TelegramError(ValueError):
    pass


def validate_token(token):
    token = token.strip()
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{20,}", token):
        raise TelegramError("Bot token biçimi geçersiz. BotFather'dan aldığınız token'ı kontrol edin.")
    return token


def validate_chat(chat):
    chat = str(chat).strip()
    if not re.fullmatch(r"-?[1-9]\d*", chat):
        raise TelegramError("Sohbet kimliği sayısal olmalıdır.")
    return chat


def api_call(token, method, payload=None):
    token = validate_token(token)
    if method not in {"getMe", "getUpdates", "sendMessage"}:
        raise TelegramError("Desteklenmeyen işlem.")
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=12) as response:
            result = json.loads(response.read(2_000_000))
    except HTTPError as exc:
        messages = {401: "Token geçersiz veya iptal edilmiş.",
                    403: "Bot engellenmiş veya bu sohbete erişemiyor.",
                    409: "Bot başka bir uygulamada veya webhook ile kullanılıyor.",
                    429: "Çok fazla istek gönderildi. Bir süre sonra tekrar deneyin."}
        raise TelegramError(messages.get(exc.code, "Telegram isteği reddetti. Sohbet kimliğini ve /start adımını kontrol edin.")) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise TelegramError("Telegram'a bağlanılamadı. İnternet bağlantısını kontrol edin.") from None
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise TelegramError("Telegram işlemi tamamlayamadı.")
    return result.get("result")


def private_chats(updates):
    """Offer all observed private chats; never silently choose a recipient."""
    chats = {}
    for update in updates or []:
        chat = update.get("message", {}).get("chat", {})
        if chat.get("type") == "private" and isinstance(chat.get("id"), int):
            chats[str(chat["id"])] = chat.get("first_name", "Özel sohbet")
    return chats


def perform(token, action, chat=""):
    if action == "check":
        bot = api_call(token, "getMe")
        return "Bağlantı başarılı: @" + bot.get("username", "bot")
    if action == "chats":
        return private_chats(api_call(token, "getUpdates", {"timeout": 0, "limit": 100}))
    if action == "test":
        api_call(token, "sendMessage", {"chat_id": validate_chat(chat),
                 "text": "Demirware Fish Bot Metin2 — Telegram bağlantı testi başarılı."})
        return "Test mesajı gönderildi. Telegram'ı kontrol edin."
    raise TelegramError("Desteklenmeyen işlem.")
