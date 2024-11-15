import requests
from imdb import IMDb
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"
MEDIA_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/media"

# TMDB and IMDb configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Initialize IMDb instance
ia = IMDb()

# Function to upload a featured image to WordPress
def upload_image_to_wordpress(image_url):
    try:
        image_data = requests.get(image_url).content
        headers = {
            "Content-Disposition": f"attachment; filename=featured_image.jpg",
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
        return None

# Function to create a WordPress post
def create_wordpress_post(title, content, categories=None, tags=None, image_id=None, status="publish"):
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "content": content,
        "status": status,  # "publish" or "draft"
        "categories": categories or [],
        "tags": tags or []
    }
    if image_id:
        data["featured_media"] = image_id

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
        return f"Error during post creation: {str(e)}"

# Function to fetch movie details from TMDB
def get_movie_details_tmdb(movie_name):
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
        return []

# Function to fetch movie details from IMDb
def get_movie_details_imdb(movie_name):
    imdb_movies = ia.search_movie(movie_name)
    if imdb_movies:
        movie = ia.get_movie(imdb_movies[0].movieID)
        return {
            "imdb_rating": movie.get("rating"),
            "votes": movie.get("votes"),
            "genres": ", ".join(movie.get("genres", [])),
            "plot": movie.get("plot outline", "No plot available."),
            "year": movie.get("year", "Unknown Year"),
            "runtime": movie.get("runtimes", ["Unknown Runtime"])[0]
        }
    return {}

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a movie name to search or type /help for guidance.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use this bot:\n"
        "1. Send a movie name to search.\n"
        "2. Select a movie from the list.\n"
        "3. Choose whether to publish immediately or save as a draft."
    )

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_name = update.message.text
    movies = get_movie_details_tmdb(movie_name)
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
        tmdb_content = (
            f"<h2>{title}</h2>"
            f"<p>Release Date: {selected_movie['release_date']}</p>"
            f"<p>Overview: {selected_movie['overview']}</p>"
            f"<p>Popularity: {selected_movie['popularity']}</p>"
            f"<p>Vote Average: {selected_movie['vote_average']}</p>"
        )
        
        # Fetch IMDb details
        imdb_data = get_movie_details_imdb(title)
        imdb_content = (
            f"<p>IMDb Rating: {imdb_data.get('imdb_rating', 'N/A')}</p>"
            f"<p>Votes: {imdb_data.get('votes', 'N/A')}</p>"
            f"<p>Genres: {imdb_data.get('genres', 'N/A')}</p>"
            f"<p>Plot: {imdb_data.get('plot', 'N/A')}</p>"
            f"<p>Year: {imdb_data.get('year', 'N/A')}</p>"
            f"<p>Runtime: {imdb_data.get('runtime', 'N/A')} minutes</p>"
        )

        content = tmdb_content + imdb_content
        image_id = upload_image_to_wordpress(selected_movie["poster_path"]) if selected_movie["poster_path"] else None

        # Allow user to choose publish status
        keyboard = [
            [InlineKeyboardButton("Publish Now", callback_data=f"publish_{selected_index}")],
            [InlineKeyboardButton("Save as Draft", callback_data=f"draft_{selected_index}")]
        ]
        context.user_data.update({"title": title, "content": content, "image_id": image_id})
        await query.edit_message_text(
            "How would you like to post this?\n"
            f"Title: {title}\n"
            f"Release Date: {selected_movie['release_date']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text("Invalid selection.")

# Main Function
def main():
    application = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection, pattern="^[0-9]+$"))

    application.run_polling()

if __name__ == "__main__":
    main()
