from utils.tmdb import search_tmdb_movie
from utils.wordpress import create_post

async def handle_search(update, context):
    movie_name = update.message.text
    movie_details = search_tmdb_movie(movie_name)

    if movie_details:
        title, content, image_url = movie_details
        post_link = create_post(title, content, image_url=image_url)
        if post_link:
            await update.message.reply_text(f"Post created: {post_link}")
        else:
            await update.message.reply_text("Failed to create post.")
    else:
        await update.message.reply_text("No movie details found.")
