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
api_id = os.getenv('API_ID')  # The API ID you got from Telegram
api_hash = os.getenv('API_HASH')  # The API Hash you got from Telegram
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Your Bot Token from BotFather

# Google API credentials and TMDb API
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
BLOG_ID = os.getenv('BLOG_ID')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

TMDB_BASE_URL = 'https://api.themoviedb.org/3/search/movie'

# Set up logging to track errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define an asynchronous command handler for the /start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Send me the movie name to start.")

# Handle incoming movie search requests
async def handle_movie_search(update: Update, context: CallbackContext):
    movie_name = update.message.text.strip()

    # Fetch movie details
    movies = get_movie_details(movie_name)

    if movies:
        await update.message.reply_text(f"Found {len(movies)} movies. Choose the correct one:")

        # Display movie options
        for i, movie in enumerate(movies):
            await update.message.reply_text(f"{i+1}. {movie['title']} ({movie.get('release_date', 'Unknown')})")

        await update.message.reply_text("Please select the movie number.")
        context.user_data['movies'] = movies  # Store the list of movies for future use
    else:
        await update.message.reply_text(f"No movies found with the title '{movie_name}'.")

# Handle user selection of a movie
async def select_movie(update: Update, context: CallbackContext):
    try:
        selected_movie_index = int(update.message.text) - 1
        movies = context.user_data.get('movies', [])

        if selected_movie_index >= 0 and selected_movie_index < len(movies):
            selected_movie = movies[selected_movie_index]
            title = selected_movie['title']
            description = selected_movie['overview']
            download_link = "http://example.com/download_link"  # Replace with actual download link

            # Authenticate with Blogger and post the movie details
            blogger_service = authenticate_blogger()
            post_to_blogger(blogger_service, title, description, download_link)
            await update.message.reply_text(f"Movie '{title}' has been posted to the blog!")
        else:
            await update.message.reply_text("Invalid selection. Try again.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")

# Google OAuth: authenticate and post to Blogger
def authenticate_blogger():
    client_secrets = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
    }
    
    # Use `run_console` to handle authentication directly in the Heroku console
    flow = InstalledAppFlow.from_client_config(client_secrets, scopes=['https://www.googleapis.com/auth/blogger'])
    credentials = flow.run_console()  # Prompts for authorization code in Heroku logs

    # Save the credentials to `token.json` for future use
    with open('token.json', 'w') as token_file:
        token_file.write(credentials.to_json())

    blogger_service = build('blogger', 'v3', credentials=credentials)
    return blogger_service

# Fetch movie details using TMDb API
def get_movie_details(movie_name):
    url = f'{TMDB_BASE_URL}?api_key={TMDB_API_KEY}&query={movie_name}'
    response = requests.get(url)
    data = response.json()

    if data['results']:
        return data['results']
    return []

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

# Set up webhook for receiving messages
async def setup_webhook():
    application = Application.builder().token(bot_token).build()

    # Set up the webhook (replace with your actual URL)
    webhook_url = 'https://your-app.herokuapp.com/webhook'  # Set your webhook URL here
    await application.bot.set_webhook(url=webhook_url)

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_movie))

    # Run the bot with polling
    await application.run_polling()

# Main function to start the bot with graceful shutdown
async def main():
    await setup_webhook()

if __name__ == '__main__':
    # Directly run the bot using the Application class's polling system
    import asyncio
    application = Application.builder().token(bot_token).build()
    application.run_polling()  # This will handle the event loop
