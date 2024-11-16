import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

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

# Function to delete a WordPress post
def delete_wordpress_post(post_id):
    response = requests.delete(
        f"{POSTS_API_ENDPOINT}/{post_id}",
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    return response.status_code == 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the bot! Use /list_posts to see and manage your WordPress posts."
    )

async def list_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = requests.get(
        POSTS_API_ENDPOINT,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        posts = response.json()
        keyboard = [
            [InlineKeyboardButton(f"{post['title']['rendered']}", callback_data=f"post_{post['id']}")]
            for post in posts
        ]
        await update.message.reply_text(
            "Select a post to manage:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("Failed to fetch posts.")

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

async def handle_edit_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["edit_post_id"] = post_id
    context.user_data["awaiting_edit_content"] = True
    await query.edit_message_text("Send the updated content for this post:")

async def handle_edit_content_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_edit_content"):
        post_id = context.user_data["edit_post_id"]
        new_content = update.message.text
        context.user_data["awaiting_edit_content"] = False

        success = update_wordpress_post(post_id, new_content)
        if success:
            await update.message.reply_text(f"Post {post_id} updated successfully!")
        else:
            await update.message.reply_text(f"Failed to update Post {post_id}.")
        context.user_data.clear()

async def handle_delete_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    success = delete_wordpress_post(post_id)
    if success:
        await query.edit_message_text(f"Post {post_id} deleted successfully!")
    else:
        await query.edit_message_text(f"Failed to delete Post {post_id}.")

# Add Download Link feature
async def handle_add_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addlink_post_id"] = post_id
    context.user_data["awaiting_link_name"] = True
    await query.edit_message_text("Please send the name for the download link:")

async def handle_download_link_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_link_name"):
        context.user_data["link_name"] = update.message.text
        context.user_data["awaiting_link_name"] = False
        context.user_data["awaiting_download_url"] = True
        await update.message.reply_text("Now send the download URL:")

async def handle_download_link_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_download_url"):
        post_id = context.user_data["addlink_post_id"]
        link_name = context.user_data["link_name"]
        download_url = update.message.text
        context.user_data["awaiting_download_url"] = False

        # Styled download button
        download_button = f"""
        <div style="margin: 10px 0;">
            <a href="{download_url}" style="
                display: inline-block;
                padding: 10px 15px;
                font-size: 16px;
                color: white;
                background-color: #007bff;
                text-decoration: none;
                border-radius: 5px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">{link_name}</a>
        </div>
        """

        # Fetch current content
        post_response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if post_response.status_code == 200:
            post_content = post_response.json().get("content", {}).get("rendered", "")
            new_content = f"{post_content}<br>{download_button}"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Download link '{link_name}' added to Post {post_id}!")
            else:
                await update.message.reply_text("Failed to add the download link.")
        else:
            await update.message.reply_text("Failed to fetch post content.")
        context.user_data.clear()

# Add Video Player feature
async def handle_add_video_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addvideo_post_id"] = post_id
    context.user_data["awaiting_video_url"] = True
    await query.edit_message_text("Send the source URL for the video file:")

async def handle_video_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_video_url"):
        post_id = context.user_data["addvideo_post_id"]
        video_url = update.message.text
        context.user_data["awaiting_video_url"] = False

        video_player_code = f"""
        <script src="//content.jwplatform.com/libraries/IDzF9Zmk.js"></script>
        <div id="my-video1"></div>
        <script>
        jwplayer('my-video1').setup({{
          "playlist": [
            {{
              "sources": [
                {{
                  "file": "{video_url}",
                  "type": "mp4",
                  "default": true,
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

        post_response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if post_response.status_code == 200:
            post_content = post_response.json().get("content", {}).get("rendered", "")
            new_content = f"{post_content}<br>{video_player_code}"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Video player added successfully to Post {post_id}!")
            else:
                await update.message.reply_text(f"Failed to add video player to Post {post_id}.")
        else:
            await update.message.reply_text("Failed to fetch post content.")
        context.user_data.clear()

def main():
    application = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_edit_post, pattern="^edit_\\d+$"))
    application.add_handler(CallbackQueryHandler
