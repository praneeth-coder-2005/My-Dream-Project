import os
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Blogger API authentication
def authenticate_blogger():
    credentials = service_account.Credentials.from_service_account_file(
        'path/to/client_secrets.json',
        scopes=["https://www.googleapis.com/auth/blogger"]
    )
    service = build("blogger", "v3", credentials=credentials)
    return service

# Fetch movie details from TMDB API
def get_movie_details(movie_name):
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("TMDB_API_KEY is not set.")
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": api_key,
        "query": movie_name,
        "include_adult": False,
        "language": "en-US",
        "page": 1
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        sorted_results = sorted(results, key=lambda x: x.get("popularity", 0), reverse=True)
        return sorted_results
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movie details: {e}")
        return []

# Post to Blogger
def post_to_blogger(service, blog_id, title, content, poster_url):
    body = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": title,
        "content": f"<img src='{poster_url}'/><br>{content}"
    }
    try:
        post = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
        return post["url"]
    except Exception as e:
        print(f"Error posting to Blogger: {e}")
        return None

# Handle movie search
async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a movie name to search.")
        return

    movies = get_movie_details(query)
    if not movies:
        await update.message.reply_text(f"No movies found for '{query}'.")
        return

    buttons = [
        [InlineKeyboardButton(f"{i + 1}. {movie['title']} ({movie['release_date']})", callback_data=str(i))]
        for i, movie in enumerate(movies[:10])
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(f"Found movies for '{query}':", reply_markup=reply_markup)
    context.user_data["movies"] = movies

# Handle movie selection
async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_index = int(query.data)
    movies = context.user_data.get("movies", [])
    if movie_index >= len(movies):
        await query.message.reply_text("Invalid selection.")
        return

    movie = movies[movie_index]
    service = authenticate_blogger()
    blog_id = "2426657398890190336"

    title = movie["title"]
    overview = movie.get("overview", "No description available.")
    poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else "https://via.placeholder.com/500"

    post_url = post_to_blogger(service, blog_id, title, overview, poster_url)
    if post_url:
        await query.message.reply_text(f"Movie '{title}' posted to Blogger: {post_url}")
    else:
        await query.message.reply_text(f"Failed to post '{title}' to Blogger.")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Movie Bot! Use /search <movie name> to get started.")

# Main function to run the bot
def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set.")

    application = ApplicationBuilder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection))

    application.run_polling()

if __name__ == "__main__":
    main()
