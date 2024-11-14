import os
import requests
import time  # Import time module for delay
from pyrogram import Client, filters
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Fetch API credentials from environment variables
api_id = os.getenv('API_ID')  # The API ID you got from Telegram
api_hash = os.getenv('API_HASH')  # The API Hash you got from Telegram
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Your Bot Token from BotFather

# Get configuration from environment variables
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
BLOG_ID = os.getenv('BLOG_ID')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8080/oauth2callback')

# TMDb API Configuration
TMDB_BASE_URL = 'https://api.themoviedb.org/3/search/movie'

# Google OAuth: authenticate and post to Blogger
def authenticate_blogger():
    client_secrets = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [REDIRECT_URI]
        }
    }

    flow = InstalledAppFlow.from_client_config(client_secrets, scopes=['https://www.googleapis.com/auth/blogger'])
    credentials = flow.run_local_server(port=8080, redirect_uri=REDIRECT_URI)
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

# Pyrogram client to handle incoming messages and commands
app = Client("movie_bot", bot_token=bot_token, api_id=api_id, api_hash=api_hash)

# Start command to welcome the user
@app.on_message(filters.command("start"))
def start(update, context):
    update.reply_text("Welcome! Send me the movie name to start.")

# Movie search handler (for non-command text messages)
@app.on_message(filters.text)
def handle_movie_search(update, context):
    message = update.text.strip()

    # Check if the message starts with a '/' (i.e., it's a command)
    if message.startswith('/'):
        return  # Skip commands and do nothing
    
    # Otherwise, treat it as a movie search request
    movie_name = update.text
    movies = get_movie_details(movie_name)

    if movies:
        update.reply_text(f"Found {len(movies)} movies. Choose the correct one:")

        # Display movie options
        for i, movie in enumerate(movies):
            update.reply_text(f"{i+1}. {movie['title']} ({movie.get('release_date', 'Unknown')})")

        update.reply_text("Please select the movie number.")
        context.user_data['movies'] = movies  # Store the list of movies for future use
    else:
        update.reply_text(f"No movies found with the title '{movie_name}'.")

# Handle user input (movie selection)
@app.on_message(filters.text)
def select_movie(update, context):
    message = update.text.strip()

    # Check if the message starts with a '/' (i.e., it's a command)
    if message.startswith('/'):
        return  # Skip commands and do nothing

    try:
        selected_movie_index = int(update.text) - 1
        movies = context.user_data.get('movies', [])

        if selected_movie_index >= 0 and selected_movie_index < len(movies):
            selected_movie = movies[selected_movie_index]
            title = selected_movie['title']
            description = selected_movie['overview']
            download_link = "http://example.com/download_link"  # Replace with actual download link

            # Authenticate with Blogger and post the movie details
            blogger_service = authenticate_blogger()
            post_to_blogger(blogger_service, title, description, download_link)
            update.reply_text(f"Movie '{title}' has been posted to the blog!")
        else:
            update.reply_text("Invalid selection. Try again.")
    except ValueError:
        update.reply_text("Please enter a valid number.")

# Ensure the time is synchronized before starting the bot
time.sleep(10)  # Adding a longer delay to ensure the system time syncs

# Run the bot
app.run()
