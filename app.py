import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch API credentials from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Your Bot Token from BotFather
TMDB_API_KEY = os.getenv('TMDB_API_KEY')  # TMDB API Key
BLOG_ID = os.getenv('BLOG_ID')  # Blogger Blog ID
CLIENT_ID = os.getenv('CLIENT_ID')  # Google Client ID
CLIENT_SECRET = os.getenv('CLIENT_SECRET')  # Google Client Secret
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8080/oauth2callback')

# TMDB API Base URL
TMDB_BASE_URL = 'https://api.themoviedb.org/3/search/movie'

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Blogger Service Cache
blogger_service = None

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome! Send me the name of a movie to get started.")

# Handle movie search and selection
async def handle_movie_request(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.strip()

    # Check if the user provided a number and has a movie list stored
    if user_input.isdigit() and "movies" in context.user_data:
        # Treat this as a selection from the list
        await select_movie(update, context, int(user_input))
    else:
        # Treat this as a movie search request
        await search_movies(update, context, user_input)

# Search for movies and display options
async def search_movies(update: Update, context: CallbackContext, movie_name: str) -> None:
    movies = get_movie_details(movie_name)

    if movies:
        reply_text = "I found the following movies. Reply with the movie number to select:\n"
        for i, movie in enumerate(movies):
            release_date = movie.get("release_date", "Unknown")
            reply_text += f"{i+1}. {movie['title']} ({release_date})\n"
        await update.message.reply_text(reply_text)
        context.user_data["movies"] = movies  # Save movies for selection
    else:
        await update.message.reply_text(f"No movies found with the title '{movie_name}'.")

# Handle movie selection
async def select_movie(update: Update, context: CallbackContext, selected_index: int) -> None:
    movies = context.user_data.get("movies", [])

    # Validate selection
    if 0 <= selected_index - 1 < len(movies):
        selected_movie = movies[selected_index - 1]
        title = selected_movie["title"]
        description = selected_movie.get("overview", "No description available.")
        download_link = "http://example.com/download_link"  # Placeholder

        # Post to Blogger
        global blogger_service
        if blogger_service is None:
            blogger_service = authenticate_blogger()
        post_to_blogger(blogger_service, title, description, download_link)

        await update.message.reply_text(f"Movie '{title}' has been posted to your blog!")
        context.user_data.pop("movies", None)  # Clear movie list after selection
    else:
        await update.message.reply_text("Invalid movie number. Please try again.")

# Authenticate Google Blogger
def authenticate_blogger():
    client_secrets = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_secrets, scopes=["https://www.googleapis.com/auth/blogger"])
    credentials = flow.run_local_server(port=8080, redirect_uri=REDIRECT_URI)
    service = build("blogger", "v3", credentials=credentials)
    return service

# Fetch movie details from TMDb API
def get_movie_details(movie_name):
    try:
        response = requests.get(TMDB_BASE_URL, params={"api_key": TMDB_API_KEY, "query": movie_name})
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.RequestException as e:
        logger.error(f"Error fetching movie details: {e}")
        return []

# Post to Blogger
def post_to_blogger(service, title, description, download_link):
    try:
        post_body = {
            "title": title,
            "content": f"<h2>{title}</h2><p>{description}</p><a href='{download_link}'>Download Here</a>",
        }
        service.posts().insert(blogId=BLOG_ID, body=post_body).execute()
        logger.info("Blog post created successfully.")
    except HttpError as e:
        logger.error(f"Error creating blog post: {e}")

# Main function to run the bot
def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_request))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
