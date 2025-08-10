
import os
import logging
import hashlib
import sqlite3
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Configuration ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('wellby021_bot')

# For development only - Remove for production!
TOKEN = "8027673333:AAEPW2LZYVTVZrmauZQDrb1KZveXEEm9PfE"  # Your wellby021_bot token
WEBHOOK_SECRET = "Juicewrld999."  # Change this to a strong password
APP_NAME = "wellby021-bot"

# Production settings (uncomment when deploying)
# TOKEN = os.getenv('TELEGRAM_TOKEN')
# WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET_TOKEN')
# APP_NAME = os.getenv('RENDER_APP_NAME', 'wellby021-bot')

PORT = int(os.getenv('PORT', 5000))
WEBHOOK_URL = f"https://{APP_NAME}.onrender.com/{TOKEN}"
UPLOAD_FOLDER = "videos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database ---
def init_db():
    with sqlite3.connect('wellby_bot.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS videos
                        (id INTEGER PRIMARY KEY,
                         file_hash TEXT UNIQUE,
                         video_name TEXT,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

# --- Handlers ---
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.video:
            return

        user = update.effective_user
        logger.info(f"New video from @{user.username} ({user.id})")

        file = await update.message.video.get_file()
        video_path = f"{UPLOAD_FOLDER}/{file.file_id}.mp4"
        await file.download_to_drive(video_path)
        
        with open(video_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        with sqlite3.connect('wellby_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT video_name FROM videos WHERE file_hash=?", (file_hash,))
            
            if result := cursor.fetchone():
                await update.message.reply_text(f"🎥 Video recognized: {result[0]}")
            else:
                video_name = f"clip_{file_hash[:8]}"
                cursor.execute("INSERT INTO videos (file_hash, video_name) VALUES (?,?)",
                             (file_hash, video_name))
                conn.commit()
                await update.message.reply_text(
                    f"✅ New video saved as: {video_name}\n"
                    f"🔒 Hash: {file_hash[:12]}...",
                    parse_mode='Markdown'
                )

    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await update.message.reply_text("⚠️ Error processing your video. Please try again.")

# --- Main ---
def main():
    # Security check
    if not TOKEN or ":" not in TOKEN:
        logger.error("Invalid token format! Expected '123456789:ABCdef...'")
        return
    
    init_db()
    
    app = Application.builder() \
        .token(TOKEN) \
        .post_init(lambda app: logger.info("Bot initialized")) \
        .build()
    
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    if os.getenv('RENDER'):
        logger.info("Starting webhook mode...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True
        )
    else:
        logger.info("Starting polling mode...")
        app.run_polling()

if __name__ == "__main__":
    main()
