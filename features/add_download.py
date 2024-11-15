from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.wordpress import update_post_content

async def handle_add_download_link(update, context):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    context.user_data["add_download_post_id"] = post_id
    await query.edit_message_text("Send the download link title:")
