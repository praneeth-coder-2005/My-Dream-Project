import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0WXnIZ61HwdI6ilVP"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"
MEDIA_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/media"

# TMDB API configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Function to upload a featured image to WordPress
def upload_image_to_wordpress(image_url):
    try:
        image_data = requests.get(image_url).content
        headers = {
            "Content-Disposition": f"attachment; filename=featured_image.jpg",
            "Content-Type": "image/jpeg"
        }
        response = requests.post(
            MEDIA_API_ENDPOINT,
            headers=headers,
            data=image_data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 201:
            return response.json().get("id")  # Return the media ID
        else:
            return None
    except Exception as e:
        return None

# Function to create a WordPress movie post with custom fields
def create_movie_post(title, content, tmdb_data, image_id=None, status="publish"):
    headers = {"Content-Type": "application/json"}
    
    # Movie-specific custom fields (update these to match your actual custom field keys)
    custom_fields = {
        "title": title,
        "content": content,
        "status": status,
        "meta": {
            "release_year": tmdb_data.get("release_date", "")[:4],
            "runtime": tmdb_data.get("runtime"),
            "tmdb_rating": tmdb_data.get("vote_average"),
            "budget": tmdb_data.get("budget"),
            "revenue": tmdb_data.get("revenue"),
            "youtube_trailer": tmdb_data.get("trailer_id"),
            "translator": "Unknown",
            "poster_url": tmdb_data.get("poster_path"),
            "imdbID": tmdb_data.get("imdb_id"),
            "tmdbID": tmdb_data.get("id")
        }
    }
    
    if image_id:
        custom_fields["featured_media"] = image_id

    try:
        response = requests.post(
            POSTS_API_ENDPOINT,
            headers=headers,
            json=custom_fields,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 201:
            return response.json().get("link")
        else:
            return f"Failed to create post: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error during post creation: {str(e)}"

# Function to fetch movie details from TMDB
def get_movie_details(movie_name):
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

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a movie name to search or type /help for guidance.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use this bot:\n"
        "1. Send a movie name to search.\n"
        "2. Select a movie from the list.\n"
        "3. Choose whether to publish immediately or save as a draft."
    )

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_name = update.message.text
    movies = get_movie_details(movie_name)
    if movies:
        keyboard = [
            [InlineKeyboardButton(f"{movie['title']} ({movie['release_date']})", callback_data=str(i))]
            for i, movie in enumerate(movies[:10])
        ]
        context.user_data["movies"] = movies
        await update.message.reply_text(
            f"Found movies for '{movie_name}': Select a movie to post to WordPress.",
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
        image_id = upload_image_to_wordpress(selected_movie["poster_path"]) if selected_movie["poster_path"] else None

        keyboard = [
            [InlineKeyboardButton("Publish Now", callback_data=f"publish_{selected_index}")],
            [InlineKeyboardButton("Save as Draft", callback_data=f"draft_{selected_index}")]
        ]
        context.user_data.update({"title": title, "content": content, "image_id": image_id, "tmdb_data": selected_movie})
        await query.edit_message_text(
            "How would you like to post this?\n"
            f"Title: {title}\n"
            f"Release Date: {selected_movie['release_date']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text("Invalid selection.")

async def handle_post_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, selected_index = data[0], int(data[1])
    movies = context.user_data.get("movies", [])
    if 0 <= selected_index < len(movies):
        title = context.user_data.get("title")
        content = context.user_data.get("content")
        image_id = context.user_data.get("image_id")
        tmdb_data = context.user_data.get("tmdb_data")
        status = "publish" if action == "publish" else "draft"

        post_url = create_movie_post(title, content, tmdb_data, image_id=image_id, status=status)
        if post_url.startswith("http"):
            await query.edit_message_text(f"Post successfully created: {post_url}")
        else:
            await query.edit_message_text(f"Error posting to WordPress: {post_url}")
    else:
        await query.edit_message_text("Invalid selection.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection, pattern="^[0-9]+$))
    application.add_handler(CallbackQueryHandler(handle_post_publish, pattern="^(publish|draft)_\d+$"))

    application.run_polling()

if __name__ == "__main__":
    main()
