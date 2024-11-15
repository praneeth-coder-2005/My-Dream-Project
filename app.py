import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"  # Replace with your WordPress site URL
WORDPRESS_USERNAME = "admin"  # Replace with your WordPress username
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"  # Replace with the 24-character application password

# WordPress REST API endpoint for creating posts
API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# Function to create a WordPress post
def create_wordpress_post(title, content, status="publish"):
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "content": content,
        "status": status  # "publish" or "draft"
    }

    # Make a POST request to WordPress
    response = requests.post(
        API_ENDPOINT,
        headers=headers,
        json=data,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )

    if response.status_code == 201:  # HTTP 201 Created
        return response.json().get("link")
    else:
        return f"Failed to create post: {response.status_code} - {response.text}"

# Function to search for movies using an API (replace this with TMDB or your preferred movie API)
def get_movie_details(movie_name):
    TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"  # Replace with your TMDB API Key
    TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    response = requests.get(TMDB_API_URL, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        return [
            {"title": movie.get("title"), "release_date": movie.get("release_date", "Unknown Date")}
            for movie in results
        ]
    else:
        return []

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a movie name to search.")

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
        content = f"<h2>{title}</h2><p>Release Date: {selected_movie['release_date']}</p>"
        post_url = create_wordpress_post(title, content)
        if "http" in post_url:
            await query.edit_message_text(f"Post successfully created: {post_url}")
        else:
            await query.edit_message_text(f"Error posting to WordPress: {post_url}")
    else:
        await query.edit_message_text("Invalid selection.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()  # Replace with your bot token
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection))

    application.run_polling()

if __name__ == "__main__":
    main()
