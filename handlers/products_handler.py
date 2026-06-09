from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import database as db

(PRODUCT_MENU, ADD_PRODUCT_NAME, ADD_PRODUCT_PRICE,
 ADD_PRODUCT_QTY, ADD_PRODUCT_UNIT, VIEW_PRODUCT,
 UPDATE_PRICE, ADD_STOCK, DELETE_CONFIRM) = range(9)

STATES = {}


def products_keyboard(products):
    kb = []
    for p in products:
        status = "✅" if p["quantity"] > 0 else "❌"
        label = f"{status} {p['name']} — {p['quantity']} {p['unit']} | {p['price']:,.0f} so'm"
        kb.append([InlineKeyboardButton(label, callback_data=f"prod_view_{p['id']}")])
    kb.append([InlineKeyboardButton("➕ Tovar qo'shish", callback_data="prod_add")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb)


async def products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    products = db.get_products()
    text = f"📦 *Tovarlar ro'yxati* — {len(products)} ta\n\nTovar tanlang:"
    await query.edit_message_text(text, reply_markup=products_keyboard(products), parse_mode="Markdown")
    return PRODUCT_MENU


async def product_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[-1])
    p = db.get_product(prod_id)
    status = "✅ Mavjud" if p["quantity"] > 0 else "❌ Tugagan"

    text = (
        f"📦 *{p['name']}*\n"
        f"💰 Narx: *{p['price']:,.0f} so'm*\n"
        f"📊 Soni: *{p['quantity']} {p['unit']}*\n"
        f"📌 Holat: {status}\n"
        f"📅 Qo'shilgan: {p['created_at'][:10]}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Narxni o'zgartir", callback_data=f"prod_price_{prod_id}"),
         InlineKeyboardButton("📦 Stok qo'sh", callback_data=f"prod_stock_{prod_id}")],
        [InlineKeyboardButton("🗑 O'chirish", callback_data=f"prod_del_{prod_id}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="products")]
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return VIEW_PRODUCT


async def product_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📦 *Yangi tovar qo'shish*\n\nTovar nomini kiriting:", parse_mode="Markdown")
    return ADD_PRODUCT_NAME


async def product_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_name"] = update.message.text.strip()
    await update.message.reply_text("💰 Narxini kiriting (so'mda, masalan: 15000):")
    return ADD_PRODUCT_PRICE


async def product_add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        context.user_data["new_prod_price"] = price
        await update.message.reply_text("📊 Boshlang'ich sonini kiriting (masalan: 100):")
        return ADD_PRODUCT_QTY
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format. Raqam kiriting (masalan: 15000):")
        return ADD_PRODUCT_PRICE


async def product_add_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        context.user_data["new_prod_qty"] = qty
        await update.message.reply_text("📏 O'lchov birligini kiriting (dona / kg / litr / quti):")
        return ADD_PRODUCT_UNIT
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format. Butun son kiriting:")
        return ADD_PRODUCT_QTY


async def product_add_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    unit = update.message.text.strip()
    name = context.user_data["new_prod_name"]
    price = context.user_data["new_prod_price"]
    qty = context.user_data["new_prod_qty"]

    success = db.add_product(name, price, qty, unit)
    if success:
        msg = f"✅ *{name}* tovar qo'shildi!\nNarx: {price:,.0f} so'm | Soni: {qty} {unit}"
    else:
        msg = f"❌ *{name}* nomli tovar allaqachon mavjud!"

    products = db.get_products()
    await update.message.reply_text(msg, reply_markup=products_keyboard(products), parse_mode="Markdown")
    return PRODUCT_MENU


async def product_update_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[-1])
    context.user_data["edit_prod_id"] = prod_id
    p = db.get_product(prod_id)
    await query.edit_message_text(
        f"💰 *{p['name']}* tovar narxini o'zgartirish\nHozirgi narx: *{p['price']:,.0f} so'm*\n\nYangi narxni kiriting:",
        parse_mode="Markdown"
    )
    return UPDATE_PRICE


async def product_update_price_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        prod_id = context.user_data["edit_prod_id"]
        db.update_product_price(prod_id, new_price)
        p = db.get_product(prod_id)
        await update.message.reply_text(
            f"✅ *{p['name']}* narxi *{new_price:,.0f} so'm* ga o'zgartirildi!",
            parse_mode="Markdown"
        )
        products = db.get_products()
        await update.message.reply_text("📦 Tovarlar:", reply_markup=products_keyboard(products))
        return PRODUCT_MENU
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format. Raqam kiriting:")
        return UPDATE_PRICE


async def product_add_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[-1])
    context.user_data["stock_prod_id"] = prod_id
    p = db.get_product(prod_id)
    await query.edit_message_text(
        f"📦 *{p['name']}* — hozirgi son: *{p['quantity']} {p['unit']}*\n\nNechta qo'shmoqchisiz?",
        parse_mode="Markdown"
    )
    return ADD_STOCK


async def product_add_stock_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        prod_id = context.user_data["stock_prod_id"]
        db.update_product_quantity(prod_id, qty)
        p = db.get_product(prod_id)
        await update.message.reply_text(
            f"✅ *{p['name']}* ga *+{qty}* ta qo'shildi. Yangi soni: *{p['quantity']} {p['unit']}*",
            parse_mode="Markdown"
        )
        products = db.get_products()
        await update.message.reply_text("📦 Tovarlar:", reply_markup=products_keyboard(products))
        return PRODUCT_MENU
    except ValueError:
        await update.message.reply_text("❌ Butun son kiriting:")
        return ADD_STOCK


async def product_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[-1])
    p = db.get_product(prod_id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha", callback_data=f"prod_del_yes_{prod_id}"),
         InlineKeyboardButton("❌ Yo'q", callback_data=f"prod_view_{prod_id}")]
    ])
    await query.edit_message_text(
        f"⚠️ *{p['name']}* tovarini o'chirishni tasdiqlaysizmi?",
        reply_markup=kb, parse_mode="Markdown"
    )
    return DELETE_CONFIRM


async def product_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[-1])
    p = db.get_product(prod_id)
    db.delete_product(prod_id)
    products = db.get_products()
    await query.edit_message_text(
        f"🗑 *{p['name']}* o'chirildi.",
        reply_markup=products_keyboard(products),
        parse_mode="Markdown"
    )
    return PRODUCT_MENU


STATES = {
    PRODUCT_MENU: [
        CallbackQueryHandler(product_view, pattern="^prod_view_\\d+$"),
        CallbackQueryHandler(product_add_start, pattern="^prod_add$"),
    ],
    ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_add_name)],
    ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_add_price)],
    ADD_PRODUCT_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_add_qty)],
    ADD_PRODUCT_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_add_unit)],
    VIEW_PRODUCT: [
        CallbackQueryHandler(product_update_price_start, pattern="^prod_price_"),
        CallbackQueryHandler(product_add_stock_start, pattern="^prod_stock_"),
        CallbackQueryHandler(product_delete_confirm, pattern="^prod_del_\\d+$"),
        CallbackQueryHandler(products_menu, pattern="^products$"),
    ],
    UPDATE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_update_price_save)],
    ADD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_add_stock_save)],
    DELETE_CONFIRM: [
        CallbackQueryHandler(product_delete_yes, pattern="^prod_del_yes_"),
        CallbackQueryHandler(product_view, pattern="^prod_view_\\d+$"),
    ],
}
