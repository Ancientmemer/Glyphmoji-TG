# app.py
# Full GlyphMoji Telegram bot — EXPOSED_URL webhook method
# Features:
# - Emoji cipher + Unicode (\uXXXX) mode
# - /start, /help, /mode, /changemod, /encode, /decode
# - plain text auto-encode
# - per-chat mode persistence (modes.json)
# - /set_webhook (uses EXPOSED_URL)
# - /webhook receiver and /healthz for Koyeb
# Uses: pyTelegramBotAPI (telebot) + Flask

import os
import json
import logging
import requests
from flask import Flask, request, jsonify
import telebot

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("glyphmoji")

# ---------- Env / Bot setup ----------
TOKEN = os.getenv("TG_TOKEN")
EXPOSED_URL = os.getenv("EXPOSED_URL")  # e.g. https://your-app.koyeb.app

if not TOKEN:
    raise RuntimeError("TG_TOKEN environment variable is required")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ---------- Emoji mapping (chart) ----------
CHART_EMOJI = {
    "a": "😀",   #01
    "b": "🐒",   #02
    "c": "🍌",   #03
    "d": "🍩",   #04
    "e": "🥚",   #05
    "f": "🍟",   #06
    "g": "🦍",   #07
    "h": "🏡",   #08
    "i": "🍦",   #09
    "j": "🕹️",  #10
    "k": "🔑",   #11
    "l": "🍋",   #12
    "m": "🌝",   #13
    "n": "🎶",   #14
    "o": "🍊",   #15
    "p": "🥞",   #16
    "q": "❓",   #17
    "r": "🌈",   #18
    "s": "⭐",   #19
    "t": "🌴",   #20
    "u": "☂️",  #21
    "v": "🌋",   #22
    "w": "🌊",   #23
    "x": "❌",   #24
    "y": "🍸",   #25
    "z": "⚡",   #26
    " ": "⬜",    #00 Space
}
REV_EMOJI = {v: k for k, v in CHART_EMOJI.items()}

# ---------- Unicode mapping (circled capitals) ----------
CHART_UNICODE = {
    "a": "Ⓐ","b": "Ⓑ","c": "Ⓒ","d": "Ⓓ","e": "Ⓔ","f": "Ⓕ",
    "g": "Ⓖ","h": "Ⓗ","i": "Ⓘ","j": "Ⓙ","k": "Ⓚ","l": "Ⓛ",
    "m": "Ⓜ","n": "Ⓝ","o": "Ⓞ","p": "Ⓟ","q": "Ⓠ","r": "Ⓡ",
    "s": "Ⓢ","t": "Ⓣ","u": "Ⓤ","v": "Ⓥ","w": "Ⓦ","x": "Ⓧ",
    "y": "Ⓨ","z": "Ⓩ"," ": "␣"
}
REV_UNICODE = {v: k for k, v in CHART_UNICODE.items()}

# ---------- Modes persistence ----------
MODES_FILE = "modes.json"

def load_modes():
    try:
        with open(MODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_modes(m):
    try:
        with open(MODES_FILE, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Failed to save modes: %s", e)

modes = load_modes()

def get_mode_for_chat(chat_id: int) -> str:
    return modes.get(str(chat_id), "emoji")

def set_mode_for_chat(chat_id: int, mode: str):
    modes[str(chat_id)] = mode
    save_modes(modes)

# ---------- Encoding / Decoding helpers ----------
def encode_emoji_text(text: str) -> str:
    out = []
    for ch in text:
        mapped = CHART_EMOJI.get(ch) or CHART_EMOJI.get(ch.lower())
        out.append(mapped if mapped is not None else ch)
    return "".join(out)

def decode_emoji_text(glyphs: str) -> str:
    out = []
    i = 0
    keys = sorted(REV_EMOJI.keys(), key=len, reverse=True)
    max_len = len(keys[0]) if keys else 1
    while i < len(glyphs):
        matched = False
        for L in range(max_len, 0, -1):
            tok = glyphs[i:i+L]
            if tok in REV_EMOJI:
                out.append(REV_EMOJI[tok])
                i += L
                matched = True
                break
        if not matched:
            out.append(glyphs[i])
            i += 1
    return "".join(out)

def unicode_encode(text: str) -> str:
    parts = []
    for ch in text:
        parts.append(f"\\u{ord(ch):04x}")
    return " ".join(parts)

def unicode_decode(text: str) -> str:
    parts = text.split()
    out = []
    for p in parts:
        if p.startswith("\\u"):
            try:
                out.append(chr(int(p[2:], 16)))
            except Exception:
                out.append(p)
        else:
            out.append(p)
    return "".join(out)

def encode_text_with_mode(text: str, mode: str) -> str:
    if mode == "emoji":
        return encode_emoji_text(text)
    elif mode == "unicode":
        return unicode_encode(text)
    return text

def decode_text_with_mode(text: str, mode: str) -> str:
    if mode == "emoji":
        return decode_emoji_text(text)
    elif mode == "unicode":
        return unicode_decode(text)
    return text

# ---------- Bot command handlers (telebot) ----------
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    mode = get_mode_for_chat(chat_id)
    text = (f"GlyphMoji bot ready. Current mode: <b>{mode}</b>\n\n"
            "Commands:\n"
            "/start - welcome\n"
            "/help - this message\n"
            "/mode - show current mode\n"
            "/changemod [emoji|unicode] - change or toggle mode\n"
            "/encode <text> - encode\n"
            "/decode <glyphs> - decode\n\n"
            "Send plain text to auto-encode.")
    bot.send_message(chat_id, text)

@bot.message_handler(commands=['help'])
def handle_help(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, (
        "/start - Welcome\n"
        "/help - This message\n"
        "/mode - Show current mode\n"
        "/changemod [emoji|unicode] - Change/toggle mode\n"
        "/encode TEXT - Encode to current mode\n"
        "/decode GLYPHS - Decode from current mode\n\nSend plain text to auto-encode."
    ))

@bot.message_handler(commands=['mode'])
def handle_mode(message):
    chat_id = message.chat.id
    mode = get_mode_for_chat(chat_id)
    bot.send_message(chat_id, f"Current mode for this chat: <b>{mode}</b>")

@bot.message_handler(commands=['changemod'])
def handle_changemod(message):
    chat_id = message.chat.id
    parts = message.text.split()
    current = get_mode_for_chat(chat_id)
    if len(parts) > 1:
        arg = parts[1].lower()
        if arg not in ("emoji", "unicode"):
            bot.send_message(chat_id, "Invalid mode. Use 'emoji' or 'unicode'.")
            return
        set_mode_for_chat(chat_id, arg)
        bot.send_message(chat_id, f"Mode set to <b>{arg}</b>")
    else:
        new = "unicode" if current == "emoji" else "emoji"
        set_mode_for_chat(chat_id, new)
        bot.send_message(chat_id, f"Toggled mode: <b>{new}</b>")

@bot.message_handler(commands=['encode'])
def handle_encode(message):
    chat_id = message.chat.id
    txt = message.text.partition(' ')[2].strip()
    if not txt:
        bot.send_message(chat_id, "Usage: /encode your text here")
        return
    mode = get_mode_for_chat(chat_id)
    res = encode_text_with_mode(txt, mode)
    bot.send_message(chat_id, res)

@bot.message_handler(commands=['decode'])
def handle_decode(message):
    chat_id = message.chat.id
    txt = message.text.partition(' ')[2].strip()
    if not txt:
        bot.send_message(chat_id, "Usage: /decode <glyphs>")
        return
    mode = get_mode_for_chat(chat_id)
    res = decode_text_with_mode(txt, mode)
    bot.send_message(chat_id, res)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_plain_text(message):
    chat_id = message.chat.id
    txt = message.text or ""
    mode = get_mode_for_chat(chat_id)
    res = encode_text_with_mode(txt, mode)
    bot.send_message(chat_id, res)

# ---------- Flask routes: webhook, set_webhook, healthz ----------
@app.post("/webhook")
def webhook():
    try:
        update_json = request.get_json(force=True)
        update = telebot.types.Update.de_json(update_json)
        bot.process_new_updates([update])
    except Exception as e:
        logger.exception("Error processing update: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True})

@app.get("/set_webhook")
def set_webhook():
    # Use EXPOSED_URL method (no token in path)
    token = TOKEN
    exposed = os.getenv("EXPOSED_URL")
    if not exposed:
        return jsonify({"error": "EXPOSED_URL env not set"}), 500

    webhook_url = f"{exposed.rstrip('/')}/webhook"
    telegram_api = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        r = requests.post(telegram_api, data={"url": webhook_url})
        logger.info("set_webhook response: %s", r.text)
        return (r.json(), r.status_code) if r.headers.get("content-type","").startswith("application/json") else (r.text, r.status_code)
    except Exception as e:
        logger.exception("Failed to set webhook: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/healthz")
def health():
    return jsonify({"status": "ok"}), 200

# ---------- Start (flask) ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info("Starting Flask on port %s", port)
    app.run(host="0.0.0.0", port=port)
