import os
import requests
from requests.auth import HTTPBasicAuth
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# WordPress credentials and base URL from environment variables
WORDPRESS_USERNAME = os.getenv('WORDPRESS_USERNAME')
WORDPRESS_PASSWORD = os.getenv('WORDPRESS_PASSWORD')
WORDPRESS_SITE_URL = os.getenv('WORDPRESS_SITE_URL')

# TMDB API configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = "https://api.themoviedb.org/3/search/movie"

# Function to fetch movie details from TMDB API
def get_movie_details(query):
    url = f"{TMDB_BASE_URL}?api_key={TMDB_API_KEY}&query={query}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [
            {"title": movie["title"], "release_date": movie.get("release_date", "Unknown Date"), "overview": movie.get("overview", "No description available.")}
            for movie in data.get("results", [])
        ]
    else:
        print("Error fetching movies:", response.json())
        return []

# Function to post a new blog post to WordPress
def post_to_wordpress(title, content):
    url = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"
    headers = {'Content-Type': 'application/json'}
    data = {'title': title, 'content': content, 'status': 'publish'}
    response = requests.post(url, json=data, headers=headers, auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_PASSWORD))
    
    if response.status_code == 201:
        print("Post created successfully:", response.json().get("link"))
        return response.json().get("link")
    else:
        print("Failed to create post:", response.json())
        return None

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Type the name of a movie to search for its details.")

# Function to handle movie search
async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    movies = get_movie_details(query)
    
    if not movies:
        await update.message.reply_text("No movies found. Please try a different search term.")
        return
    
    # Store movies in context for selection
    context.user_data['movies'] = movies
    reply_text = f"Found movies for '{query}':\n" + "\n".join([f"{i+1}. {movie['title']} ({movie['release_date']})" for i, movie in enumerate(movies)])
    reply_text += "\nPlease reply with the movie number to post to WordPress."
    
    # Save search state
    context.user_data['search_active'] = True
    await update.message.reply_text(reply_text)

# Function to handle movie selection
async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('search_active'):
        await update.message.reply_text("Please start by searching for a movie first.")
        return

    try:
        choice = int(update.message.text) - 1
        movies = context.user_data.get('movies', [])
        
        if 0 <= choice < len(movies):
            selected_movie = movies[choice]
            title = selected_movie['title']
            content = f"<p><strong>Title:</strong> {selected_movie['title']}</p><p><strong>Release Date:</strong> {selected_movie['release_date']}</p><p><strong>Description:</strong> {selected_movie['overview']}</p>"
            
            link = post_to_wordpress(title, content)
            if link:
                await update.message.reply_text(f"Posted '{title}' to WordPress. View it here: {link}")
            else:
                await update.message.reply_text("An error occurred while posting to WordPress.")
            
            # Reset search state
            context.user_data['search_active'] = False
        else:
            await update.message.reply_text("Please enter a valid movie number.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")

# Set up the Telegram bot handlers
def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_selection))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
