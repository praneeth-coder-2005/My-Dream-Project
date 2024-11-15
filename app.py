import os
import requests
from flask import Flask, request, send_from_directory
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from requests.auth import HTTPBasicAuth

# Flask App Initialization
app = Flask(__name__)

# File storage directory
FILE_STORAGE_PATH = "file_store"
os.makedirs(FILE_STORAGE_PATH, exist_ok=True)  # Ensure directory exists

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# Telegram Bot Token
BOT_TOKEN = "8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo"

# Initialize Telegram Bot Application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Route to serve files
@app.route('/files/<path:filename>', methods=['GET'])
def serve_file(filename):
    """Serve files stored in the bot's file storage."""
    return send_from_directory(FILE_STORAGE_PATH, filename)

# WordPress Post Functions
def list_wordpress_posts():
    response = requests.get(
        POSTS_API_ENDPOINT,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        return response.json()
    else:
        return []

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

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /list_posts to see WordPress posts, or upload files to store and generate links.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available Commands:\n"
        "/list_posts - Manage WordPress posts.\n"
        "/upload - Upload a file to generate a shareable link.\n"
        "Interact with posts to add download links, video players, or edit content."
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

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads and provide a link."""
    document = update.message.document
    if document:
        file_id = document.file_id
        file = await context.bot.get_file(file_id)
        file_path = os.path.join(FILE_STORAGE_PATH, document.file_name)
        
        # Download and save the file
        await file.download_to_drive(file_path)
        
        # Generate link
        file_url = f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com/files/{document.file_name}"
        await update.message.reply_text(f"File uploaded successfully! Access it here: {file_url}")
    else:
        await update.message.reply_text("Please upload a valid file.")

# Add Handlers to the Application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("list_posts", list_posts))
application.add_handler(MessageHandler(filters.Document.ALL, handle_file_upload))
application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_\\d+$"))
application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_player_input))

# Flask App for Heroku
@app.route('/')
def index():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook route for Telegram."""
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
