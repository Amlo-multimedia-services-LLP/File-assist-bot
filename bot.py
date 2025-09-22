import logging
import os
import redis # Import the redis library
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION (Reads from Heroku Config Vars) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_GROUP_ID = int(os.environ.get("DATABASE_GROUP_ID", 0))
FILE_ASSIST_GROUP_ID = int(os.environ.get("FILE_ASSIST_GROUP_ID", 0))

# --- REDIS DATABASE CONNECTION ---
# Heroku automatically provides the REDIS_URL when the add-on is provisioned
redis_url = os.environ.get("REDIS_URL")
# The 'decode_responses=True' part means we get strings back from Redis, not bytes
db = redis.from_url(redis_url, decode_responses=True) if redis_url else None

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
        )
        logger = logging.getLogger(__name__)

        # --- CORE BOT HANDLER FUNCTIONS (Modified for Redis) ---
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Sends a welcome message when the /start command is issued."""
                await update.message.reply_text(
                        "Hello! I am your File Assistant Bot, running on Heroku."
                            )

                            async def handle_new_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                                """Handles new documents and saves them to Redis."""
                                    if not update.message.document or update.message.chat_id != DATABASE_GROUP_ID:
                                            return

                                                file_name = update.message.document.file_name
                                                    file_id = update.message.document.file_id

                                                        # Instead of a dictionary, we now use db.set(key, value)
                                                            db.set(file_name, file_id)
                                                                
                                                                    logger.info(f"Indexed file to Redis: {file_name}")
                                                                        await update.message.reply_text(f"✅ Indexed: `{file_name}`", parse_mode='MarkdownV2')

                                                                        async def handle_file_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                                                                            """Handles text messages and fetches files from Redis."""
                                                                                if not update.message.text or update.message.chat_id != FILE_ASSIST_GROUP_ID:
                                                                                        return

                                                                                            requested_filename = update.message.text.strip()
                                                                                                logger.info(f"Received request for '{requested_filename}'")

                                                                                                    # Instead of a dictionary, we now use db.get(key)
                                                                                                        file_id = db.get(requested_filename)

                                                                                                            if file_id:
                                                                                                                    logger.info(f"File found in Redis! Sending...")
                                                                                                                            await context.bot.send_document(
                                                                                                                                        chat_id=FILE_ASSIST_GROUP_ID,
                                                                                                                                                    document=file_id,
                                                                                                                                                                caption=f"Here is your file: `{requested_filename}`",
                                                                                                                                                                            parse_mode='MarkdownV2'
                                                                                                                                                                                    )
                                                                                                                                                                                        else:
                                                                                                                                                                                                logger.warning(f"File '{requested_filename}' not found in Redis.")
                                                                                                                                                                                                        await update.message.reply_text(
                                                                                                                                                                                                                    f"Sorry, I couldn't find the file named `{requested_filename}`\\. "
                                                                                                                                                                                                                                "Please check the name and try again\\.",
                                                                                                                                                                                                                                            parse_mode='MarkdownV2'
                                                                                                                                                                                                                                                    )

                                                                                                                                                                                                                                                    # --- MAIN FUNCTION TO RUN THE BOT ---
                                                                                                                                                                                                                                                    def main() -> None:
                                                                                                                                                                                                                                                        """Set up handlers and start the bot."""
                                                                                                                                                                                                                                                            if not all([BOT_TOKEN, DATABASE_GROUP_ID, FILE_ASSIST_GROUP_ID, db]):
                                                                                                                                                                                                                                                                    logger.error("FATAL: Environment variables or Redis connection is missing. Bot cannot start.")
                                                                                                                                                                                                                                                                            if not db:
                                                                                                                                                                                                                                                                                        logger.error("Could not connect to Redis. Check if the Heroku Redis add-on is provisioned.")
                                                                                                                                                                                                                                                                                                return
                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                        application = Application.builder().token(BOT_TOKEN).build()

                                                                                                                                                                                                                                                                                                            # Register all the handlers
                                                                                                                                                                                                                                                                                                                application.add_handler(CommandHandler("start", start))
                                                                                                                                                                                                                                                                                                                    application.add_handler(MessageHandler(filters.Document.Chat(chat_id=DATABASE_GROUP_ID), handle_new_files))
                                                                                                                                                                                                                                                                                                                        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=FILE_ASSIST_GROUP_ID), handle_file_request))

                                                                                                                                                                                                                                                                                                                            print("Bot is running on Heroku...")
                                                                                                                                                                                                                                                                                                                                application.run_polling()

                                                                                                                                                                                                                                                                                                                                if __name__ == '__main__':
                                                                                                                                                                                                                                                                                                                                    main()