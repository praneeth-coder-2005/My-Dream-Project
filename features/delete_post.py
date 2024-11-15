from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.wordpress import delete_post

async def handle_delete_post(update, context):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    # Implement logic to handle deleting the post
    success = delete_post(post_id)
    if success:
        await query.edit_message_text(f"Post ID {post_id} deleted successfully!")
    else:
        await query.edit_message_text(f"Failed to delete Post ID {post_id}.")
