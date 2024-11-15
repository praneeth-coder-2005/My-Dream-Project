import requests
from telegram import Update
from telegram.ext import ContextTypes
from requests.auth import HTTPBasicAuth

WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

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
        response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 200:
            post_content = response.json().get("content", {}).get("rendered", "")
            new_content = f"{post_content}<br>{video_player_code}"
            update_post_response = requests.post(
                f"{POSTS_API_ENDPOINT}/{post_id}",
                json={"content": new_content},
                auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
            )
            if update_post_response.status_code == 200:
                await update.message.reply_text(f"Video player added to Post {post_id}!")
            else:
                await update.message.reply_text("Failed to update post content.")
        context.user_data.clear()
