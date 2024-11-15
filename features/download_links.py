import requests
from telegram import Update
from telegram.ext import ContextTypes
from requests.auth import HTTPBasicAuth

WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

async def handle_add_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addlink_post_id"] = post_id
    context.user_data["awaiting_download_link"] = True
    await query.edit_message_text("Send the download link title:")

async def handle_download_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_download_link"):
        post_id = context.user_data.get("addlink_post_id")
        link_title = update.message.text
        context.user_data["awaiting_download_url"] = True
        context.user_data["download_link_title"] = link_title
        await update.message.reply_text("Send the URL for the download link:")
    elif context.user_data.get("awaiting_download_url"):
        post_id = context.user_data.get("addlink_post_id")
        link_url = update.message.text
        link_title = context.user_data.get("download_link_title")
        response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 200:
            post_content = response.json().get("content", {}).get("rendered", "")
            new_content = f"{post_content}<br><a href='{link_url}'>{link_title}</a>"
            update_post_response = requests.post(
                f"{POSTS_API_ENDPOINT}/{post_id}",
                json={"content": new_content},
                auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
            )
            if update_post_response.status_code == 200:
                await update.message.reply_text(f"Download link added to Post {post_id}!")
            else:
                await update.message.reply_text("Failed to update post content.")
        context.user_data.clear()
