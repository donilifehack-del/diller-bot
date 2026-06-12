from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import database as db
import re

(AUTH_MENU, REGISTER_NAME, REGISTER_EMAIL, REGISTER_PASSWORD,
 LOGIN_EMAIL, LOGIN_PASSWORD) = range(6)

STATES = {}


def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None


def auth_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Akkaunt yaratish", callback_data="auth_register")],
        [InlineKeyboardButton("🔑 Kirish (Login)", callback_data="auth_login")],
    ])


async def auth_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Diller boshqaruv tizimi*\n\n"
        "Davom etish uchun akkauntingizga kiring\n"
        "yoki yangi akkaunt yarating:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=auth_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=auth_keyboard(), parse_mode="Markdown")
    return AUTH_MENU


# ─── REGISTER ─────────────────────────────────────────────────────────────────

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🆕 *Yangi akkaunt yaratish*\n\nIsm-familyangizni kiriting:",
        parse_mode="Markdown"
    )
    return REGISTER_NAME


async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Ism kamida 2 ta harf bo'lishi kerak:")
        return REGISTER_NAME
    context.user_data["reg_name"] = name
    await update.message.reply_text("📧 Email manzilingizni kiriting (masalan: test@gmail.com):")
    return REGISTER_EMAIL


async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if not is_valid_email(email):
        await update.message.reply_text("❌ Noto'g'ri email format. Qayta kiriting:")
        return REGISTER_EMAIL
    context.user_data["reg_email"] = email
    await update.message.reply_text(
        "🔒 Parol o'rnating (kamida 4 ta belgi):\n\n"
        "⚠️ Parolni yodda saqlang!"
    )
    return REGISTER_PASSWORD


async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if len(password) < 4:
        await update.message.reply_text("❌ Parol kamida 4 ta belgi bo'lishi kerak:")
        return REGISTER_PASSWORD

    name = context.user_data["reg_name"]
    email = context.user_data["reg_email"]

    success, msg = db.register_user(email, password, name)
    if success:
        user = db.login_user(email, password)
        db.update_telegram_id(user["id"], update.message.from_user.id)
        context.user_data["user_id"] = user["id"]
        context.user_data["user_name"] = user["name"]
        context.user_data["logged_in"] = True

        from handlers.start_handler import main_menu_keyboard
        await update.message.reply_text(
            f"✅ *Akkaunt yaratildi!*\n\n"
            f"👤 Ism: *{name}*\n"
            f"📧 Email: *{email}*\n\n"
            f"Xush kelibsiz, *{name}*! 🎉",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"❌ {msg}\n\nBoshqa email kiriting:",
        )
        return REGISTER_EMAIL


# ─── LOGIN ────────────────────────────────────────────────────────────────────

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 *Kirish*\n\nEmail manzilingizni kiriting:",
        parse_mode="Markdown"
    )
    return LOGIN_EMAIL


async def login_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    context.user_data["login_email"] = email
    await update.message.reply_text("🔒 Parolni kiriting:")
    return LOGIN_PASSWORD


async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    email = context.user_data["login_email"]

    user = db.login_user(email, password)
    if user:
        db.update_telegram_id(user["id"], update.message.from_user.id)
        context.user_data["user_id"] = user["id"]
        context.user_data["user_name"] = user["name"]
        context.user_data["logged_in"] = True

        from handlers.start_handler import main_menu_keyboard
        await update.message.reply_text(
            f"✅ *Xush kelibsiz, {user['name']}!*\n\n"
            f"📧 {email}",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Email yoki parol noto'g'ri!\n\nQayta urinib ko'ring:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Qayta kirish", callback_data="auth_login")],
                [InlineKeyboardButton("🆕 Akkaunt yaratish", callback_data="auth_register")]
            ])
        )
        return AUTH_MENU


STATES = {
    AUTH_MENU: [
        CallbackQueryHandler(register_start, pattern="^auth_register$"),
        CallbackQueryHandler(login_start, pattern="^auth_login$"),
    ],
    REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
    REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_email)],
    REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
    LOGIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_email)],
    LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
}
