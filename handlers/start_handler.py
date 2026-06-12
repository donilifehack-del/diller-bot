from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import init_db

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar login qilingan bo'lsa — asosiy menyuga
    if context.user_data.get("logged_in"):
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
            "Davom etish uchun akkauntingizga kiring\n"
            "yoki yangi akkaunt yarating:",
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

    # Agar login qilinmagan bo'lsa
    if not context.user_data.get("logged_in"):
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
