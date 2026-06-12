from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import database as db

(ORDER_SELECT_SHOP, ORDER_SELECT_PRODUCT, ORDER_ENTER_QTY,
 ORDER_DISCOUNT, ORDER_DISCOUNT_VALUE, ORDER_ENTER_PAID,
 ORDER_NOTE, ORDER_CONFIRM) = range(8)

STATES = {}


def shops_kb():
    shops = db.get_shops()
    kb = [[InlineKeyboardButton(f"🏪 {s['name']}", callback_data=f"ord_shop_{s['id']}")] for s in shops]
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb), shops


def products_kb():
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

    if not context.user_data.get("logged_in"):
        from handlers.auth_handler import auth_keyboard
        await query.edit_message_text("⚠️ Avval tizimga kiring!", reply_markup=auth_keyboard())
        return ConversationHandler.END

    context.user_data.pop("ord_shop_id", None)
    context.user_data.pop("ord_prod_id", None)

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
        context.user_data["ord_total_original"] = total

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏷 Foizda skidka (%)", callback_data="disc_percent")],
            [InlineKeyboardButton("💵 So'mda skidka", callback_data="disc_sum")],
            [InlineKeyboardButton("❌ Skidkasiz", callback_data="disc_none")],
        ])
        await update.message.reply_text(
            f"📊 Soni: *{qty} {context.user_data['ord_prod_unit']}*\n"
            f"💰 Jami: *{total:,.0f} so'm*\n\n"
            "🏷 Skidka bormi?",
            reply_markup=kb, parse_mode="Markdown"
        )
        return ORDER_DISCOUNT
    except ValueError:
        await update.message.reply_text("❌ Butun son kiriting:")
        return ORDER_ENTER_QTY


async def order_discount_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    disc_type = query.data.replace("disc_", "")

    if disc_type == "none":
        context.user_data["ord_discount_type"] = "none"
        context.user_data["ord_discount_value"] = 0
        context.user_data["ord_total"] = context.user_data["ord_total_original"]
        await query.edit_message_text(
            f"💰 Jami summa: *{context.user_data['ord_total']:,.0f} so'm*\n\n"
            "Qancha pul to'landi? (Hammasi to'langan bo'lsa raqamni, qarz bo'lsa 0 yozing):",
            parse_mode="Markdown"
        )
        return ORDER_ENTER_PAID

    context.user_data["ord_discount_type"] = disc_type
    if disc_type == "percent":
        await query.edit_message_text("🏷 Necha foiz skidka? (masalan: 10):")
    else:
        await query.edit_message_text("💵 Necha so'm skidka? (masalan: 5000):")
    return ORDER_DISCOUNT_VALUE


async def order_discount_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        disc_type = context.user_data["ord_discount_type"]
        original = context.user_data["ord_total_original"]

        if disc_type == "percent":
            if val <= 0 or val >= 100:
                await update.message.reply_text("❌ Foiz 1-99 orasida bo'lishi kerak:")
                return ORDER_DISCOUNT_VALUE
            discount_amount = original * val / 100
            disc_label = f"{val:.0f}%"
        else:
            if val <= 0 or val >= original:
                await update.message.reply_text(f"❌ Skidka 0 dan {original:,.0f} so'mgacha bo'lishi kerak:")
                return ORDER_DISCOUNT_VALUE
            discount_amount = val
            disc_label = f"{val:,.0f} so'm"

        context.user_data["ord_discount_value"] = val
        context.user_data["ord_discount_label"] = disc_label
        new_total = original - discount_amount
        context.user_data["ord_total"] = new_total

        await update.message.reply_text(
            f"🏷 Skidka: *{disc_label}* (-{discount_amount:,.0f} so'm)\n"
            f"💰 Yangi jami: *{new_total:,.0f} so'm*\n\n"
            "Qancha pul to'landi? (Hammasi to'langan bo'lsa raqamni, qarz bo'lsa 0 yozing):",
            parse_mode="Markdown"
        )
        return ORDER_ENTER_PAID
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting:")
        return ORDER_DISCOUNT_VALUE


async def order_enter_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        paid = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        total = context.user_data["ord_total"]
        if paid < 0:
            await update.message.reply_text("❌ Manfiy bo'lmasin:")
            return ORDER_ENTER_PAID
        if paid > total:
            await update.message.reply_text(f"❌ To'lov ({paid:,.0f}) jami ({total:,.0f}) dan ko'p bo'lishi mumkin emas:")
            return ORDER_ENTER_PAID

        context.user_data["ord_paid"] = paid
        await update.message.reply_text("💬 Izoh kiriting (o'tkazib yuborish uchun '-' yozing):")
        return ORDER_NOTE
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting:")
        return ORDER_ENTER_PAID


async def order_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    context.user_data["ord_note"] = "" if note == "-" else note

    d = context.user_data
    total = d["ord_total"]
    original = d["ord_total_original"]
    paid = d["ord_paid"]
    debt = total - paid
    disc_type = d.get("ord_discount_type", "none")

    text = (
        f"📋 *Buyurtma tasdiqi*\n\n"
        f"🏪 Dokon: *{d['ord_shop_name']}*\n"
        f"📦 Tovar: *{d['ord_prod_name']}*\n"
        f"📊 Soni: *{d['ord_qty']} {d['ord_prod_unit']}*\n"
        f"💰 Narx: *{d['ord_prod_price']:,.0f} so'm*\n"
    )
    if disc_type != "none":
        text += f"🏷 Skidka: *{d.get('ord_discount_label', '')}* (-{original - total:,.0f} so'm)\n"
    text += (
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
        discount_type=d.get("ord_discount_type", "none"),
        discount_value=d.get("ord_discount_value", 0),
        paid=d["ord_paid"],
        note=d.get("ord_note", ""),
        created_by=d.get("user_id")
    )

    debt = d["ord_total"] - d["ord_paid"]
    msg = (
        f"✅ *Buyurtma saqlandi!*\n\n"
        f"🏪 {d['ord_shop_name']} — {d['ord_prod_name']} × {d['ord_qty']}\n"
        f"💵 Jami: {d['ord_total']:,.0f} so'm\n"
    )
    if d.get("ord_discount_type", "none") != "none":
        msg += f"🏷 Skidka: {d.get('ord_discount_label', '')}\n"
    if debt > 0:
        msg += f"💸 Qarz: *{debt:,.0f} so'm* (Qarzdorlar bo'limiga qo'shildi)"

    from handlers.start_handler import main_menu_keyboard
    await query.edit_message_text(msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    # Eski order ma'lumotlarini tozalash, lekin login ma'lumotlarini saqlash
    keys_to_remove = [k for k in context.user_data if k.startswith("ord_")]
    for k in keys_to_remove:
        del context.user_data[k]

    return ConversationHandler.END


STATES = {
    ORDER_SELECT_SHOP: [CallbackQueryHandler(order_select_shop, pattern="^ord_shop_")],
    ORDER_SELECT_PRODUCT: [CallbackQueryHandler(order_select_product, pattern="^ord_prod_")],
    ORDER_ENTER_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_enter_qty)],
    ORDER_DISCOUNT: [CallbackQueryHandler(order_discount_type, pattern="^disc_")],
    ORDER_DISCOUNT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_discount_value)],
    ORDER_ENTER_PAID: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_enter_paid)],
    ORDER_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_note)],
    ORDER_CONFIRM: [CallbackQueryHandler(order_confirm, pattern="^ord_confirm$")],
}
