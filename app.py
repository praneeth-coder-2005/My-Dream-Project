import os
import requests
from requests.auth import HTTPBasicAuth
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# WordPress credentials and base URL from environment variables
WORDPRESS_USERNAME = os.getenv('WORDPRESS_USERNAME')
WORDPRESS_PASSWORD = os.getenv('WORDPRESS_PASSWORD')
WORDPRESS_SITE_URL = os.getenv('WORDPRESS_SITE_URL')

# TMDB API configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = "https://api.themoviedb.org/3/search/movie"

# State to store current search results
movie_results = {}


# Function to fetch movie details from TMDB API
def get_movie_details(query):
    url = f"{TMDB_BASE_URL}?api_key={TMDB_API_KEY}&query={query}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [
            {"title": movie["title"], "release_date": movie.get("release_date", "Unknown Date"), "overview": movie.get("overview", "No description available.")}
            for movie in data.get("results", [])
        ]
    else:
        print("Error fetching movies:", response.json())
        return []


# Function to post a new blog post to WordPress
def post_to_wordpress(title, content):
    url = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"
    response = requests.post(
        url,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_PASSWORD),
        json={"title": title, "content": content, "status": "publish"},
    )
    if response.status_code == 201:
        return "Post published successfully!"
    else:
        return f"Error posting to WordPress: {response.json()}"


# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send me a movie name to search for.")


# Message handler for searching movies
async def search_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global movie_results

    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("Please enter a valid movie name.")
        return

    # Fetch movies from TMDB
    movies = get_movie_details(query)
    if not movies:
        await update.message.reply_text("No movies found. Try a different name.")
        return

    # Store results in global state and show them to the user
    movie_results[update.message.chat_id] = movies
    reply_text = f"Found movies for '{query}':\n"
    for i, movie in enumerate(movies, start=1):
        reply_text += f"{i}. {movie['title']} ({movie['release_date']})\n"
    reply_text += "Please reply with the movie number to post to WordPress."
    await update.message.reply_text(reply_text)


# Message handler for selecting a movie
async def select_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global movie_results

    chat_id = update.message.chat_id
    if chat_id not in movie_results or not movie_results[chat_id]:
        await update.message.reply_text("No movies to select. Start by searching for a movie.")
        return

    try:
        movie_index = int(update.message.text.strip()) - 1
        if movie_index < 0 or movie_index >= len(movie_results[chat_id]):
            await update.message.reply_text("Please enter a valid movie number.")
            return
    except ValueError:
        await update.message.reply_text("Please enter a valid movie number.")
        return

    # Get the selected movie
    movie = movie_results[chat_id][movie_index]
    title = movie["title"]
    content = f"**Release Date:** {movie['release_date']}\n\n**Overview:**\n{movie['overview']}"

    # Post to WordPress
    result = post_to_wordpress(title, content)
    await update.message.reply_text(result)

    # Clear the results for this chat
    del movie_results[chat_id]


def main():
    # Telegram bot token
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Initialize the bot application
    application = Application.builder().token(TOKEN).build()

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movies))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_movie))

    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
