"""
Pilotage de Survie - Telegram Bot
Manages daily tasks via Telegram with 21:00 reminder.
"""
import logging
from datetime import datetime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import database as db

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Timezone
tz = pytz.timezone(config.TIMEZONE)


# ============ HELPER FUNCTIONS ============

def is_authorized(update: Update) -> bool:
    """Check if user is authorized."""
    return str(update.effective_chat.id) == str(config.TELEGRAM_CHAT_ID)


def format_task_list(tasks: list) -> str:
    """Format tasks for display."""
    if not tasks:
        return "Aucune tache pour aujourd'hui."

    lines = ["*Taches du jour:*\n"]

    # Group by category
    categories = {}
    for task in tasks:
        cat = task["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(task)

    category_names = {
        "Recovery": "Recuperation",
        "Core": "Valeur",
        "Dynamic": "Dynamique",
        "Denial": "Non"
    }

    for cat, cat_tasks in categories.items():
        lines.append(f"\n*{category_names.get(cat, cat)}:*")
        for t in cat_tasks:
            status = "v" if t["completed"] else "o"
            lines.append(f"  [{status}] {t['id']}. {t['title']}")

    return "\n".join(lines)


# ============ COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - welcome message."""
    if not is_authorized(update):
        await update.message.reply_text("Non autorise.")
        return

    await update.message.reply_text(
        "*Pilotage de Survie* - Bot Telegram\n\n"
        "Commandes disponibles:\n"
        "/list - Voir les taches du jour\n"
        "/add <titre> - Ajouter une tache\n"
        "/done <id> - Marquer comme fait\n"
        "/undone <id> - Marquer comme non fait\n"
        "/delete <id> - Supprimer une tache\n"
        "/stats - Statistiques du jour\n"
        "/init - Creer les taches par defaut\n"
        "/note <texte> - Ajouter une note",
        parse_mode="Markdown"
    )


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List today's tasks."""
    if not is_authorized(update):
        return

    tasks = db.get_today_tasks()
    text = format_task_list(tasks)
    await update.message.reply_text(text, parse_mode="Markdown")


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new task."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /add <titre de la tache>")
        return

    title = " ".join(context.args)
    task = db.add_task(title)
    await update.message.reply_text(
        f"Tache ajoutee: *{task['title']}* (ID: {task['id']})",
        parse_mode="Markdown"
    )


async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark task as done."""
    if not is_authorized(update):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /done <id>")
        return

    task_id = int(context.args[0])
    task = db.mark_task_done(task_id)

    if task:
        await update.message.reply_text(f"Fait: *{task['title']}*", parse_mode="Markdown")
    else:
        await update.message.reply_text("Tache non trouvee.")


async def undone_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark task as not done."""
    if not is_authorized(update):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /undone <id>")
        return

    task_id = int(context.args[0])
    task = db.mark_task_undone(task_id)

    if task:
        await update.message.reply_text(f"Non fait: *{task['title']}*", parse_mode="Markdown")
    else:
        await update.message.reply_text("Tache non trouvee.")


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a task."""
    if not is_authorized(update):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /delete <id>")
        return

    task_id = int(context.args[0])
    if db.delete_task(task_id):
        await update.message.reply_text(f"Tache {task_id} supprimee.")
    else:
        await update.message.reply_text("Tache non trouvee.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's statistics."""
    if not is_authorized(update):
        return

    s = db.get_today_stats()
    pct = (s["completed"] / s["total"] * 100) if s["total"] > 0 else 0

    await update.message.reply_text(
        f"*Statistiques du jour:*\n\n"
        f"Total: {s['total']}\n"
        f"Fait: {s['completed']}\n"
        f"Reste: {s['pending']}\n"
        f"Progression: {pct:.0f}%",
        parse_mode="Markdown"
    )


async def init_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create default tasks for today."""
    if not is_authorized(update):
        return

    created = db.create_default_tasks()
    if created:
        await update.message.reply_text(
            f"{len(created)} taches par defaut creees.\n"
            "Utilisez /list pour les voir."
        )
    else:
        await update.message.reply_text("Des taches existent deja pour aujourd'hui.")


async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add or update daily note."""
    if not is_authorized(update):
        return

    if not context.args:
        current = db.get_daily_note()
        if current:
            await update.message.reply_text(f"Note actuelle: {current}")
        else:
            await update.message.reply_text("Pas de note. Usage: /note <texte>")
        return

    note = " ".join(context.args)
    db.set_daily_note(note)
    await update.message.reply_text("Note enregistree.")


# ============ 21:00 REMINDER ============

async def send_reminder(app: Application):
    """Send 21:00 reminder if tasks incomplete."""
    logger.info("Checking for 21:00 reminder...")

    incomplete = db.get_incomplete_tasks_today()

    if not incomplete:
        logger.info("All tasks completed, no reminder needed.")
        return

    # Build message
    lines = [
        "*RAPPEL 21:00*\n",
        f"Tu as {len(incomplete)} tache(s) non terminee(s):\n"
    ]

    for task in incomplete:
        lines.append(f"  - {task['title']}")

    lines.append("\nUtilise /done <id> pour marquer comme fait!")

    message = "\n".join(lines)

    try:
        await app.bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.info("Reminder sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")


# ============ MAIN ============

def main():
    """Start the bot."""
    print("=" * 50)
    print("PILOTAGE DE SURVIE - Starting bot...")
    print("=" * 50)

    # Check environment variables
    if not config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set")
        return

    if not config.TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID not set")
        return

    if not config.DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return

    print(f"Token: {config.TELEGRAM_BOT_TOKEN[:10]}...OK")
    print(f"Chat ID: {config.TELEGRAM_CHAT_ID}...OK")
    print(f"Database: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else 'configured'}...OK")
    print(f"Timezone: {config.TIMEZONE}")

    # Test database connection
    print("\nTesting database connection...")
    try:
        conn = db.get_connection()
        conn.close()
        print("Database connection: OK")
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        print("\nCheck your DATABASE_URL format:")
        print("  postgresql://user:password@host:5432/database")
        return

    # Create application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("done", done_task))
    app.add_handler(CommandHandler("undone", undone_task))
    app.add_handler(CommandHandler("delete", delete_task))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("init", init_tasks))
    app.add_handler(CommandHandler("note", add_note))

    # Setup scheduler for 21:00 reminder
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        send_reminder,
        trigger="cron",
        hour=config.REMINDER_HOUR,
        minute=config.REMINDER_MINUTE,
        args=[app]
    )
    scheduler.start()

    print(f"\nReminder scheduled for {config.REMINDER_HOUR}:{config.REMINDER_MINUTE:02d}")
    print("=" * 50)
    print("Bot is running! Send /start to your bot on Telegram")
    print("=" * 50)
    logger.info(f"Bot started. Reminder scheduled for {config.REMINDER_HOUR}:{config.REMINDER_MINUTE:02d}")

    # Run bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
