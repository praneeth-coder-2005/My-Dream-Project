from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from features.edit_post import handle_edit_post
from features.delete_post import handle_delete_post
from features.add_download import handle_add_download_link
from features.add_video import handle_add_video_player
from features.search_post import handle_search
from utils.wordpress import list_posts
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "YOUR_BOT_TOKEN"

async def start(update, context):
    await update.message.reply_text(
        "Welcome to the WordPress Bot!\n\nCommands:\n"
        "/list_posts - List all posts\n"
        "Send a movie name to search and post directly\n"
        "Manage posts with buttons."
    )

async def list_posts_handler(update, context):
    posts = list_posts()
    if posts:
        buttons = [
            [InlineKeyboardButton(post['title']['rendered'], callback_data=f"post_{post['id']}")]
            for post in posts
        ]
        await update.message.reply_text(
            "Select a post to manage:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.message.reply_text("No posts found.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_posts", list_posts_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    application.add_handler(CallbackQueryHandler(handle_edit_post, pattern="^edit_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_delete_post, pattern="^delete_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_download_link, pattern="^addlink_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))

    application.run_polling()

if __name__ == "__main__":
    main()
