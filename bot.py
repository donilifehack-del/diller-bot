import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)
from config import BOT_TOKEN
from handlers import (
    start_handler, shops_handler, products_handler,
    orders_handler, debtors_handler, history_handler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler.start))

    shop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(shops_handler.shops_menu, pattern="^shops$")],
        states=shops_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(shop_conv)

    product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(products_handler.products_menu, pattern="^products$")],
        states=products_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(product_conv)

    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(orders_handler.orders_menu, pattern="^orders$")],
        states=orders_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(order_conv)

    debtor_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(debtors_handler.debtors_menu, pattern="^debtors$")],
        states=debtors_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(debtor_conv)

    history_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(history_handler.history_menu, pattern="^history$")],
        states=history_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(history_conv)

    app.add_handler(CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$"))

    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
