import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://ClawFilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilV"

# WordPress REST API endpoint for creating posts
API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# TMDB API configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Function to get detailed movie information
def get_movie_details(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    response = requests.get(TMDB_API_URL, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        return [
            {
                "title": movie.get("title"),
                "release_date": movie.get("release_date", "Unknown Date"),
                "overview": movie.get("overview", "No overview available."),
                "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None
            }
            for movie in results
        ]
    else:
        return []

# Function to create a WordPress post using REST API
def create_wordpress_post(title, content, status="publish", categories=[], tags=[]):
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "content": content,
        "status": status,
        "categories": categories,
        "tags": tags
    }

    # Make a POST request to WordPress
    response = requests.post(
        API_ENDPOINT,
        headers=headers,
        json=data,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_PASSWORD)
    )

    if response.status_code == 201:
        return response.json().get("link")
    else:
        return f"Failed to create post: {response.status_code} - {response.text}"

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a movie name to search.")

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_name = update.message.text
    movies = get_movie_details(movie_name)
    if movies:
        keyboard = [
            [InlineKeyboardButton(f"{movie['title']} ({movie['release_date']})", callback_data=str(i))]
            for i, movie in enumerate(movies[:10])
        ]
        context.user_data["movies"] = movies
        await update.message.reply_text(
            f"Found movies for '{movie_name}': Select a movie to post to WordPress.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("No movies found.")

async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_index = int(query.data)
    movies = context.user_data.get("movies", [])
    if 0 <= selected_index < len(movies):
        selected_movie = movies[selected_index]
        title = selected_movie["title"]
        poster_url = selected_movie["poster_path"]
        overview = selected_movie["overview"]
        content = f"<h2>{title}</h2><p><strong>Release Date:</strong> {selected_movie['release_date']}</p><p>{overview}</p>"
        if poster_url:
            content += f'<p><img src="{poster_url}" alt="{title} poster"></p>'
        
        # Create post with additional details and custom status
        post_url = create_wordpress_post(title, content, status="publish", categories=[1], tags=[1])
        
        if "http" in post_url:
            await query.edit_message_text(f"Post successfully created: {post_url}")
        else:
            await query.edit_message_text(f"Error posting to WordPress: {post_url}")
    else:
        await query.edit_message_text("Invalid selection.")

# Main Function
def main():
    application = ApplicationBuilder().token("8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection))

    application.run_polling()

if __name__ == "__main__":
    main()
