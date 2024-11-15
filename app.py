import os
from flask import Flask
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

app = Flask(__name__)
TOKEN = "8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo"  # Replace this with your bot token

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Import feature handlers from other files
    from features.list_posts import list_posts_handler
    from features.download_links import handle_add_download_link
    from features.video_player import handle_add_video_player
    from features.edit_delete import handle_edit_post, handle_delete_post
    from features.search_movie import handle_search

    # Register commands and handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_posts", list_posts_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    application.add_handler(CallbackQueryHandler(handle_edit_post, pattern="^edit_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_delete_post, pattern="^delete_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_download_link, pattern="^addlink_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))

    # Ensure app binds to Heroku's $PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
