import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)
from config import BOT_TOKEN
from handlers import (
    start_handler, auth_handler, shops_handler, products_handler,
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

    # Orders - to'liq ConversationHandler ICHIDA
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(orders_handler.orders_menu, pattern="^orders$")],
        states={
            1: [CallbackQueryHandler(orders_handler.order_select_shop, pattern="^ord_shop_")],
            2: [CallbackQueryHandler(orders_handler.order_select_product, pattern="^ord_prod_")],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, orders_handler.order_text_handler)],
            4: [CallbackQueryHandler(orders_handler.order_discount_type, pattern="^disc_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, orders_handler.order_text_handler)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, orders_handler.order_text_handler)],
            6: [MessageHandler(filters.TEXT & ~filters.COMMAND, orders_handler.order_text_handler)],
            7: [CallbackQueryHandler(orders_handler.order_save, pattern="^ord_save$"),
                CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        },
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(order_conv)

    # Auth
    auth_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(auth_handler.register_start, pattern="^auth_register$"),
            CallbackQueryHandler(auth_handler.login_start, pattern="^auth_login$"),
        ],
        states=auth_handler.STATES,
        fallbacks=[CommandHandler("start", start_handler.start)],
        allow_reentry=True
    )
    app.add_handler(auth_conv)

    # Shops
    shop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(shops_handler.shops_menu, pattern="^shops$")],
        states=shops_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(shop_conv)

    # Products
    product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(products_handler.products_menu, pattern="^products$")],
        states=products_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(product_conv)

    # Debtors
    debtor_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(debtors_handler.debtors_menu, pattern="^debtors$")],
        states=debtors_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(debtor_conv)

    # History
    history_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(history_handler.history_menu, pattern="^history$")],
        states=history_handler.STATES,
        fallbacks=[CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$")],
        allow_reentry=True
    )
    app.add_handler(history_conv)

    app.add_handler(CallbackQueryHandler(start_handler.back_to_main, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(start_handler.back_to_main, pattern="^logout$"))

    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
