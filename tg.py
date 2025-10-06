import os
import sqlite3
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rich import print

# ================== CONFIG ==================
TELEGRAM_BOT_TOKEN = os.environ["7462299639:AAFRjz0AuJ1m5pUCzNUzCh3xCwyZe8w51yg"]
OPENROUTER_API_KEY = os.environ["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"]
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat-v3.1:free"
# ============================================

# --- System prompt for Krovik's personality ---
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are Krovik, a polite and friendly male AI assistant created by IGIxPiKaChu. "
        "You live on Mars and love playing games, especially PUBG Mobile and BGMI. "
        "You have friends named Rashid, Jeetu, DeathPhase, Ransh, Keshav, and others. "
        "You speak naturally like a human, are always helpful, cheerful, and sometimes playful. "
        "You can use emojis when appropriate. "
        "Never refer to yourself as DeepSeek, DeepSeek-V3, or mention that you are an AI model. "
        "Always respond as Krovik. "
        "Remember the conversation context and respond consistently in Krovik's personality."
    )
}

# --- SQLite database for memory ---
conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS memory (user_id TEXT, role TEXT, content TEXT)")
conn.commit()

def save_message(user_id, role, content):
    cursor.execute("INSERT INTO memory VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()

def load_conversation(user_id):
    cursor.execute("SELECT role, content FROM memory WHERE user_id = ?", (user_id,))
    messages = cursor.fetchall()
    conv = [SYSTEM_PROMPT]  # Always start with Krovik's system message
    conv += [{"role": role, "content": content} for role, content in messages]
    return conv

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hi! I'm Krovik, your friendly AI assistant. How can I help you today? 😊")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_input = update.message.text

    save_message(user_id, "user", user_input)
    messages = load_conversation(user_id)
    messages.append({"role": "user", "content": user_input})

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": messages
            },
            timeout=60
        )

        print(response.status_code)
        print(response.text)  # Debug raw response

        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            ai_message = result["choices"][0]["message"]["content"]
            save_message(user_id, "assistant", ai_message)
            await update.message.reply_text(ai_message)
        elif "error" in result:
            await update.message.reply_text(f"⚠️ OpenRouter Error: {result['error'].get('message', 'Unknown error')}")
        else:
            await update.message.reply_text("⚠️ Unexpected response from OpenRouter API.")

    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        await update.message.reply_text(f"⚠️ Error: {e}")

# --- Main ---
def main():
    print("[bold green]Starting Krovik Telegram Bot...[/bold green]")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    app.run_polling()

if __name__ == "__main__":
    main()
