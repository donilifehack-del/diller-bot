from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import database as db

(DEBTOR_LIST, DEBTOR_DETAIL, DEBTOR_PAYMENT_AMOUNT, DEBTOR_PAYMENT_NOTE) = range(4)

STATES = {}


def debtors_keyboard(debtors):
    kb = []
    for d in debtors:
        label = f"🏪 {d['name']} — 💸 {d['total_debt']:,.0f} so'm"
        kb.append([InlineKeyboardButton(label, callback_data=f"debt_view_{d['id']}")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb)


async def debtors_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    debtors = db.get_debtors()
    if not debtors:
        await query.edit_message_text(
            "✅ *Hech qanday qarzdor yo'q!*\nBarcha to'lovlar amalga oshirilgan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )
        return DEBTOR_LIST

    total_all = sum(d["total_debt"] for d in debtors)
    text = (
        f"💸 *Qarzdorlar* — {len(debtors)} ta dokon\n"
        f"📊 Umumiy qarz: *{total_all:,.0f} so'm*\n\n"
        "Dokon tanlang:"
    )
    await query.edit_message_text(text, reply_markup=debtors_keyboard(debtors), parse_mode="Markdown")
    return DEBTOR_LIST


async def debtor_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split("_")[-1])
    shop = db.get_shop(shop_id)
    orders = db.get_shop_debt_detail(shop_id)
    total_debt = db.get_shop_total_debt(shop_id)
    payments = db.get_payments(shop_id)

    context.user_data["pay_shop_id"] = shop_id
    context.user_data["pay_shop_name"] = shop["name"]

    lines = [f"💸 *{shop['name']}* — Qarz tafsiloti\n"]
    lines.append(f"📊 Jami qarz: *{total_debt:,.0f} so'm*\n")

    lines.append("\n📋 *Buyurtmalar:*")
    for i, o in enumerate(orders[:10], 1):
        lines.append(
            f"{i}. {o['created_at'][:10]} | {o['product_name']} × {o['quantity']} {o['unit']}\n"
            f"   Jami: {o['total']:,.0f} | To'langan: {o['paid']:,.0f} | *Qarz: {o['debt']:,.0f}*"
        )

    if payments:
        lines.append("\n💰 *So'nggi to'lovlar:*")
        for p in payments[:5]:
            lines.append(f"• {p['created_at'][:10]}: *{p['amount']:,.0f} so'm*" + (f" ({p['note']})" if p['note'] else ""))

    text = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 To'lov qabul qilish", callback_data=f"debt_pay_{shop_id}")],
        [InlineKeyboardButton("🔙 Qarzdorlar", callback_data="debtors")]
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return DEBTOR_DETAIL


async def debtor_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split("_")[-1])
    context.user_data["pay_shop_id"] = shop_id
    shop = db.get_shop(shop_id)
    debt = db.get_shop_total_debt(shop_id)
    context.user_data["pay_shop_name"] = shop["name"]

    await query.edit_message_text(
        f"💰 *{shop['name']}* dan to'lov qabul qilish\n"
        f"💸 Umumiy qarz: *{debt:,.0f} so'm*\n\n"
        "Qancha pul berildi?",
        parse_mode="Markdown"
    )
    return DEBTOR_PAYMENT_AMOUNT


async def debtor_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        if amount <= 0:
            await update.message.reply_text("❌ Musbat son kiriting:")
            return DEBTOR_PAYMENT_AMOUNT
        context.user_data["pay_amount"] = amount
        await update.message.reply_text("💬 Izoh kiriting (o'tkazish uchun '-' yozing):")
        return DEBTOR_PAYMENT_NOTE
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting:")
        return DEBTOR_PAYMENT_AMOUNT


async def debtor_payment_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    note = "" if note == "-" else note

    shop_id = context.user_data["pay_shop_id"]
    amount = context.user_data["pay_amount"]
    shop_name = context.user_data["pay_shop_name"]

    old_debt = db.get_shop_total_debt(shop_id)
    db.add_payment(shop_id, amount, note)
    new_debt = db.get_shop_total_debt(shop_id)

    msg = (
        f"✅ *To'lov qabul qilindi!*\n\n"
        f"🏪 Dokon: {shop_name}\n"
        f"💰 To'langan: *{amount:,.0f} so'm*\n"
        f"📉 Oldingi qarz: {old_debt:,.0f} so'm\n"
        f"📊 Qolgan qarz: *{new_debt:,.0f} so'm*"
    )
    if note:
        msg += f"\n💬 Izoh: {note}"

    debtors = db.get_debtors()
    if debtors:
        await update.message.reply_text(msg, parse_mode="Markdown")
        await update.message.reply_text("💸 Qarzdorlar:", reply_markup=debtors_keyboard(debtors))
    else:
        from handlers.start_handler import main_menu_keyboard
        await update.message.reply_text(
            msg + "\n\n✅ Barcha qarzlar to'landi!",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
    return DEBTOR_LIST


STATES = {
    DEBTOR_LIST: [
        CallbackQueryHandler(debtor_view, pattern="^debt_view_"),
        CallbackQueryHandler(debtors_menu, pattern="^debtors$"),
    ],
    DEBTOR_DETAIL: [
        CallbackQueryHandler(debtor_payment_start, pattern="^debt_pay_"),
        CallbackQueryHandler(debtors_menu, pattern="^debtors$"),
    ],
    DEBTOR_PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, debtor_payment_amount)],
    DEBTOR_PAYMENT_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, debtor_payment_note)],
}
