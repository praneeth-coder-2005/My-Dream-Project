import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# Function to fetch posts from WordPress
def fetch_wordpress_posts():
    try:
        response = requests.get(
            POSTS_API_ENDPOINT,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        return []

# Function to update a post in WordPress
def update_wordpress_post(post_id, updated_content):
    try:
        headers = {"Content-Type": "application/json"}
        data = {"content": updated_content}
        response = requests.post(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            headers=headers,
            json=data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        return response.status_code == 200
    except Exception as e:
        return False

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /list_posts to view WordPress posts.")

async def list_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = fetch_wordpress_posts()
    if posts:
        keyboard = [
            [InlineKeyboardButton(post["title"]["rendered"], callback_data=f"post_{post['id']}")]
            for post in posts[:10]
        ]
        await update.message.reply_text(
            "Here are your WordPress posts. Select one to edit, delete, or add a download link:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("No posts found in WordPress.")

async def handle_post_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    keyboard = [
        [InlineKeyboardButton("Edit Post", callback_data=f"edit_{post_id}")],
        [InlineKeyboardButton("Delete Post", callback_data=f"delete_{post_id}")],
        [InlineKeyboardButton("Add Download Link", callback_data=f"addlink_{post_id}")]
    ]
    await query.edit_message_text(
        f"What would you like to do with Post ID {post_id}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_add_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addlink_post_id"] = post_id
    await query.edit_message_text("Send the title for the download link:")

async def handle_download_link_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_id = context.user_data.get("addlink_post_id")
    if post_id:
        context.user_data["download_link_title"] = update.message.text
        await update.message.reply_text("Send the URL for the download link:")

async def handle_download_link_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_id = context.user_data.get("addlink_post_id")
    title = context.user_data.get("download_link_title")
    if post_id and title:
        url = update.message.text
        # Fetch the current content of the post
        post_response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if post_response.status_code == 200:
            post_content = post_response.json().get("content", {}).get("rendered", "")
            # Add the download button
            new_content = f"{post_content}<br><a href='{url}' style='display:inline-block;padding:10px 20px;color:white;background-color:blue;text-decoration:none;'>{title}</a>"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Download link added successfully to Post {post_id}!")
            else:
                await update.message.reply_text(f"Failed to add download link to Post {post_id}.")
        else:
            await update.message.reply_text("Failed to fetch post content.")
        # Clear user data after completing the process
        context.user_data.pop("addlink_post_id", None)
        context.user_data.pop("download_link_title", None)
    else:
        await update.message.reply_text("No post or title selected for adding a download link.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_"))
    application.add_handler(CallbackQueryHandler(handle_add_download_link, pattern="^addlink_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download_link_title))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download_link_url))

    application.run_polling()

if __name__ == "__main__":
    main()
