import logging
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION (Reads from Render Environment Variables) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# The '0' is a default value in case the variable isn't found
DATABASE_GROUP_ID = int(os.environ.get("DATABASE_GROUP_ID", 0))
FILE_ASSIST_GROUP_ID = int(os.environ.get("FILE_ASSIST_GROUP_ID", 0))

# --- DATABASE PATH (Modified for Render's Persistent Disk) ---
DISK_PATH = os.environ.get('RENDER_DISK_PATH', '.')
DATABASE_FILE = os.path.join(DISK_PATH, "database.json")

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- GLOBAL DATABASE DICTIONARY ---
file_database = {}

# --- DATABASE HELPER FUNCTIONS ---
def load_database_from_file():
    """Loads the file index from the JSON file on the persistent disk."""
    try:
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"Database file not found at {DATABASE_FILE}. Starting fresh.")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Could not decode JSON from {DATABASE_FILE}. Starting fresh.")
        return {}

def save_database_to_file():
    """Saves the current file index to the JSON file on the persistent disk."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(file_database, f, indent=4)
    logger.info(f"Database saved to {DATABASE_FILE}")

# --- CORE BOT HANDLER FUNCTIONS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! I am your File Assistant Bot.\n"
        "I will help you find files. Just type the filename you need."
    )

async def handle_new_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles new documents uploaded to the Database Group."""
    if not update.message.document or update.message.chat_id != DATABASE_GROUP_ID:
        return

    file_name = update.message.document.file_name
    file_id = update.message.document.file_id

    file_database[file_name] = file_id
    save_database_to_file()
    
    logger.info(f"Indexed file: {file_name}")
    await update.message.reply_text(f"✅ Indexed: `{file_name}`", parse_mode='MarkdownV2')

async def handle_file_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages in the File Assist Group to search for files."""
    if not update.message.text or update.message.chat_id != FILE_ASSIST_GROUP_ID:
        return

    requested_filename = update.message.text.strip()
    logger.info(f"Received request for '{requested_filename}'")

    file_id = file_database.get(requested_filename)

    if file_id:
        logger.info(f"File found! Sending...")
        await context.bot.send_document(
            chat_id=FILE_ASSIST_GROUP_ID,
            document=file_id,
            caption=f"Here is your file: `{requested_filename}`",
            parse_mode='MarkdownV2'
        )
    else:
        logger.warning(f"File '{requested_filename}' not found.")
        await update.message.reply_text(
            f"Sorry, I couldn't find the file named `{requested_filename}`\\. "
            "Please check the name and try again\\.",
            parse_mode='MarkdownV2'
        )

# --- MAIN FUNCTION TO RUN THE BOT ---
def main() -> None:
    """Load data, set up handlers, and start the bot."""
    global file_database
    file_database = load_database_from_file()
    logger.info(f"Loaded {len(file_database)} files from database.")

    if not BOT_TOKEN or not DATABASE_GROUP_ID or not FILE_ASSIST_GROUP_ID:
        logger.error("FATAL: Environment variables (BOT_TOKEN, DATABASE_GROUP_ID, FILE_ASSIST_GROUP_ID) are not configured correctly. The bot cannot start.")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()

    # Register all the handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.Chat(chat_id=DATABASE_GROUP_ID), handle_new_files))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=FILE_ASSIST_GROUP_ID), handle_file_request))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
