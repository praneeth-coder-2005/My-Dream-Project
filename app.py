import os
import time
from pyrogram import Client
from pyrogram.errors import BadMsgNotification, FloodWait  # Corrected import here

# Fetch API credentials from environment variables
api_id = os.getenv('API_ID')  # The API ID you got from Telegram
api_hash = os.getenv('API_HASH')  # The API Hash you got from Telegram
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Your Bot Token from BotFather

# Create the Pyrogram client with session persistence
app = Client("movie_bot", bot_token=bot_token, api_id=api_id, api_hash=api_hash, session_name="my_session")

# Start the bot with retry logic for time sync and flood wait errors
def start_bot_with_retries():
    retry_count = 5  # Number of retry attempts
    backoff_time = 10  # Initial wait time before retrying in seconds
    
    for attempt in range(retry_count):
        try:
            print(f"Attempt {attempt + 1} to start the bot...")
            app.start()  # Start the bot session
            break  # Successfully started the bot, break the loop
        except BadMsgNotification as e:
            print(f"BadMsgNotification Error: {e}. Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)  # Wait for time to sync
            backoff_time *= 2  # Exponential backoff: double the wait time
        except FloodWait as e:  # Use the correct exception name here
            print(f"FloodWaitError: Telegram says wait for {e.x} seconds. Retrying in {e.x} seconds...")
            time.sleep(e.x)  # Wait for the required amount of time specified by Telegram
        except Exception as e:
            print(f"Unexpected error: {e}. Giving up.")
            break

# Define command handlers
@app.on_message(filters.command("start"))
def start(update, context):
    update.message.reply_text("Welcome! Send me the movie name to start.")

# Movie search handler (for non-command text messages)
@app.on_message(filters.text)
def handle_movie_search(update, context):
    movie_name = update.message.text.strip()

    # Fetch movie details from TMDb API or database
    movies = get_movie_details(movie_name)

    if movies:
        update.message.reply_text(f"Found {len(movies)} movies. Choose the correct one:")

        # Display movie options
        for i, movie in enumerate(movies):
            update.message.reply_text(f"{i+1}. {movie['title']} ({movie.get('release_date', 'Unknown')})")

        update.message.reply_text("Please select the movie number.")
        context.user_data['movies'] = movies  # Store the list of movies for future use
    else:
        update.message.reply_text(f"No movies found with the title '{movie_name}'.")

# Handle user input (movie selection)
@app.on_message(filters.text)
def select_movie(update, context):
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
            update.message.reply_text(f"Movie '{title}' has been posted to the blog!")
        else:
            update.message.reply_text("Invalid selection. Try again.")
    except ValueError:
        update.message.reply_text("Please enter a valid number.")

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

# Run the bot with retry logic
start_bot_with_retries()
