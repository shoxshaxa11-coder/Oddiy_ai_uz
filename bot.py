import os
import logging
import requests
from urllib.parse import quote

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Sozlamalar (environment variables orqali) ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY")
POLLINATIONS_BASE = "https://gen.pollinations.ai"

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable topilmadi!")
if not POLLINATIONS_API_KEY:
    raise RuntimeError("POLLINATIONS_API_KEY environment variable topilmadi!")

# Foydalanuvchi holatini xotirada saqlash: {user_id: "text"/"image"/"video"}
user_mode = {}

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["💬 Matn (Chat)"],
        ["🎨 Rasm yaratish"],
        ["🎬 Video yaratish"],
        ["ℹ️ Yordam"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = None
    await update.message.reply_text(
        "Assalomu alaykum! 👋\nQuyidagi menyudan birini tanlang:",
        reply_markup=MAIN_MENU,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Yordam:\n\n"
        "💬 Matn — men bilan oddiy suhbat qiling\n"
        "🎨 Rasm yaratish — biror narsa yozing, men rasm chizib beraman\n"
        "🎬 Video yaratish — biror narsa yozing, men video yasab beraman "
        "(1-3 daqiqa vaqt olishi mumkin)\n\n"
        "Boshlash uchun /start buyrug'ini yuboring."
    )


async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💬 Matn (Chat)":
        user_mode[user_id] = "text"
        await update.message.reply_text("Matn rejimi yoqildi. Menga yozing, javob beraman.")
        return
    if text == "🎨 Rasm yaratish":
        user_mode[user_id] = "image"
        await update.message.reply_text("Qanday rasm chizishimni yozing (masalan: 'kosmosdagi mushuk').")
        return
    if text == "🎬 Video yaratish":
        user_mode[user_id] = "video"
        await update.message.reply_text(
            "Qanday video yasashimni yozing (masalan: 'dengiz to'lqinlari').\n"
            "⏳ Video tayyorlanishi 1-3 daqiqa davom etishi mumkin, sabr qiling."
        )
        return
    if text == "ℹ️ Yordam":
        await help_command(update, context)
        return

    # Menyudan tanlanmagan bo'lsa — foydalanuvchi rejimiga qarab ishlaymiz
    mode = user_mode.get(user_id)
    if mode == "image":
        await generate_image(update, context, text)
    elif mode == "video":
        await generate_video(update, context, text)
    else:
        await generate_text(update, context, text)


async def generate_text(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    await update.message.chat.send_action("typing")
    try:
        url = f"{POLLINATIONS_BASE}/text/{quote(prompt)}"
        resp = requests.get(url, params={"key": POLLINATIONS_API_KEY}, timeout=60)
        resp.raise_for_status()
        await update.message.reply_text(resp.text)
    except Exception as e:
        logger.exception("Matn generatsiyasida xatolik")
        await update.message.reply_text(f"⚠️ Xatolik yuz berdi: {e}")


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    await update.message.chat.send_action("upload_photo")
    try:
        url = f"{POLLINATIONS_BASE}/image/{quote(prompt)}"
        resp = requests.get(url, params={"key": POLLINATIONS_API_KEY}, timeout=120)
        resp.raise_for_status()
        await update.message.reply_photo(photo=resp.content, caption=f"🎨 {prompt}")
    except Exception as e:
        logger.exception("Rasm generatsiyasida xatolik")
        await update.message.reply_text(f"⚠️ Rasm yaratishda xatolik: {e}")


async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    await update.message.chat.send_action("upload_video")
    status_msg = await update.message.reply_text("🎬 Video tayyorlanmoqda, kuting...")
    try:
        url = f"{POLLINATIONS_BASE}/video/{quote(prompt)}"
        resp = requests.get(url, params={"key": POLLINATIONS_API_KEY}, timeout=300)
        resp.raise_for_status()
        await update.message.reply_video(video=resp.content, caption=f"🎬 {prompt}")
        await status_msg.delete()
    except Exception as e:
        logger.exception("Video generatsiyasida xatolik")
        await status_msg.edit_text(f"⚠️ Video yaratishda xatolik: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
