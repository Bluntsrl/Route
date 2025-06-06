# bot.py
import os
import logging
import easyocr
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from urllib.parse import quote_plus

# Setup
logging.basicConfig(level=logging.INFO)
reader = easyocr.Reader(['en'])  # Downloads model on first run

# Google Maps Route URL
def create_gmaps_route(addresses):
    base = "https://www.google.com/maps/dir/"
    return base + '/'.join([quote_plus(addr) for addr in addresses])

# Extract plausible street addresses (simplified regex)
def extract_addresses(text_lines):
    address_pattern = re.compile(r'\d{1,5}\s+\w+(\s\w+)*\s(St|Ave|Blvd|Rd|Ln|Dr|Ct|Way|Pl|Cir|Highway|Hwy)\b', re.IGNORECASE)
    return [line for line in text_lines if address_pattern.search(line)]

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = "image.jpg"
    await file.download_to_drive(file_path)

    result = reader.readtext(file_path, detail=0)
    addresses = extract_addresses(result)

    if len(addresses) < 2:
        await update.message.reply_text("Found less than 2 addresses. Please try a clearer screenshot.")
        return

    url = create_gmaps_route(addresses)
    await update.message.reply_text(f"📍 Google Maps Route:\n{url}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a screenshot with addresses and I’ll generate a route.")

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    app.run_polling()

if __name__ == "__main__":
    main()
