from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import database as db

# States
(SHOP_MENU, ADD_SHOP_NAME, ADD_SHOP_PHONE, ADD_SHOP_ADDRESS,
 VIEW_SHOP, DELETE_SHOP_CONFIRM) = range(6)

STATES = {}


def shops_keyboard(shops):
    kb = []
    for s in shops:
        debt = db.get_shop_total_debt(s["id"])
        label = f"🏪 {s['name']}"
        if debt > 0:
            label += f" (💸 {debt:,.0f} so'm)"
        kb.append([InlineKeyboardButton(label, callback_data=f"shop_view_{s['id']}")])
    kb.append([InlineKeyboardButton("➕ Dokon qo'shish", callback_data="shop_add")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb)


async def shops_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shops = db.get_shops()
    text = f"🏪 *Dokonlar ro'yxati* — {len(shops)} ta\n\nDokon tanlang yoki yangi qo'shing:"
    await query.edit_message_text(text, reply_markup=shops_keyboard(shops), parse_mode="Markdown")
    return SHOP_MENU


async def shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split("_")[-1])
    shop = db.get_shop(shop_id)
    debt = db.get_shop_total_debt(shop_id)
    orders = db.get_orders(shop_id)

    text = (
        f"🏪 *{shop['name']}*\n"
        f"📞 Tel: {shop['phone'] or 'kiritilmagan'}\n"
        f"📍 Manzil: {shop['address'] or 'kiritilmagan'}\n"
        f"📋 Jami buyurtmalar: {len(orders)} ta\n"
        f"💸 Qarz: *{debt:,.0f} so'm*\n"
        f"📅 Qo'shilgan: {shop['created_at'][:10]}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 O'chirish", callback_data=f"shop_del_{shop_id}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="shops")]
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return VIEW_SHOP


async def shop_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏪 *Yangi dokon qo'shish*\n\nDokon nomini kiriting:",
        parse_mode="Markdown"
    )
    return ADD_SHOP_NAME


async def shop_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shop_name"] = update.message.text.strip()
    await update.message.reply_text("📞 Telefon raqamini kiriting (o'tkazib yuborish uchun '-' yozing):")
    return ADD_SHOP_PHONE


async def shop_add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data["new_shop_phone"] = "" if phone == "-" else phone
    await update.message.reply_text("📍 Manzilni kiriting (o'tkazib yuborish uchun '-' yozing):")
    return ADD_SHOP_ADDRESS


async def shop_add_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    context.user_data["new_shop_address"] = "" if address == "-" else address

    name = context.user_data["new_shop_name"]
    phone = context.user_data.get("new_shop_phone", "")
    addr = context.user_data.get("new_shop_address", "")

    success = db.add_shop(name, phone, addr)
    if success:
        msg = f"✅ *{name}* dokon muvaffaqiyatli qo'shildi!"
    else:
        msg = f"❌ *{name}* nomli dokon allaqachon mavjud!"

    shops = db.get_shops()
    await update.message.reply_text(
        msg + "\n\n🏪 Dokonlar ro'yxati:",
        reply_markup=shops_keyboard(shops),
        parse_mode="Markdown"
    )
    return SHOP_MENU


async def shop_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split("_")[-1])
    shop = db.get_shop(shop_id)
    context.user_data["del_shop_id"] = shop_id

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"shop_del_yes_{shop_id}"),
         InlineKeyboardButton("❌ Yo'q", callback_data=f"shop_view_{shop_id}")]
    ])
    await query.edit_message_text(
        f"⚠️ *{shop['name']}* dokonini o'chirishni tasdiqlaysizmi?\n"
        "Barcha buyurtmalar ham o'chadi!",
        reply_markup=kb, parse_mode="Markdown"
    )
    return DELETE_SHOP_CONFIRM


async def shop_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split("_")[-1])
    shop = db.get_shop(shop_id)
    db.delete_shop(shop_id)

    shops = db.get_shops()
    await query.edit_message_text(
        f"🗑 *{shop['name']}* o'chirildi.\n\n🏪 Dokonlar ro'yxati:",
        reply_markup=shops_keyboard(shops),
        parse_mode="Markdown"
    )
    return SHOP_MENU


STATES = {
    SHOP_MENU: [
        CallbackQueryHandler(shop_view, pattern="^shop_view_"),
        CallbackQueryHandler(shop_add_start, pattern="^shop_add$"),
        CallbackQueryHandler(shop_delete_confirm, pattern="^shop_del_\\d+$"),
        CallbackQueryHandler(shop_delete_yes, pattern="^shop_del_yes_"),
    ],
    ADD_SHOP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, shop_add_name)],
    ADD_SHOP_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, shop_add_phone)],
    ADD_SHOP_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, shop_add_address)],
    VIEW_SHOP: [
        CallbackQueryHandler(shop_delete_confirm, pattern="^shop_del_\\d+$"),
        CallbackQueryHandler(shop_delete_yes, pattern="^shop_del_yes_"),
        CallbackQueryHandler(shops_menu, pattern="^shops$"),
    ],
    DELETE_SHOP_CONFIRM: [
        CallbackQueryHandler(shop_delete_yes, pattern="^shop_del_yes_"),
        CallbackQueryHandler(shop_view, pattern="^shop_view_"),
    ],
}
