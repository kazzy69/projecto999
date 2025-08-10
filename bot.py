import os
import logging
import random
import hashlib
import sqlite3
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('8027673333:AAEPW2LZYVTVZrmauZQDrb1KZveXEEm9PfE')
UPLOAD_FOLDER = "videos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuração do Webhook
RENDER_APP_NAME = os.getenv('RENDER_APP_NAME')
WEBHOOK_URL = f"https://{RENDER_APP_NAME}.onrender.com/{TOKEN}"
PORT = int(os.environ.get('PORT', 5000))
SECRET_TOKEN = os.getenv('WEBHOOK_SECRET_TOKEN')

# Inicialização do banco de dados
def init_db():
    try:
        with sqlite3.connect('thimbles.db') as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS embaralhamentos
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         nome TEXT,
                         video_path TEXT,
                         file_hash TEXT UNIQUE)''')
            conn.commit()
    except Exception as e:
        logger.error(f"Erro no banco de dados: {e}")

# Geração de hash alternativa (sem OpenCV)
def generate_file_hash(file_path):
    try:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        return hashlib.md5(f"{file_name}_{file_size}_{os.path.getmtime(file_path)}".encode()).hexdigest()
    except Exception as e:
        logger.error(f"Erro ao gerar hash: {e}")
        return None

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.video:
            return

        file = await update.message.video.get_file()
        video_path = os.path.join(UPLOAD_FOLDER, f"{file.file_id}.mp4")
        await file.download_to_drive(video_path)
        
        file_hash = generate_file_hash(video_path)
        if not file_hash:
            await update.message.reply_text("❌ Erro ao processar vídeo")
            return

        with sqlite3.connect('thimbles.db') as conn:
            c = conn.cursor()
            c.execute("SELECT nome FROM embaralhamentos WHERE file_hash = ?", (file_hash,))
            
            if result := c.fetchone():
                await update.message.reply_text(f"🔍 Reconhecido: {result[0]}")
            else:
                nome = f"{random.choice(['kicumu','oh','vibe'])}_{random.randint(1000,9999)}"
                c.execute("INSERT INTO embaralhamentos (nome, video_path, file_hash) VALUES (?,?,?)",
                          (nome, video_path, file_hash))
                conn.commit()
                await update.message.reply_text(f"✨ Novo registro: {nome}")

    except Exception as e:
        logger.error(f"Erro no handle_video: {e}")
        await update.message.reply_text("⚠️ Ocorreu um erro. Tente novamente.")

async def set_webhook(app: Application):
    try:
        await app.bot.set_webhook(
            url=WEBHOOK_URL,
            secret_token=SECRET_TOKEN,
            drop_pending_updates=True
        )
        logger.info(f"Webhook configurado em {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")

async def startup(app: Application):
    init_db()
    await set_webhook(app)

def main():
    app = Application.builder() \
        .token(TOKEN) \
        .post_init(startup) \
        .build()
    
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    if os.environ.get('RENDER'):
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=SECRET_TOKEN,
            webhook_url=WEBHOOK_URL
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
