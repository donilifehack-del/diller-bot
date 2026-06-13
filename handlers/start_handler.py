from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import init_db, get_user_by_telegram_id

init_db()


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Dokonlar", callback_data="shops"),
         InlineKeyboardButton("📦 Tovarlar", callback_data="products")],
        [InlineKeyboardButton("🛒 Buyurtma berish", callback_data="orders")],
        [InlineKeyboardButton("💸 Qarzdorlar", callback_data="debtors"),
         InlineKeyboardButton("📊 Tarix", callback_data="history")],
        [InlineKeyboardButton("🚪 Chiqish", callback_data="logout")],
    ])


def check_auth(context, telegram_id):
    """Login tekshirish - user_data yoki DB dan"""
    if context.user_data.get("logged_in"):
        return True
    # DB dan tekshir
    user = get_user_by_telegram_id(telegram_id)
    if user:
        context.user_data["logged_in"] = True
        context.user_data["user_id"] = user["id"]
        context.user_data["user_name"] = user["name"]
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.message.from_user.id
    if check_auth(context, tg_id):
        name = context.user_data.get("user_name", "")
        await update.message.reply_text(
            f"👋 Xush kelibsiz, *{name}*!\n\nQuyidagi bo'limlardan birini tanlang:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        from handlers.auth_handler import auth_keyboard
        await update.message.reply_text(
            "👋 *Diller boshqaruv tizimi*\n\n"
            "Davom etish uchun akkauntingizga kiring:",
            reply_markup=auth_keyboard(),
            parse_mode="Markdown"
        )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "logout":
        context.user_data.clear()
        from handlers.auth_handler import auth_keyboard
        await query.edit_message_text(
            "🚪 *Chiqdingiz!*\n\nQayta kirish uchun:",
            reply_markup=auth_keyboard(),
            parse_mode="Markdown"
        )
        return

    tg_id = query.from_user.id
    if not check_auth(context, tg_id):
        from handlers.auth_handler import auth_keyboard
        await query.edit_message_text(
            "⚠️ Avval tizimga kiring!",
            reply_markup=auth_keyboard()
        )
        return

    name = context.user_data.get("user_name", "")
    await query.edit_message_text(
        f"👋 *{name}* — Asosiy menyu\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )
