from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import database as db

(ORDER_SELECT_SHOP, ORDER_SELECT_PRODUCT, ORDER_ENTER_QTY,
 ORDER_ENTER_PAID, ORDER_CONFIRM, ORDER_NOTE) = range(6)

STATES = {}


def shops_kb():
    shops = db.get_shops()
    kb = [[InlineKeyboardButton(f"🏪 {s['name']}", callback_data=f"ord_shop_{s['id']}")] for s in shops]
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb), shops


def products_kb(selected_ids=None):
    products = db.get_products()
    available = [p for p in products if p["quantity"] > 0]
    kb = []
    for p in available:
        label = f"📦 {p['name']} — {p['quantity']} {p['unit']} | {p['price']:,.0f} so'm"
        kb.append([InlineKeyboardButton(label, callback_data=f"ord_prod_{p['id']}")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="orders")])
    return InlineKeyboardMarkup(kb), available


async def orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    kb, shops = shops_kb()
    if not shops:
        await query.edit_message_text(
            "❌ Hech qanday dokon yo'q. Avval dokon qo'shing!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]])
        )
        return ConversationHandler.END
    await query.edit_message_text(
        "🛒 *Yangi buyurtma*\n\nQaysi dokonga yuboryapsiz?",
        reply_markup=kb, parse_mode="Markdown"
    )
    return ORDER_SELECT_SHOP


async def order_select_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split("_")[-1])
    shop = db.get_shop(shop_id)
    context.user_data["ord_shop_id"] = shop_id
    context.user_data["ord_shop_name"] = shop["name"]

    kb, available = products_kb()
    if not available:
        await query.edit_message_text(
            "❌ Omborda tovar yo'q. Avval tovar qo'shing!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]])
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"🏪 Dokon: *{shop['name']}*\n\nQaysi tovarni yuborasiz?",
        reply_markup=kb, parse_mode="Markdown"
    )
    return ORDER_SELECT_PRODUCT


async def order_select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[-1])
    prod = db.get_product(prod_id)
    context.user_data["ord_prod_id"] = prod_id
    context.user_data["ord_prod_name"] = prod["name"]
    context.user_data["ord_prod_price"] = prod["price"]
    context.user_data["ord_prod_unit"] = prod["unit"]
    context.user_data["ord_prod_qty_avail"] = prod["quantity"]

    await query.edit_message_text(
        f"🏪 Dokon: *{context.user_data['ord_shop_name']}*\n"
        f"📦 Tovar: *{prod['name']}*\n"
        f"💰 Narx: *{prod['price']:,.0f} so'm/{prod['unit']}*\n"
        f"📊 Mavjud: *{prod['quantity']} {prod['unit']}*\n\n"
        "Nechta yuborasiz?",
        parse_mode="Markdown"
    )
    return ORDER_ENTER_QTY


async def order_enter_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        avail = context.user_data["ord_prod_qty_avail"]
        if qty <= 0:
            await update.message.reply_text("❌ Son 0 dan katta bo'lishi kerak:")
            return ORDER_ENTER_QTY
        if qty > avail:
            await update.message.reply_text(f"❌ Omborda faqat {avail} ta bor. Kamroq kiriting:")
            return ORDER_ENTER_QTY

        context.user_data["ord_qty"] = qty
        total = qty * context.user_data["ord_prod_price"]
        context.user_data["ord_total"] = total

        await update.message.reply_text(
            f"📊 Soni: *{qty} {context.user_data['ord_prod_unit']}*\n"
            f"💰 Jami summa: *{total:,.0f} so'm*\n\n"
            "Qancha pul to'landi? (Hammasi to'langan bo'lsa raqamni, qarz bo'lsa 0 yozing):",
            parse_mode="Markdown"
        )
        return ORDER_ENTER_PAID
    except ValueError:
        await update.message.reply_text("❌ Butun son kiriting:")
        return ORDER_ENTER_QTY


async def order_enter_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        paid = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        total = context.user_data["ord_total"]
        if paid < 0:
            await update.message.reply_text("❌ Manfiy bo'lmasin:")
            return ORDER_ENTER_PAID
        if paid > total:
            await update.message.reply_text(f"❌ To'lov ({paid:,.0f}) jami summa ({total:,.0f}) dan ko'p bo'lishi mumkin emas:")
            return ORDER_ENTER_PAID

        context.user_data["ord_paid"] = paid
        debt = total - paid

        await update.message.reply_text(
            f"💬 Izoh kiriting yoki o'tkazib yuborish uchun '-' yozing:"
        )
        return ORDER_NOTE
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting:")
        return ORDER_ENTER_PAID


async def order_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    context.user_data["ord_note"] = "" if note == "-" else note

    d = context.user_data
    total = d["ord_total"]
    paid = d["ord_paid"]
    debt = total - paid

    text = (
        f"📋 *Buyurtma tasdiqi*\n\n"
        f"🏪 Dokon: *{d['ord_shop_name']}*\n"
        f"📦 Tovar: *{d['ord_prod_name']}*\n"
        f"📊 Soni: *{d['ord_qty']} {d['ord_prod_unit']}*\n"
        f"💰 Narx: *{d['ord_prod_price']:,.0f} so'm*\n"
        f"💵 Jami: *{total:,.0f} so'm*\n"
        f"✅ To'langan: *{paid:,.0f} so'm*\n"
        f"💸 Qarz: *{debt:,.0f} so'm*\n"
    )
    if d["ord_note"]:
        text += f"💬 Izoh: {d['ord_note']}\n"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data="ord_confirm"),
         InlineKeyboardButton("❌ Bekor qilish", callback_data="main_menu")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    return ORDER_CONFIRM


async def order_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    d = context.user_data

    db.add_order(
        shop_id=d["ord_shop_id"],
        product_id=d["ord_prod_id"],
        quantity=d["ord_qty"],
        price=d["ord_prod_price"],
        paid=d["ord_paid"],
        note=d.get("ord_note", "")
    )

    debt = d["ord_total"] - d["ord_paid"]
    msg = (
        f"✅ *Buyurtma saqlandi!*\n\n"
        f"🏪 {d['ord_shop_name']} — {d['ord_prod_name']} × {d['ord_qty']}\n"
        f"💵 Jami: {d['ord_total']:,.0f} so'm\n"
    )
    if debt > 0:
        msg += f"💸 Qarz: *{debt:,.0f} so'm* (Qarzdorlar bo'limiga qo'shildi)"

    from handlers.start_handler import main_menu_keyboard
    await query.edit_message_text(msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


STATES = {
    ORDER_SELECT_SHOP: [CallbackQueryHandler(order_select_shop, pattern="^ord_shop_")],
    ORDER_SELECT_PRODUCT: [CallbackQueryHandler(order_select_product, pattern="^ord_prod_")],
    ORDER_ENTER_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_enter_qty)],
    ORDER_ENTER_PAID: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_enter_paid)],
    ORDER_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_note)],
    ORDER_CONFIRM: [
        CallbackQueryHandler(order_confirm, pattern="^ord_confirm$"),
    ],
}
