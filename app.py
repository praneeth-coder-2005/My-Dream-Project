import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# WordPress credentials
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME")  # Replace with your username if not using env
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")  # Replace with your application password if not using env

# WordPress REST API endpoint for creating posts
API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# Function to create a WordPress post
def create_wordpress_post(title, content, status="publish"):
    """
    Creates a post on WordPress using the REST API.
    """
    auth = (WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    headers = {"Content-Type": "application/json"}
    data = {"title": title, "content": content, "status": status}

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data, auth=auth)
        if response.status_code == 201:
            return response.json().get("link")
        else:
            return f"Error: {response.status_code}, {response.json().get('message')}"
    except requests.exceptions.RequestException as e:
        return f"Request error: {str(e)}"

# TMDB API Integration
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

def get_movie_details(movie_name):
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
        buttons = [
            f"{i + 1}. {movie['title']} ({movie['release_date']})"
            for i, movie in enumerate(movies[:10])
        ]
        context.user_data["movies"] = movies
        await update.message.reply_text(
            f"Found movies for '{movie_name}':\n" + "\n".join(buttons) + "\nPlease reply with the movie number."
        )
    else:
        await update.message.reply_text("No movies found.")

async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        selected_index = int(update.message.text) - 1
        movies = context.user_data.get("movies", [])
        if 0 <= selected_index < len(movies):
            selected_movie = movies[selected_index]
            title = selected_movie["title"]
            content = f"<h2>{title}</h2><p>Release Date: {selected_movie['release_date']}</p>"
            post_url = create_wordpress_post(title, content)
            if "http" in post_url:
                await update.message.reply_text(f"Post successfully created: {post_url}")
            else:
                await update.message.reply_text(f"Error posting to WordPress: {post_url}")
        else:
            await update.message.reply_text("Please enter a valid movie number.")
    except ValueError:
        await update.message.reply_text("Please enter a number.")

# Main Function
def main():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(MessageHandler(filters.Regex(r"^\d+$"), handle_movie_selection))

    application.run_polling()

if __name__ == "__main__":
    main()
