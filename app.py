import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Blogger API Setup
SCOPES = ['https://www.googleapis.com/auth/blogger']
BLOG_ID = '2426657398890190336'  # Replace with your Blogger blog ID

# Authenticate with Blogger using JSON data from environment variables
def authenticate_blogger():
    credentials_info = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=SCOPES
    )
    service = build('blogger', 'v3', credentials=credentials)
    return service

# Fetch movie details from an API
def get_movie_details(movie_name):
    url = f'https://api.example.com/movies?query={movie_name}'  # Replace with actual API URL
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['results']
    else:
        logger.error("Failed to fetch movie details.")
        return []

# Post to Blogger
def post_to_blogger(service, title, content, image_url):
    body = {
        'kind': 'blogger#post',
        'blog': {'id': BLOG_ID},
        'title': title,
        'content': f"<h1>{title}</h1><img src='{image_url}' alt='{title}'><p>{content}</p>"
    }
    try:
        post = service.posts().insert(blogId=BLOG_ID, body=body).execute()
        logger.info(f"Post created: {post['url']}")
        return post['url']
    except Exception as e:
        logger.error(f"An error occurred while posting to Blogger: {e}")
        return None

# Handler to search for movies
async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a movie name.")
        return

    movies = get_movie_details(query)
    if not movies:
        await update.message.reply_text("No movies found.")
        return

    movie_list = "\n".join([f"{i + 1}. {movie['title']} ({movie['release_date']})" for i, movie in enumerate(movies[:10])])
    context.user_data['movies'] = movies
    await update.message.reply_text(f"Found movies:\n{movie_list}\n\nPlease reply with the movie number.")

# Handler to handle movie selection and post to Blogger
async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        movie_index = int(update.message.text) - 1
        movies = context.user_data.get('movies', [])

        if 0 <= movie_index < len(movies):
            selected_movie = movies[movie_index]
            title = selected_movie['title']
            overview = selected_movie.get('overview', 'No overview available.')
            poster_path = selected_movie.get('poster_path', '')
            image_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''

            service = authenticate_blogger()
            post_url = post_to_blogger(service, title, overview, image_url)
            if post_url:
                await update.message.reply_text(f"Movie posted to Blogger: {post_url}")
            else:
                await update.message.reply_text("Failed to post movie to Blogger.")
        else:
            await update.message.reply_text("Invalid selection.")
    except ValueError:
        await update.message.reply_text("Please reply with a valid movie number.")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send /movie <movie name> to search for a movie.")

# Main function to set up the bot
def main():
    token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("movie", handle_movie_search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_selection))

    # Run bot
    application.run_polling()

if __name__ == '__main__':
    main()
