from utils.wordpress import update_post_content
from utils.video_player import generate_video_player_html

async def handle_add_video_player(update, context):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    context.user_data["add_video_post_id"] = post_id
    await query.edit_message_text("Send the source URL for the video player:")

async def handle_video_player_input(update, context):
    if "add_video_post_id" in context.user_data:
        post_id = context.user_data["add_video_post_id"]
        video_url = update.message.text

        # Generate video player HTML
        video_player_html = generate_video_player_html(video_url)

        # Append video player to the post content
        success = update_post_content(post_id, video_player_html)
        if success:
            await update.message.reply_text(f"Video player added to Post ID {post_id}!")
        else:
            await update.message.reply_text(f"Failed to add video player to Post ID {post_id}.")
        context.user_data.pop("add_video_post_id", None)
