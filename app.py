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

# Function to list posts from WordPress
def list_wordpress_posts():
    response = requests.get(
        POSTS_API_ENDPOINT,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        return response.json()
    else:
        return []

# Function to update a WordPress post
def update_wordpress_post(post_id, content):
    headers = {"Content-Type": "application/json"}
    data = {"content": content}
    response = requests.post(
        f"{POSTS_API_ENDPOINT}/{post_id}",
        headers=headers,
        json=data,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    return response.status_code == 200

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /list_posts to see available posts or type /help for guidance.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available Commands:\n"
        "/list_posts - List all posts on your WordPress site.\n"
        "Interact with posts to edit, delete, or add links and video players."
    )

async def list_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = list_wordpress_posts()
    if posts:
        keyboard = [
            [InlineKeyboardButton(f"{post['title']['rendered']}", callback_data=f"post_{post['id']}")]
            for post in posts
        ]
        await update.message.reply_text(
            "Select a post to manage:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("No posts found.")

async def handle_post_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    keyboard = [
        [InlineKeyboardButton("Edit Post", callback_data=f"edit_{post_id}")],
        [InlineKeyboardButton("Delete Post", callback_data=f"delete_{post_id}")],
        [InlineKeyboardButton("Add Download Link", callback_data=f"addlink_{post_id}")],
        [InlineKeyboardButton("Add Video Player", callback_data=f"addvideo_{post_id}")]
    ]
    await query.edit_message_text(
        f"What would you like to do with Post ID {post_id}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_add_video_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addvideo_post_id"] = post_id
    context.user_data["awaiting_video_url"] = True  # Set state for awaiting video URL
    await query.edit_message_text("Send the source URL for the video file:")

async def handle_video_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_video_url"):
        post_id = context.user_data.get("addvideo_post_id")
        video_url = update.message.text
        context.user_data["awaiting_video_url"] = False

        # JWPlayer code with the provided source URL
        video_player_code = f"""
        <script src="//content.jwplatform.com/libraries/IDzF9Zmk.js"></script>
        <div id="my-video1"></div>
        <script>
        // <![CDATA[
        jwplayer('my-video1').setup({{
          "playlist": [
            {{
              "sources": [
                {{
                  "default": true,
                  "type": "mp4",
                  "file": "{video_url}",
                  "label": "HD"
                }}
              ]
            }}
          ],
          "primary": "html5",
          "hlshtml": true,
          "autostart": false
        }});
        // ]]>
        </script>
        """

        # Fetch the current content of the post
        post_response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if post_response.status_code == 200:
            post_content = post_response.json().get("content", {}).get("rendered", "")
            # Append the video player code
            new_content = f"{post_content}<br>{video_player_code}"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Video player added successfully to Post {post_id}!")
            else:
                await update.message.reply_text(f"Failed to add video player to Post {post_id}.")
        else:
            await update.message.reply_text("Failed to fetch post content.")
        # Clear user data after completing the process
        context.user_data.clear()
    else:
        await update.message.reply_text("Unexpected input. Please use /list_posts to start again.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_player_input))

    application.run_polling()

if __name__ == "__main__":
    main()
