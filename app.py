import os
import requests
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram and Blogger configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
BLOG_ID = os.getenv('BLOG_ID')

# Logging configuration
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to start the bot
async def start(update: Update, context):
    await update.message.reply_text("Welcome! Send me a movie name to search for.")

# Handle movie search
async def handle_movie_search(update: Update, context):
    movie_name = update.message.text.strip()
    movies = get_movie_details(movie_name)
    if not movies:
        await update.message.reply_text(f"No movies found with the name '{movie_name}'.")
        return

    context.user_data["movies"] = movies
    reply = "\n".join(
        [f"{idx + 1}. {movie['title']} ({movie.get('release_date', 'Unknown')})" for idx, movie in enumerate(movies)]
    )
    await update.message.reply_text(f"Found movies:\n{reply}\nPlease reply with the movie number.")

# Handle movie selection
async def select_movie(update: Update, context):
    try:
        movies = context.user_data.get("movies", [])
        selected_index = int(update.message.text.strip()) - 1
        if selected_index < 0 or selected_index >= len(movies):
            await update.message.reply_text("Invalid selection. Please try again.")
            return

        selected_movie = movies[selected_index]
        title = selected_movie["title"]
        description = selected_movie["overview"]

        # Authenticate with Blogger and post
        blogger_service = authenticate_blogger()
        post_to_blogger(blogger_service, title, description)

        await update.message.reply_text(f"'{title}' has been posted to Blogger!")
    except ValueError:
        await update.message.reply_text("Invalid input. Please provide a valid movie number.")

# Authenticate Blogger API
def authenticate_blogger():
    service_account_info = json.loads(os.getenv("SERVICE_ACCOUNT_JSON"))
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=["https://www.googleapis.com/auth/blogger"]
    )
    return build("blogger", "v3", credentials=credentials)

# Fetch movie details from TMDB
def get_movie_details(movie_name):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    response = requests.get(url)
    return response.json().get("results", [])

# Post to Blogger
def post_to_blogger(blogger_service, title, description):
    try:
        post_body = {
            "title": title,
            "content": f"<p>{description}</p>",
        }
        blogger_service.posts().insert(blogId=BLOG_ID, body=post_body).execute()
        logger.info("Blog post created successfully.")
    except HttpError as error:
        logger.error(f"An error occurred: {error}")

# Main application setup
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))

    application.run_polling()

if __name__ == "__main__":
    main()
