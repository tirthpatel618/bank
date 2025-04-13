import logging
import telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
from PIL import Image
import pytesseract
import os
import psycopg2
import asyncio
from dotenv import load_dotenv
# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation States
QUOTE, ASK_PLACE, ASK_NUMBER, CHOOSE_TOPIC, NEW_TOPIC = range(5)

# Topics
TOPICS_FILE = "topics.txt"

def load_topics():
    """
    Load topics from a local text file. Each topic should be on its own line.
    If the file doesn't exist or is empty, return a default list.
    """
    if not os.path.exists(TOPICS_FILE):
        # Return some default topics if file not found
        return []

    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        # Ensure "Add new topic" is always at the end. We’ll remove it first if present.
        if "Add new topic" in lines:
            lines.remove("Add new topic")
        # Return the lines plus the special topic
        return lines + ["Add new topic"]

def save_topics(topics_list):
    """
    Save the topics list (excluding 'Add new topic') to the file.
    """
    # Filter out the special "Add new topic" if it’s in the list
    filtered = [topic for topic in topics_list if topic != "Add new topic"]
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        for topic in filtered:
            f.write(topic + "\n")

# Load topics at startup
TOPICS = load_topics()

# Database Configuration

DB_CONN = None  # Global database connection

load_dotenv()
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT')

def init_db():

    conn = psycopg2.connect(
         host=DB_HOST,      # Change if necessary
         port=DB_PORT,             # Default PostgreSQL port
         dbname=DB_NAME,   # Replace with your database name
         user=DB_USER,         # Replace with your database user
         password=DB_PASSWORD  # Replace with your database password
    )
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vachanamrut_quotes (
         id SERIAL PRIMARY KEY,
         vachanamrut_place TEXT,
         vachanamrut_number TEXT,
         quote TEXT,
         topic TEXT
    );
    ''')
    conn.commit()
    cursor.close()
    return conn

def insert_into_db(row):
    """
    Inserts a new row into the vachanamrut_quotes table.
    row: List in the order [vachanamrut_place, vachanamrut_number, quote, topic]
    """
    global DB_CONN
    cursor = DB_CONN.cursor()
    query = """
    INSERT INTO vachanamrut_quotes (vachanamrut_place, vachanamrut_number, quote, topic)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(query, tuple(row))
    DB_CONN.commit()
    cursor.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome! Please send me a Vachanamrut quote. You can send the text directly or a clear screenshot image."
    )
    return QUOTE

async def receive_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the incoming quote which can be either:
    - A photo: Performs OCR to extract text.
    - A text message: Uses the text directly.
    """
    if update.message.photo:
        try:
            # Get the best (highest resolution) photo available
            file_id = update.message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            image_path = "quote_image.jpg"
            await new_file.download_to_drive(image_path)

            # Use OCR to extract text from the image
            img = Image.open(image_path)
            extracted_text = pytesseract.image_to_string(img).strip()
            os.remove(image_path)
            
            if not extracted_text:
                await update.message.reply_text("I couldn’t extract any text from that image. Please try again or send the quote as text.")
                return QUOTE

            context.user_data["quote"] = extracted_text
            await update.message.reply_text("I extracted the following text:\n\n" + extracted_text)
        except Exception as e:
            logger.error("OCR error: %s", e)
            await update.message.reply_text("Sorry, an error occurred while processing your image. Please try again.")
            return QUOTE
    elif update.message.text:
        context.user_data["quote"] = update.message.text
    else:
        await update.message.reply_text("Please send a valid text or image.")
        return QUOTE

    await update.message.reply_text("Which Vachanamrut is this from? (Enter the Vachanamrut Place)")
    return ASK_PLACE

async def receive_place(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the Vachanamrut place and asks for the Vachanamrut number."""
    context.user_data["vachanamrut_place"] = update.message.text
    await update.message.reply_text("Please enter the Vachanamrut Number.")
    return ASK_NUMBER

async def receive_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the Vachanamrut number and prompts for the topic selection."""
    context.user_data["vachanamrut_number"] = update.message.text

    # Build a custom keyboard with topics
    reply_keyboard = [[topic] for topic in TOPICS]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "Select a topic for this quote (or choose 'Add new topic'):",
        reply_markup=markup,
    )
    return CHOOSE_TOPIC

async def choose_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Stores the selected topic or, if 'Add new topic' is chosen,
    initiates a new topic entry.
    """
    topic = update.message.text
    if topic == "Add new topic":
        await update.message.reply_text(
            "Please enter the new topic name:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NEW_TOPIC
    else:
        if topic not in TOPICS:
            await update.message.reply_text("Invalid topic selected. Please try again. Type /cancel to exit.")
            return CHOOSE_TOPIC
        context.user_data["topic"] = topic
        return await finalize(update, context)
    
async def add_new_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Adds the new topic into the topics list (and file) and stores it.
    """
    new_topic = update.message.text
    # Insert the new topic just before "Add new topic" if not already present
    if new_topic not in TOPICS:
        TOPICS.insert(-1, new_topic)
        # Persist the updated list to file
        save_topics(TOPICS)

    context.user_data["topic"] = new_topic
    await update.message.reply_text(f"New topic '{new_topic}' added.")
    return await finalize(update, context)

async def finalize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Inserts the collected data into the PostgreSQL database
    and completes the conversation.
    """
    quote = context.user_data.get("quote")
    vachanamrut_place = context.user_data.get("vachanamrut_place")
    vachanamrut_number = context.user_data.get("vachanamrut_number")
    topic = context.user_data.get("topic")

    # Prepare the row
    row = [vachanamrut_place, vachanamrut_number, quote, topic]

    try:
        # Insert into DB on a background thread to avoid blocking
        await asyncio.to_thread(insert_into_db, row)
        await update.message.reply_text(
            "The quote has been saved successfully to the database!",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error("Database error: %s", e)
        await update.message.reply_text(
            "Sorry, an error occurred while saving the quote. Please try again.",
            reply_markup=ReplyKeyboardRemove()
        )

    await update.message.reply_text("Send /start to add another quote.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    global DB_CONN

    # Initialize PostgreSQL connection (and table)
    DB_CONN = init_db()

    # Create the Telegram Bot Application
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    application = Application.builder().token(TOKEN).build()

    # Set up the conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUOTE: [MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, receive_quote)],
            ASK_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_place)],
            ASK_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_number)],
            CHOOSE_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_topic)],
            NEW_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_new_topic)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    # Start polling for updates
    application.run_polling()

if __name__ == "__main__":
    main()