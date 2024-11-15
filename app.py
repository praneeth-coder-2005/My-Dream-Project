import os
import logging
import requests
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Blogger setup
def authenticate_blogger():
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not credentials_json:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON is not set.")
    credentials = Credentials.from_service_account_info(eval(credentials_json))
    return build("blogger", "v3", credentials=credentials)

def create_blogger_post(title, content):
    service = authenticate_blogger()
    blog_id = "YOUR_BLOGGER_BLOG_ID"  # Replace with your Blogger blog ID
    post_body = {
        "title": title,
        "content": content,
        "labels": ["Movies", "Telegram Bot"]
    }
    service.posts().insert(blogId=blog_id, body=post_body, isDraft=False).execute()
    logger.info(f"Posted to Blogger: {title}")

# Movie API integration
def get_movie_details(movie_name):
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("TMDB_API_KEY is not set.")
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching movie details: {e}")
        return []

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send a movie name to get its details.")

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_name = update.message.text
    movies = get_movie_details(movie_name)
    if not movies:
        await update.message.reply_text("No movies found. Try another name.")
        return
    
    response_text = "Found movies:\n"
    for i, movie in enumerate(movies[:10], start=1):
        title = movie.get("title", "N/A")
        release_date = movie.get("release_date", "Unknown")
        response_text += f"{i}. {title} ({release_date})\n"
    response_text += "Please reply with the movie number to post to Blogger."

    # Store movies in context for selection
    context.user_data["movies"] = movies
    await update.message.reply_text(response_text)

async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        selection = int(update.message.text) - 1
        movies = context.user_data.get("movies", [])
        if selection < 0 or selection >= len(movies):
            await update.message.reply_text("Invalid selection. Try again.")
            return

        # Selected movie details
        selected_movie = movies[selection]
        title = selected_movie.get("title", "N/A")
        overview = selected_movie.get("overview", "No description available.")
        poster_path = selected_movie.get("poster_path", "")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "No poster available."

        # Post to Blogger
        content = f"<h2>{title}</h2><p>{overview}</p>"
        if poster_path:
            content += f'<img src="{poster_url}" alt="{title} poster"/>'
        create_blogger_post(title, content)

        await update.message.reply_text(f"Posted to Blogger: {title}")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("An error occurred while posting to Blogger.")

# Main function
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set.")
    
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("movie", handle_movie_search))
    app.add_handler(CommandHandler("select", handle_movie_selection))

    app.run_polling()

if __name__ == "__main__":
    main()
