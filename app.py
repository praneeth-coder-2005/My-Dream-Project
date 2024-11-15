import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth
import logging
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# WordPress REST API endpoints
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"
MEDIA_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/media"

# TMDB API configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Global variables for search history
SEARCH_HISTORY = {}

# Function to upload a featured image to WordPress
def upload_image_to_wordpress(image_url):
    try:
        image_data = requests.get(image_url).content
        headers = {
            "Content-Disposition": "attachment; filename=featured_image.jpg",
            "Content-Type": "image/jpeg"
        }
        response = requests.post(
            MEDIA_API_ENDPOINT,
            headers=headers,
            data=image_data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 201:
            return response.json().get("id")  # Return the media ID
        else:
            return None
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return None

# Function to create a WordPress post
def create_wordpress_post(title, content, categories=None, tags=None, image_id=None, status="publish", date=None):
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "content": content,
        "status": status,  # "publish", "draft", or "future" (for scheduling)
        "categories": categories or [],
        "tags": tags or [],
    }
    if image_id:
        data["featured_media"] = image_id
    if date and status == "future":
        data["date"] = date

    try:
        response = requests.post(
            POSTS_API_ENDPOINT,
            headers=headers,
            json=data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 201:
            return response.json().get("link")
        else:
            return f"Failed to create post: {response.status_code} - {response.text}"
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        return f"Error during post creation: {str(e)}"

# Function to fetch movie details from TMDB
def get_movie_details(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    try:
        response = requests.get(TMDB_API_URL, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [
                {
                    "title": movie.get("title"),
                    "release_date": movie.get("release_date", "Unknown Date"),
                    "overview": movie.get("overview", "No overview available."),
                    "popularity": movie.get("popularity"),
                    "vote_average": movie.get("vote_average"),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
                }
                for movie in results
            ]
        else:
            return []
    except Exception as e:
        logger.error(f"Error fetching movie details: {e}")
        return []

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    SEARCH_HISTORY[user_id] = []
    await update.message.reply_text("Welcome! Send a movie name to search or type /help for guidance.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use this bot:\n"
        "1. Send a movie name to search.\n"
        "2. Select a movie from the list.\n"
        "3. Choose whether to publish immediately, save as a draft, or schedule a post."
    )

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    movie_name = update.message.text
    movies = get_movie_details(movie_name)
    if movies:
        SEARCH_HISTORY[user_id] = movies
        keyboard = [
            [InlineKeyboardButton(f"{movie['title']} ({movie['release_date']})", callback_data=str(i))]
            for i, movie in enumerate(movies[:10])
        ]
        await update.message.reply_text(
            f"Found movies for '{movie_name}': Select a movie to post to WordPress.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("No movies found.")

async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    selected_index = int(query.data)
    movies = SEARCH_HISTORY.get(user_id, [])
    if 0 <= selected_index < len(movies):
        selected_movie = movies[selected_index]
        title = selected_movie["title"]
        content = (
            f"<h2>{title}</h2>"
            f"<p>Release Date: {selected_movie['release_date']}</p>"
            f"<p>Overview: {selected_movie['overview']}</p>"
            f"<p>Popularity: {selected_movie['popularity']}</p>"
            f"<p>Vote Average: {selected_movie['vote_average']}</p>"
        )
        image_id = upload_image_to_wordpress(selected_movie["poster_path"]) if selected_movie["poster_path"] else None

        keyboard = [
            [InlineKeyboardButton("Publish Now", callback_data=f"publish_{selected_index}")],
            [InlineKeyboardButton("Save as Draft", callback_data=f"draft_{selected_index}")],
            [InlineKeyboardButton("Schedule Post", callback_data=f"schedule_{selected_index}")]
        ]
        context.user_data.update({"title": title, "content": content, "image_id": image_id})
        await query.edit_message_text(
            f"Title: {title}\nRelease Date: {selected_movie['release_date']}\nHow would you like to post this?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text("Invalid selection.")

async def handle_post_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, selected_index = query.data.split("_")
    user_id = query.from_user.id
    movies = SEARCH_HISTORY.get(user_id, [])
    if 0 <= int(selected_index) < len(movies):
        title = context.user_data["title"]
        content = context.user_data["content"]
        image_id = context.user_data["image_id"]

        if action == "publish":
            post_url = create_wordpress_post(title, content, image_id=image_id, status="publish")
        elif action == "draft":
            post_url = create_wordpress_post(title, content, image_id=image_id, status="draft")
        elif action == "schedule":
            # Schedule the post for a specific time (example: 24 hours later)
            scheduled_time = (datetime.now() + timedelta(days=1)).isoformat()
            post_url = create_wordpress_post(title, content, image_id=image_id, status="future", date=scheduled_time)
        else:
            post_url = "Invalid action"

        if "http" in post_url:
            await query.edit_message_text(f"Post successfully created: {post_url}")
        else:
            await query.edit_message_text(f"Error posting to WordPress: {post_url}")
    else:
        await query.edit_message_text("Invalid selection.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7Pl9PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection, pattern=r"^\d+$"))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern=r"^(publish|draft|schedule)_\d+$"))

    application.run_polling()

if __name__ == "__main__":
    main()
