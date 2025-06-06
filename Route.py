import logging
import pytesseract
import re
from PIL import Image
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(level=logging.INFO)

# Replace with your actual bot token
import os
BOT_TOKEN = os.environ["7687692663:AAEZx-8Qa_LPA_Lpi-xV-I4ivl9tiQKOFE4"]

# Address regex (simple street pattern, can be improved)
ADDRESS_REGEX = r'\d{1,5} [\w\s]{1,40},? [\w\s]{1,40}'

def extract_addresses(text):
    return re.findall(ADDRESS_REGEX, text)

def generate_maps_url(addresses):
    base = "https://www.google.com/maps/dir/"
    joined = "/".join(address.replace(" ", "+") for address in addresses)
    return base + joined

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    # Get the highest resolution photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    img_bytes = await file.download_as_bytearray()

    image = Image.open(BytesIO(img_bytes))
    ocr_text = pytesseract.image_to_string(image)
    addresses = extract_addresses(ocr_text)

    if len(addresses) < 2:
        await update.message.reply_text("Couldn't find at least two addresses. Please try again with a clearer image.")
        return

    maps_url = generate_maps_url(addresses)
    await update.message.reply_text(f"📍 Driving route:\n{maps_url}")

# Start bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    print("Bot is running...")
    app.run_polling()
