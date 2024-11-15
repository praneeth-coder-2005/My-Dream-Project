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

# Function to delete a post from WordPress
def delete_wordpress_post(post_id):
    try:
        response = requests.delete(
            f"{POSTS_API_ENDPOINT}/{post_id}?force=true",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        return response.status_code == 200
    except Exception as e:
        return False

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
            "Here are your WordPress posts. Select one to edit or delete:",
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
        [InlineKeyboardButton("Delete Post", callback_data=f"delete_{post_id}")]
    ]
    await query.edit_message_text(
        f"What would you like to do with Post ID {post_id}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_post_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["edit_post_id"] = post_id

    await query.edit_message_text("Send the updated content for this post:")

async def handle_new_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_id = context.user_data.get("edit_post_id")
    if post_id:
        updated_content = update.message.text
        success = update_wordpress_post(post_id, updated_content)
        if success:
            await update.message.reply_text(f"Post {post_id} updated successfully!")
        else:
            await update.message.reply_text(f"Failed to update Post {post_id}.")
        context.user_data.pop("edit_post_id", None)
    else:
        await update.message.reply_text("No post is being edited currently.")

async def handle_post_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    success = delete_wordpress_post(post_id)
    if success:
        await query.edit_message_text(f"Post {post_id} deleted successfully!")
    else:
        await query.edit_message_text(f"Failed to delete Post {post_id}.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_"))
    application.add_handler(CallbackQueryHandler(handle_post_edit, pattern="^edit_"))
    application.add_handler(CallbackQueryHandler(handle_post_delete, pattern="^delete_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_content))

    application.run_polling()

if __name__ == "__main__":
    main()
