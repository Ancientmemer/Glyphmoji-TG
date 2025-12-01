# app.py
# Telegram GlyphMoji bot (Flask + python-telegram-bot v13)
import os
import json
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Emoji Cipher mapping (from your chart) ----------
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

# ---------- Unicode cipher (global): uses \uXXXX escaping ----------
CHART_UNICODE = {
    "a": "Ⓐ",
    "b": "Ⓑ",
    "c": "Ⓒ",
    "d": "Ⓓ",
    "e": "Ⓔ",
    "f": "Ⓕ",
    "g": "Ⓖ",
    "h": "Ⓗ",
    "i": "Ⓘ",
    "j": "Ⓙ",
    "k": "Ⓚ",
    "l": "Ⓛ",
    "m": "Ⓜ",
    "n": "Ⓝ",
    "o": "Ⓞ",
    "p": "Ⓟ",
    "q": "Ⓠ",
    "r": "Ⓡ",
    "s": "Ⓢ",
    "t": "Ⓣ",
    "u": "Ⓤ",
    "v": "Ⓥ",
    "w": "Ⓦ",
    "x": "Ⓧ",
    "y": "Ⓨ",
    "z": "Ⓩ",
    " ": "␣",   # visible space symbol (optional)
}
REV_UNICODE = {v: k for k, v in CHART_UNICODE.items()}

# ---------- Modes persistence ----------
MODES_FILE = "modes.json"  # chat_id -> "emoji" or "unicode"

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

# ---------- Emoji encode/decode ----------
def encode_emoji_text(text: str) -> str:
    out = []
    for ch in text:
        mapped = CHART_EMOJI.get(ch) or CHART_EMOJI.get(ch.lower())
        out.append(mapped if mapped is not None else ch)
    return "".join(out)

def decode_emoji_text(glyphs: str) -> str:
    # Greedy matching over keys sorted by length (handles multi-char emoji tokens)
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

# ---------- Unicode encode/decode (\uXXXX style) ----------
def unicode_encode(text: str) -> str:
    parts = []
    for ch in text:
        code = ord(ch)
        parts.append(f"\\u{code:04x}")
    return " ".join(parts)

def unicode_decode(text: str) -> str:
    parts = text.split()
    out = []
    for p in parts:
        if p.startswith("\\u") and len(p) >= 4+2:  # \uXXXX minimal
            hexpart = p[2:]
            try:
                code = int(hexpart, 16)
                out.append(chr(code))
            except Exception:
                out.append(p)
        else:
            out.append(p)
    return "".join(out)

# ---------- Top-level encode/decode dispatcher ----------
def encode_text_with_mode(text: str, mode: str) -> str:
    if mode == "emoji":
        return encode_emoji_text(text)
    elif mode == "unicode":
        # Unicode mode on site uses \uXXXX escapes
        return unicode_encode(text)
    else:
        return text

def decode_text_with_mode(text: str, mode: str) -> str:
    if mode == "emoji":
        return decode_emoji_text(text)
    elif mode == "unicode":
        return unicode_decode(text)
    else:
        return text

# ---------- Telegram + Flask setup ----------
TOKEN = os.environ.get("TG_TOKEN")
if not TOKEN:
    raise RuntimeError("TG_TOKEN environment variable is required")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# create dispatcher (no persistence, workers=0 because Flask handles incoming updates)
dispatcher = Dispatcher(bot, None, workers=0)

# ---------- Handlers ----------
def start(update, context):
    chat_id = update.effective_chat.id
    mode = get_mode_for_chat(chat_id)
    update.message.reply_text(
        f"GlyphMoji bot ready. Current mode: *{mode}*\n"
        "Use /encode TEXT or /decode GLYPHS\n"
        "Use /changemod [emoji|unicode] to switch modes, or /changemod to toggle.",
        parse_mode="Markdown"
    )

def help_cmd(update, context):
    update.message.reply_text(
        "/start - Welcome\n"
        "/help - This message\n"
        "/mode - Show current mode\n"
        "/changemod [emoji|unicode] - Change or toggle mode\n"
        "/encode TEXT - Encode to current mode\n"
        "/decode GLYPHS - Decode from current mode\n\n"
        "Send plain text message to auto-encode."
    )

def mode_cmd(update, context):
    chat_id = update.effective_chat.id
    mode = get_mode_for_chat(chat_id)
    update.message.reply_text(f"Current mode for this chat: *{mode}*", parse_mode="Markdown")

def changemod_cmd(update, context):
    chat_id = update.effective_chat.id
    args = context.args
    current = get_mode_for_chat(chat_id)
    if args:
        arg = args[0].lower()
        if arg not in ("emoji", "unicode"):
            update.message.reply_text("Invalid mode. Use `emoji` or `unicode`.", parse_mode="Markdown")
            return
        set_mode_for_chat(chat_id, arg)
        update.message.reply_text(f"Mode set to *{arg}*.", parse_mode="Markdown")
    else:
        new = "unicode" if current == "emoji" else "emoji"
        set_mode_for_chat(chat_id, new)
        update.message.reply_text(f"Toggled mode: *{new}*.", parse_mode="Markdown")

def encode_cmd(update, context):
    chat_id = update.effective_chat.id
    mode = get_mode_for_chat(chat_id)
    txt = " ".join(context.args) if context.args else ""
    if not txt:
        update.message.reply_text("Usage: /encode your text here")
        return
    res = encode_text_with_mode(txt, mode)
    update.message.reply_text(res)

def decode_cmd(update, context):
    chat_id = update.effective_chat.id
    mode = get_mode_for_chat(chat_id)
    txt = " ".join(context.args) if context.args else ""
    if not txt:
        update.message.reply_text("Usage: /decode <glyphs>")
        return
    res = decode_text_with_mode(txt, mode)
    update.message.reply_text(res)

def plain_message(update, context):
    chat_id = update.effective_chat.id
    mode = get_mode_for_chat(chat_id)
    t = update.message.text or ""
    # default: encode incoming plain text
    update.message.reply_text(encode_text_with_mode(t, mode))

# register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_cmd))
dispatcher.add_handler(CommandHandler("mode", mode_cmd))
dispatcher.add_handler(CommandHandler("changemod", changemod_cmd))
dispatcher.add_handler(CommandHandler("encode", encode_cmd))
dispatcher.add_handler(CommandHandler("decode", decode_cmd))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, plain_message))

# ---------- Health check + webhook route ----------
@app.route("/healthz")
def health():
    return "ok", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
