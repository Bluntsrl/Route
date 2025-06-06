import os
import re
import logging
import pytesseract
from PIL import Image
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Replace with your bot token
BOT_TOKEN = "7687692663:AAEZx-8Qa_LPA_Lpi-xV-I4ivl9tiQKOFE4"

logging.basicConfig(level=logging.INFO)

# Basic U.S. street address regex
ADDRESS_REGEX = re.compile(
    r"\d{3,5}\s+[A-Z0-9 .]+(?:RD|ROAD|AVE|AVENUE|ST|STREET|DR|DRIVE|LANE|LN|BLVD|COURT|CT|WAY|CIRCLE|CIR)\b.*",
    re.IGNORECASE
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a screenshot with addresses and I’ll generate a Google Maps route.")

def extract_addresses(text: str):
    lines = text.splitlines()
    addresses = []
    buffer = []
    for line in lines:
        line = line.strip()
        if ADDRESS_REGEX.search(line):
            if buffer:
                addresses.append(" ".join(buffer))
                buffer = []
            buffer.append(line)
        elif buffer:
            buffer.append(line)
    if buffer:
        addresses.append(" ".join(buffer))
    return [addr.strip() for addr in addresses if addr.strip()]

def build_maps_url(addresses):
    base = "https://www.google.com/maps/dir/"
    parts = [addr.replace(" ", "+") for addr in addresses]
    return base + "/".join(parts)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    img_bytes = await photo_file.download_as_bytearray()
    img = Image.open(BytesIO(img_bytes))

    text = pytesseract.image_to_string(img)
    addresses = extract_addresses(text)

    if not addresses:
        await update.message.reply_text("I couldn’t find any addresses. Try a clearer screenshot.")
        return

    maps_url = build_maps_url(addresses)
    await update.message.reply_text("🗺 Google Maps Route:\n" + maps_url)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot is running...")
    app.run_polling()
