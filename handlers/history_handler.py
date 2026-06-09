from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from datetime import datetime
import database as db

(HISTORY_MENU, HISTORY_DATE_SELECT, HISTORY_CUSTOM_DATE) = range(3)

STATES = {}


async def history_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    today = datetime.now().strftime("%Y-%m-%d")
    summary = db.get_history_summary(today)
    dates = db.get_available_dates()

    kb = []

    # Tezkor tugmalar
    kb.append([
        InlineKeyboardButton("📅 Bugun", callback_data=f"hist_date_{today}"),
        InlineKeyboardButton("📆 Sana kiriting", callback_data="hist_custom")
    ])

    # So'nggi sanalar
    if dates:
        kb.append([InlineKeyboardButton("── So'nggi sanalar ──", callback_data="noop")])
        for d in dates[:7]:
            s = db.get_history_summary(d)
            label = f"📋 {d} | {s['order_count']} ta | {s['total_sum']:,.0f} so'm"
            kb.append([InlineKeyboardButton(label, callback_data=f"hist_date_{d}")])

    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])

    # Bugungi qisqa statistika
    text = (
        f"📊 *Tarix*\n\n"
        f"📅 Bugun ({today}):\n"
        f"• Buyurtmalar: *{summary['order_count']} ta*\n"
        f"• Jami savdo: *{summary['total_sum']:,.0f} so'm*\n"
        f"• To'langan: *{summary['paid_sum']:,.0f} so'm*\n"
        f"• Qarz: *{summary['debt_sum']:,.0f} so'm*\n\n"
        "Sana tanlang:"
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return HISTORY_MENU


async def history_date_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "noop":
        return HISTORY_MENU

    date_str = query.data.replace("hist_date_", "")
    orders = db.get_daily_history(date_str)
    summary = db.get_history_summary(date_str)

    lines = [f"📋 *{date_str} — Kunlik hisobot*\n"]

    if not orders:
        lines.append("❌ Bu kunda buyurtma yo'q.")
    else:
        lines.append(
            f"📦 Buyurtmalar: *{summary['order_count']} ta*\n"
            f"🔢 Jami dona: *{summary['total_qty']}*\n"
            f"💵 Jami savdo: *{summary['total_sum']:,.0f} so'm*\n"
            f"✅ To'langan: *{summary['paid_sum']:,.0f} so'm*\n"
            f"💸 Qarz: *{summary['debt_sum']:,.0f} so'm*\n"
        )

        lines.append("─" * 30)
        lines.append("📌 *Tafsilot:*\n")

        for i, o in enumerate(orders, 1):
            time_str = o["created_at"][11:16] if len(o["created_at"]) > 10 else ""
            debt_str = f" | 💸Qarz: {o['debt']:,.0f}" if o["debt"] > 0 else ""
            lines.append(
                f"{i}. *{o['shop_name']}*\n"
                f"   🕐 {time_str} | {o['product_name']} × {o['quantity']} {o['unit']}\n"
                f"   💰 {o['total']:,.0f} so'm{debt_str}"
            )
            if o["note"]:
                lines.append(f"   💬 {o['note']}")

    text = "\n".join(lines)

    # Telegram 4096 belgidan uzun bo'lsa kesish
    if len(text) > 4000:
        text = text[:3900] + "\n\n... (qisqartirildi)"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Tarixga qaytish", callback_data="history")]
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return HISTORY_DATE_SELECT


async def history_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📆 *Sana kiriting*\n\nFormat: *YYYY-MM-DD*\nMasalan: *2025-01-15*",
        parse_mode="Markdown"
    )
    return HISTORY_CUSTOM_DATE


async def history_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri format. *YYYY-MM-DD* formatida kiriting:\nMasalan: *2025-01-15*",
            parse_mode="Markdown"
        )
        return HISTORY_CUSTOM_DATE

    orders = db.get_daily_history(text)
    summary = db.get_history_summary(text)

    lines = [f"📋 *{text} — Kunlik hisobot*\n"]

    if not orders:
        lines.append("❌ Bu kunda buyurtma yo'q.")
    else:
        lines.append(
            f"📦 Buyurtmalar: *{summary['order_count']} ta*\n"
            f"💵 Jami savdo: *{summary['total_sum']:,.0f} so'm*\n"
            f"✅ To'langan: *{summary['paid_sum']:,.0f} so'm*\n"
            f"💸 Qarz: *{summary['debt_sum']:,.0f} so'm*\n"
        )
        lines.append("─" * 30)
        for i, o in enumerate(orders, 1):
            time_str = o["created_at"][11:16]
            debt_str = f" | 💸{o['debt']:,.0f}" if o["debt"] > 0 else ""
            lines.append(
                f"{i}. *{o['shop_name']}* — {time_str}\n"
                f"   {o['product_name']} × {o['quantity']} {o['unit']} | {o['total']:,.0f} so'm{debt_str}"
            )

    result = "\n".join(lines)
    if len(result) > 4000:
        result = result[:3900] + "\n\n... (qisqartirildi)"

    from handlers.start_handler import main_menu_keyboard
    await update.message.reply_text(result, parse_mode="Markdown")
    await update.message.reply_text("Asosiy menyu:", reply_markup=main_menu_keyboard())
    return HISTORY_MENU


STATES = {
    HISTORY_MENU: [
        CallbackQueryHandler(history_date_view, pattern="^hist_date_"),
        CallbackQueryHandler(history_custom_start, pattern="^hist_custom$"),
        CallbackQueryHandler(lambda u, c: None, pattern="^noop$"),
        CallbackQueryHandler(history_menu, pattern="^history$"),
    ],
    HISTORY_DATE_SELECT: [
        CallbackQueryHandler(history_menu, pattern="^history$"),
    ],
    HISTORY_CUSTOM_DATE: [
        MessageHandler(filters.TEXT & ~filters.COMMAND, history_custom_date)
    ],
}
