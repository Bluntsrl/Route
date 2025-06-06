import logging
import re
import json
import tempfile
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
from ocr import extract_addresses_from_image

# === Load Config ===
with open("config.json", "r") as f:
    config = json.load(f)
    TELEGRAM_BOT_TOKEN = config["7687692663:AAEZx-8Qa_LPA_Lpi-xV-I4ivl9tiQKOFE4"]

# === In-Memory Schedule Context ===
schedule_data = {}
WAIT_START, WAIT_END, WAIT_PICTURES, READY, IN_TRIP = range(5)

# === Helpers ===
def is_ohio_address(text):
    return bool(re.search(r",?\s*OH\s*\d{5}$", text.strip(), re.IGNORECASE))

def generate_maps_url(start, stops, end):
    all_locations = [start] + stops + [end]
    base = "https://www.google.com/maps/dir/"
    return base + "/".join([loc.replace(" ", "+") for loc in all_locations])

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Delivery Bot!\nUse /newschedule to start a new delivery schedule."
    )

async def newschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    schedule_data[chat_id] = {
        "state": WAIT_START,
        "start_location": None,
        "end_location": None,
        "pictures": [],
        "itinerary": [],
        "current_stop": 0,
    }
    await update.message.reply_text("New schedule started. Send your start address (e.g., '123 Main St, OH 44123').")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in schedule_data:
        await update.message.reply_text("Use /newschedule to start a new schedule.")
        return

    state = schedule_data[chat_id]["state"]
    text = update.message.text.strip()

    if state == WAIT_START:
        schedule_data[chat_id]["start_location"] = text
        schedule_data[chat_id]["state"] = WAIT_END
        await update.message.reply_text(f"Start location set to '{text}'. Now send the end address.")
    elif state == WAIT_END:
        schedule_data[chat_id]["end_location"] = text
        schedule_data[chat_id]["state"] = WAIT_PICTURES
        await update.message.reply_text("End location set. Send delivery screenshots or type more OH addresses. Use /endpictures when done.")
    elif state == WAIT_PICTURES:
        if is_ohio_address(text):
            schedule_data[chat_id]["pictures"].append(text)
            await update.message.reply_text(f"Added: {text}")
        else:
            await update.message.reply_text("Address ignored — not recognized as an Ohio address.")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in schedule_data or schedule_data[chat_id]["state"] != WAIT_PICTURES:
        await update.message.reply_text("Start a schedule with /newschedule first.")
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        await file.download_to_drive(custom_path=tf.name)
        extracted = extract_addresses_from_image(tf.name)

    ohio_addresses = [addr for addr in extracted if is_ohio_address(addr)]
    if ohio_addresses:
        schedule_data[chat_id]["pictures"].extend(ohio_addresses)
        await update.message.reply_text("Extracted OH addresses: " + ", ".join(ohio_addresses))
    else:
        await update.message.reply_text("No valid Ohio addresses found.")

async def endpictures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = schedule_data.get(chat_id)
    if not data or data["state"] != WAIT_PICTURES:
        await update.message.reply_text("No active session. Use /newschedule.")
        return

    if not data["pictures"]:
        await update.message.reply_text("No addresses collected.")
        return

    itinerary = [data["start_location"]] + data["pictures"] + [data["end_location"]]
    schedule_data[chat_id]["itinerary"] = itinerary
    schedule_data[chat_id]["state"] = READY

    url = generate_maps_url(data["start_location"], data["pictures"], data["end_location"])
    await update.message.reply_text(f"Route ready! Open in Maps:\n{url}\nUse /starttrip to begin.")

async def starttrip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = schedule_data.get(chat_id)
    if not data or data["state"] != READY:
        await update.message.reply_text("No route ready. Use /endpictures first.")
        return

    data["state"] = IN_TRIP
    data["current_stop"] = 1
    await update.message.reply_text("Trip started. First stop:")
    await update.message.reply_text(f"{data['itinerary'][1]}")

async def nextstop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = schedule_data.get(chat_id)
    if not data or data["state"] != IN_TRIP:
        await update.message.reply_text("Trip not in progress. Use /starttrip.")
        return

    data["current_stop"] += 1
    if data["current_stop"] >= len(data["itinerary"]):
        await update.message.reply_text("Trip complete!")
        del schedule_data[chat_id]
    else:
        await update.message.reply_text(f"Next stop: {data['itinerary'][data['current_stop']]}")

async def endtrip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in schedule_data:
        del schedule_data[chat_id]
    await update.message.reply_text("Trip ended.")

# === Main ===
async def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newschedule", newschedule))
    app.add_handler(CommandHandler("endpictures", endpictures))
    app.add_handler(CommandHandler("starttrip", starttrip))
    app.add_handler(CommandHandler("nextstop", nextstop))
    app.add_handler(CommandHandler("endtrip", endtrip))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
