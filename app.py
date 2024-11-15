import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# TMDB API configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# Function to fetch movie details from TMDB
def get_movie_details_tmdb(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    try:
        response = requests.get(TMDB_API_URL, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [
                {
                    "title": movie.get("title"),
                    "release_date": movie.get("release_date", "Unknown Date"),
                    "overview": movie.get("overview", "No overview available."),
                    "popularity": movie.get("popularity"),
                    "vote_average": movie.get("vote_average"),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
                }
                for movie in results
            ]
        else:
            return []
    except Exception as e:
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
    await update.message.reply_text("Welcome! Use /list_posts, /search <movie>, or /help for guidance.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/list_posts - List WordPress posts.\n"
        "/search <movie> - Search for a movie and post to WordPress.\n"
        "Manage posts to add video players or download links."
    )

# Feature: Movie Search and Post to WordPress
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Provide a movie name. Example: /search Inception")
        return

    movie_name = " ".join(context.args)
    movies = get_movie_details_tmdb(movie_name)
    if movies:
        keyboard = [
            [InlineKeyboardButton(f"{movie['title']} ({movie['release_date']})", callback_data=str(i))]
            for i, movie in enumerate(movies[:10])
        ]
        context.user_data["movies"] = movies
        await update.message.reply_text(
            f"Movies found for '{movie_name}': Select one to post to WordPress.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("No movies found.")

async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_index = int(query.data)
    movies = context.user_data.get("movies", [])
    if 0 <= selected_index < len(movies):
        selected_movie = movies[selected_index]
        title = selected_movie["title"]
        content = (
            f"<h2>{title}</h2>"
            f"<p>Release Date: {selected_movie['release_date']}</p>"
            f"<p>Overview: {selected_movie['overview']}</p>"
            f"<p>Popularity: {selected_movie['popularity']}</p>"
            f"<p>Vote Average: {selected_movie['vote_average']}</p>"
        )
        # Post to WordPress
        data = {"title": title, "content": content, "status": "publish"}
        response = requests.post(
            POSTS_API_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 201:
            post_link = response.json().get("link")
            await query.edit_message_text(f"Post created: {post_link}")
        else:
            await query.edit_message_text("Failed to post to WordPress.")
    else:
        await query.edit_message_text("Invalid selection.")

# Feature: Add Video Player
async def handle_add_video_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addvideo_post_id"] = post_id
    context.user_data["awaiting_video_url"] = True
    await query.edit_message_text("Send the video source URL:")

async def handle_video_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_video_url"):
        post_id = context.user_data.get("addvideo_post_id")
        video_url = update.message.text
        context.user_data["awaiting_video_url"] = False

        video_code = f"""
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
        # Append to WordPress
        response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 200:
            post_content = response.json().get("content", {}).get("rendered", "")
            new_content = f"{post_content}<br>{video_code}"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Video player added to Post {post_id}!")
            else:
                await update.message.reply_text("Failed to update post.")
        context.user_data.clear()

# Feature: Add Download Link
async def handle_add_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addlink_post_id"] = post_id
    await query.edit_message_text("Send the download link:")

async def handle_download_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_id = context.user_data.get("addlink_post_id")
    download_link = update.message.text

    # Append download link to post
    response = requests.get(
        f"{POSTS_API_ENDPOINT}/{post_id}",
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        post_content = response.json().get("content", {}).get("rendered", "")
        new_content = f"{post_content}<br><a href='{download_link}'>Download</a>"
        success = update_wordpress_post(post_id, new_content)
        if success:
            await update.message.reply_text(f"Download link added to Post {post_id}!")
        else:
            await update.message.reply_text("Failed to update post.")
    context.user_data.clear()

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_movie))
    application.add_handler(CallbackQueryHandler(handle_movie_selection, pattern="^\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_player_input))
    application.add_handler(CallbackQueryHandler(handle_add_download_link, pattern="^addlink_\\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download_link_input))

    application.run_polling()

if __name__ == "__main__":
    main()
