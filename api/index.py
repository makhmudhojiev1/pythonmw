from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import os
import logging

# Replace with your bot token and channel username
BOT_TOKEN = os.getenv('7135940302:AAFYWRjjhEnQ0_1ScjXtmLsS3gXxPvHr9Dk')  # Use environment variable for security
CHANNEL_USERNAME = os.getenv('@cdntelegraph')  # Use environment variable

# Dictionary to track files uploaded by the bot
uploaded_files = {}

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send me a file, and I'll upload it to the channel and share the URL.")

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available commands:
/start - Start the bot and get instructions.
/help - Show this help message.
/restart - Restart the bot (clears cached data).
/upload - Learn how to upload files to the bot.
"""
    await update.message.reply_text(help_text)

# Command: /restart
async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uploaded_files.clear()
    await update.message.reply_text("Bot has been restarted. All cached data has been cleared.")

# Command: /upload
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upload_instructions = """
To upload a file:
1. Send a file (document, photo, video, or audio) to this bot.
2. The bot will upload it to the channel and provide a URL.
3. You can delete the file using the "Delete File" button.
"""
    await update.message.reply_text(upload_instructions)

# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.document:
            file = update.message.document
        elif update.message.photo:
            file = update.message.photo[-1]
        elif update.message.video:
            file = update.message.video
        elif update.message.audio:
            file = update.message.audio
        else:
            await update.message.reply_text("Please send a valid file (document, photo, video, or audio).")
            return

        file_id = file.file_id

        # Send the file to the channel
        if update.message.document:
            sent_message = await context.bot.send_document(chat_id=CHANNEL_USERNAME, document=file_id)
        elif update.message.photo:
            sent_message = await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id)
        elif update.message.video:
            sent_message = await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id)
        elif update.message.audio:
            sent_message = await context.bot.send_audio(chat_id=CHANNEL_USERNAME, audio=file_id)

        # Generate the public URL for the file in the channel
        channel_message_id = sent_message.message_id
        channel_url = f"https://t.me/{CHANNEL_USERNAME[1:]}/{channel_message_id}"

        # Store the file information for deletion
        uploaded_files[channel_message_id] = {
            "file_id": file_id,
            "file_type": "document" if update.message.document else
                         "photo" if update.message.photo else
                         "video" if update.message.video else
                         "audio",
            "user_id": update.message.from_user.id
        }

        # Send the URL back to the user with a delete button
        keyboard = [[InlineKeyboardButton("Delete File", callback_data=f"delete_{channel_message_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"File uploaded to the channel! Here's the URL:\n{channel_url}", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error handling file: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

# Handle file deletion
async def handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channel_message_id = int(query.data.split("_")[1])

    if channel_message_id in uploaded_files and uploaded_files[channel_message_id]["user_id"] == query.from_user.id:
        try:
            await context.bot.delete_message(chat_id=CHANNEL_USERNAME, message_id=channel_message_id)
            del uploaded_files[channel_message_id]
            await query.edit_message_text("File successfully deleted!")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            await query.edit_message_text(f"Failed to delete the file: {e}")
    else:
        await query.edit_message_text("You do not have permission to delete this file or it no longer exists.")

# Initialize the bot application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("restart", restart_command))
application.add_handler(CommandHandler("upload", upload_command))
application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_file))
application.add_handler(CallbackQueryHandler(handle_delete))

# Webhook handler for Vercel
async def webhook(request):
    try:
        body = await request.json()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}
