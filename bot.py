import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory store: chat_id -> {"text": str, "message_id": int}
sticky_store: dict[int, dict] = {}


async def setsticky(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a sticky message for this chat."""
    chat_id = update.effective_chat.id
    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Usage: /setsticky <your message>")
        return

    # Delete old sticky if exists
    await _delete_old_sticky(context, chat_id)

    # Post the new sticky
    sent = await context.bot.send_message(chat_id=chat_id, text=f"📌 {text}")
    sticky_store[chat_id] = {"text": text, "message_id": sent.message_id}

    # Delete the command message to reduce clutter
    try:
        await update.message.delete()
    except Exception:
        pass


async def clearsticky(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the sticky message for this chat."""
    chat_id = update.effective_chat.id

    await _delete_old_sticky(context, chat_id)
    sticky_store.pop(chat_id, None)
    await update.message.reply_text("Sticky message cleared.")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-post the sticky message whenever anyone sends a message."""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    sticky = sticky_store.get(chat_id)

    if not sticky:
        return

    # Delete the old sticky message
    await _delete_old_sticky(context, chat_id)

    # Re-post sticky as the latest message
    sent = await context.bot.send_message(chat_id=chat_id, text=f"📌 {sticky['text']}")
    sticky_store[chat_id] = {"text": sticky["text"], "message_id": sent.message_id}


async def _delete_old_sticky(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    sticky = sticky_store.get(chat_id)
    if sticky:
        try:
            await context.bot.delete_message(
                chat_id=chat_id, message_id=sticky["message_id"]
            )
        except Exception:
            pass  # Message may already be deleted or too old


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("setsticky", setsticky))
    app.add_handler(CommandHandler("clearsticky", clearsticky))

    # Listen to all non-command text messages (and also commands from others)
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, on_message)
    )
    # Also re-bump on commands posted by others (but not our own setsticky/clearsticky)
    app.add_handler(
        MessageHandler(
            filters.COMMAND
            & ~filters.Regex(r"^/(setsticky|clearsticky)"),
            on_message,
        )
    )

    logger.info("Bot started. Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
