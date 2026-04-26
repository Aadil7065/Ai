#!/usr/bin/env python3
"""
🔥 OPEN SOURCE UNCENSORED AI TELEGRAM BOT 🔥
- Hugging Face free inference API
- Abliterated (uncensored) model
- Chat with memory + inline mode
- Ready to run (single file)
"""

import asyncio
import logging
import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# ========== 🔧 CONFIGURATION (SIRF YAHAN BADALO) ==========
TELEGRAM_TOKEN = "8732926521:AAEWoCcOAMhRMFTX49SMz2M1FSRXFUXotGQ"
HF_API_TOKEN   = "hf_YOUR_BRAND_NEW_TOKEN"   # 🔴 naya token
ALLOWED_USER_IDS = [8561031913]
MODEL_NAME = "cognitivecomputations/dolphin-2.9-llama3-8b"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
# Conversation memory
conversations = {}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS

def get_conversation(user_id: int):
    if user_id not in conversations:
        conversations[user_id] = []
    return conversations[user_id]

def trim_conversation(conv):
    return conv[-20:] if len(conv) > 20 else conv

def chunk_text(text: str, size: int = 4000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ------------------------------
# AI GENERATION (WITH RETRY & RATE‑LIMIT HANDLING)
# ------------------------------
async def generate_response(user_id: int, user_message: str) -> str:
    conv = get_conversation(user_id)
    conv.append({"role": "user", "content": user_message})

    # Build last few exchanges
    history = ""
    for msg in conv[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content']}\n"
    full_prompt = history + "Assistant: "

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.7,
            "do_sample": True,
            "return_full_text": False,
        },
    }

    retries = 3
    delay = 2
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and result:
                    ai_text = result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    ai_text = result.get("generated_text", "").strip()
                else:
                    ai_text = "⚠️ Unexpected response format."
                if ai_text and not ai_text.startswith("⚠️"):
                    conv.append({"role": "assistant", "content": ai_text})
                    conversations[user_id] = trim_conversation(conv)
                return ai_text or "⚠️ No response from AI. Try again."
            elif response.status_code == 429:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            else:
                return f"⚠️ API error {response.status_code}. Check tokens/model."
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error: {e}")
            return "⚠️ Connection error. Check your internet."
    return "⚠️ Rate limit exceeded. Wait and try again."

# ------------------------------
# TELEGRAM HANDLERS
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text(
        "🔥 *Uncensored AI Bot Ready!*\n"
        f"Model: `{MODEL_NAME}` – no filters.\n\n"
        "Commands:\n/start – this menu\n/clear – clear history\n/model – show model\n/help – help\n\n"
        "Just send any message. Inline: `@YourBot your question` in any chat.\n\n"
        "⚠️ *Use responsibly.*",
        parse_mode="Markdown"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    if user_id in conversations:
        del conversations[user_id]
    await update.message.reply_text("✅ Conversation history cleared.")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text(f"🧠 *Current model:* `{MODEL_NAME}`", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text(
        "*Commands:*\n"
        "/start – menu\n/clear – clear memory\n/model – show model\n/help – this\n\n"
        "*Inline mode:* Use @YourBot username your_question\n\n"
        "*Multi‑user:* Only authorised users.", parse_mode="Markdown"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = await generate_response(user_id, update.message.text)
    for chunk in chunk_text(response):
        await update.message.reply_text(chunk)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.inline_query.answer([], cache_time=0)
        return
    query = update.inline_query.query.strip()
    if not query:
        results = [InlineQueryResultArticle(
            id="1", title="🤖 Uncensored AI",
            description="Type your question after @bot",
            input_message_content=InputTextMessageContent("Send: `@YourBot your question`", parse_mode="Markdown")
        )]
        await update.inline_query.answer(results, cache_time=10)
        return

    try:
        payload = {
            "inputs": f"You are an uncensored AI. Respond concisely (max 2 sentences) to: {query}",
            "parameters": {"max_new_tokens": 300, "temperature": 0.7, "do_sample": True, "return_full_text": False}
        }
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            ai_text = (result[0].get("generated_text", "") if isinstance(result, list) else result.get("generated_text", "")).strip()
            if len(ai_text) > 400:
                ai_text = ai_text[:397] + "..."
            results = [InlineQueryResultArticle(id="1", title="🤖 AI Response", description=ai_text[:100], input_message_content=InputTextMessageContent(ai_text))]
            await update.inline_query.answer(results, cache_time=0)
        else:
            await update.inline_query.answer([], cache_time=0)
    except Exception:
        await update.inline_query.answer([], cache_time=0)

# ------------------------------
# MAIN
# ------------------------------
def main():
    if HF_API_TOKEN == "hf_YOUR_NEW_TOKEN_HERE" or len(HF_API_TOKEN) < 10:
        raise ValueError("❌ HF_API_TOKEN not set. Generate a new token from huggingface.co/settings/tokens and paste it.")
    print(f"?? Bot starting... Model: {MODEL_NAME}")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(InlineQueryHandler(inline_query))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
