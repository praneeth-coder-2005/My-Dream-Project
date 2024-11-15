import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for user states
USER_STATE = {}
MOVIES_CACHE = {}

# TMDB API Key (Environment Variable)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    USER_STATE[update.effective_user.id] = "start"
    await update.message.reply_text("Welcome! Send a movie name to search.")

# Movie search handler
async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_state = USER_STATE.get(user_id, "start")

    if user_state == "choose_movie":
        await handle_movie_selection(update, context)
        return

    movie_name = update.message.text
    movies = get_movie_details(movie_name)
    if not movies:
        await update.message.reply_text("No movies found. Try another search.")
        return

    MOVIES_CACHE[user_id] = movies
    USER_STATE[user_id] = "choose_movie"

    response = "Found movies:\n"
    for idx, movie in enumerate(movies, start=1):
        response += f"{idx}. {movie['title']} ({movie.get('release_date', 'Unknown')})\n"
    response += "Please reply with the movie number."
    await update.message.reply_text(response)

# Movie selection handler
async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in MOVIES_CACHE or USER_STATE.get(user_id) != "choose_movie":
        await update.message.reply_text("Please search for a movie first.")
        return

    try:
        choice = int(update.message.text)
        movies = MOVIES_CACHE[user_id]
        if choice < 1 or choice > len(movies):
            raise ValueError("Invalid choice")

        selected_movie = movies[choice - 1]
        details = (
            f"Title: {selected_movie['title']}\n"
            f"Release Date: {selected_movie.get('release_date', 'Unknown')}\n"
            f"Overview: {selected_movie.get('overview', 'No overview available.')}"
        )
        await update.message.reply_text(details)

        # Reset state
        USER_STATE[user_id] = "start"
    except ValueError:
        await update.message.reply_text("Invalid input. Please reply with the movie number.")

# Fetch movie details from TMDB
def get_movie_details(movie_name):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    data = response.json()
    return data.get("results", [])

# Main function
def main():
    # Create application
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
