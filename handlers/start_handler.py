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
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Diller boshqaruv botiga xush kelibsiz!*\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "👋 *Asosiy menyu*\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )
