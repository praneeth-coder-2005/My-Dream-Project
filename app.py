import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from dotenv import load_dotenv
import asyncio  # For event loop management

# Load environment variables
load_dotenv()

# Fetch Telegram and Blogger API credentials from environment variables
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
BLOG_ID = os.getenv('BLOG_ID')

# Set up logging to track errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to start the bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Send me the movie name to start.")

# Handle incoming movie search requests
async def handle_movie_search(update: Update, context: CallbackContext):
    movie_name = update.message.text.strip()
    movies = get_movie_details(movie_name)

    if movies:
        await update.message.reply_text(f"Found {len(movies)} movies. Choose the correct one:")
        for i, movie in enumerate(movies):
            await update.message.reply_text(f"{i+1}. {movie['title']} ({movie.get('release_date', 'Unknown')})")
        await update.message.reply_text("Please select the movie number.")
        context.user_data['movies'] = movies
    else:
        await update.message.reply_text(f"No movies found with the title '{movie_name}'.")

# Handle user selection of a movie
async def select_movie(update: Update, context: CallbackContext):
    try:
        selected_movie_index = int(update.message.text) - 1
        movies = context.user_data.get('movies', [])
        if 0 <= selected_movie_index < len(movies):
            selected_movie = movies[selected_movie_index]
            title = selected_movie['title']
            description = selected_movie['overview']
            download_link = "http://example.com/download_link"  # Placeholder link

            # Authenticate with Blogger API using service account credentials
            blogger_service = authenticate_blogger()
            post_to_blogger(blogger_service, title, description, download_link)
            await update.message.reply_text(f"Movie '{title}' has been posted to the blog!")
        else:
            await update.message.reply_text("Invalid selection. Try again.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")

# Authenticate and create a Blogger API service instance
def authenticate_blogger():
    service_account_info = json.loads(os.getenv('SERVICE_ACCOUNT_JSON'))
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=['https://www.googleapis.com/auth/blogger']
    )
    return build('blogger', 'v3', credentials=credentials)

# Fetch movie details using TMDb API
def get_movie_details(movie_name):
    url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}'
    response = requests.get(url)
    data = response.json()
    return data.get('results', [])

# Create a blog post on Blogger
def post_to_blogger(blogger_service, title, description, download_link):
    try:
        post_data = {
            'title': title,
            'content': f'<h2>{title}</h2><p>{description}</p><a href="{download_link}">Download Here</a>'
        }
        blogger_service.posts().insert(blogId=BLOG_ID, body=post_data).execute()
        print("Post successfully created!")
    except HttpError as err:
        print(f"An error occurred: {err}")

# Setup webhook and add handlers
async def setup_webhook(application):
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_movie))

    await application.run_polling()

# Main function to start the bot
async def main():
    application = Application.builder().token(bot_token).build()
    await setup_webhook(application)

# This is the block to prevent the event loop error on Heroku
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
