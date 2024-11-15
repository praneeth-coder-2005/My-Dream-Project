import os
import requests
from requests.auth import HTTPBasicAuth
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Environment Variables
WORDPRESS_USERNAME = os.getenv('WORDPRESS_USERNAME')
WORDPRESS_PASSWORD = os.getenv('WORDPRESS_PASSWORD')
WORDPRESS_SITE_URL = os.getenv('WORDPRESS_SITE_URL')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# State storage for user sessions
user_sessions = {}

# Function to fetch movie details from TMDB API
def get_movie_details(query):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [
            {"title": movie["title"], "release_date": movie.get("release_date", "Unknown Date"), "overview": movie.get("overview", "No description available.")}
            for movie in data.get("results", [])
        ]
    else:
        return []

# Function to post content to WordPress
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
    chat_id = update.message.chat_id
    user_sessions[chat_id] = {"state": "idle"}
    await update.message.reply_text("Welcome! Send me a movie name to search for.")

# Message handler for searching movies
async def search_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    query = update.message.text.strip()

    if not query:
        await update.message.reply_text("Please enter a valid movie name.")
        return

    # Fetch movies from TMDB
    movies = get_movie_details(query)
    if not movies:
        await update.message.reply_text("No movies found. Try a different name.")
        return

    # Save movies to session state
    user_sessions[chat_id] = {"state": "awaiting_selection", "movies": movies}
    keyboard = [
        [InlineKeyboardButton(f"{movie['title']} ({movie['release_date']})", callback_data=str(i))]
        for i, movie in enumerate(movies)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a movie to post to WordPress:", reply_markup=reply_markup)

# Callback handler for selecting a movie
async def select_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    # Check session state
    session = user_sessions.get(chat_id, {})
    if session.get("state") != "awaiting_selection":
        await query.edit_message_text("No movie search is active. Please search for a movie first.")
        return

    # Validate movie selection
    try:
        movie_index = int(query.data)
        movies = session.get("movies", [])
        selected_movie = movies[movie_index]
    except (ValueError, IndexError):
        await query.edit_message_text("Invalid selection. Please start a new search.")
        return

    # Get selected movie details
    title = selected_movie["title"]
    content = f"**Release Date:** {selected_movie['release_date']}\n\n**Overview:**\n{selected_movie['overview']}"

    # Post to WordPress
    result = post_to_wordpress(title, content)
    await query.edit_message_text(result)

    # Reset user session
    user_sessions[chat_id] = {"state": "idle"}

# Main function to start the bot
def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movies))
    application.add_handler(CallbackQueryHandler(select_movie))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
