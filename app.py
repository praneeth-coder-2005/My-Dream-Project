import os
from flask import Flask, request, jsonify, send_from_directory
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# Flask App
app = Flask(__name__)
UPLOAD_FOLDER = 'files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# File Store Routes
@app.route('/')
def home():
    return "File Store and Telegram Bot are running!"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    file_url = f"{request.url_root}files/{file.filename}"
    return jsonify({"file_url": file_url}), 200

@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Telegram Bot Functions
def list_wordpress_posts():
    response = requests.get(
        POSTS_API_ENDPOINT,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        return response.json()
    else:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /list_posts to manage WordPress posts or upload files via Flask.")

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

async def handle_add_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addlink_post_id"] = post_id
    context.user_data["awaiting_download_link_title"] = True
    await query.edit_message_text("Send the title for the download link:")

async def handle_download_link_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_download_link_title"):
        context.user_data["download_link_title"] = update.message.text
        context.user_data["awaiting_download_link_title"] = False
        context.user_data["awaiting_download_link_url"] = True
        await update.message.reply_text("Send the URL for the download link:")
    elif context.user_data.get("awaiting_download_link_url"):
        post_id = context.user_data.get("addlink_post_id")
        download_link_title = context.user_data.get("download_link_title")
        download_link_url = update.message.text
        context.user_data["awaiting_download_link_url"] = False

        # HTML Button Code
        download_button = f'<a href="{download_link_url}" class="btn btn-primary" target="_blank">{download_link_title}</a>'

        # Fetch the current content of the post
        post_response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if post_response.status_code == 200:
            post_content = post_response.json().get("content", {}).get("rendered", "")
            # Append the download button
            new_content = f"{post_content}<br>{download_button}"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Download link added successfully to Post {post_id}!")
            else:
                await update.message.reply_text(f"Failed to add download link to Post {post_id}.")
        else:
            await update.message.reply_text("Failed to fetch post content.")
        # Clear user data
        context.user_data.clear()
    else:
        await update.message.reply_text("Unexpected input. Please use /list_posts to start again.")

async def handle_add_video_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addvideo_post_id"] = post_id
    context.user_data["awaiting_video_url"] = True
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
        # Clear user data
        context.user_data.clear()
    else:
        await update.message.reply_text("Unexpected input. Please use /list_posts to start again.")

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

# Main Function
def start_telegram_bot():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_player_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download_link_title))

    application.run_polling()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    start_telegram_bot()
