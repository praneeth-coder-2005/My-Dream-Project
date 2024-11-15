from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
import requests

# WordPress XML-RPC configuration
WORDPRESS_XMLRPC_URL = "https://clawfilezz.in/xmlrpc.php"
WORDPRESS_USERNAME = "admin"  # Replace with your username
WORDPRESS_PASSWORD = "pass"   # Replace with your password

# TMDB API Integration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"  # Replace with your TMDB API Key
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

def get_movie_details(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    response = requests.get(TMDB_API_URL, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        return [
            {"title": movie.get("title"), "release_date": movie.get("release_date", "Unknown Date")}
            for movie in results
        ]
    else:
        return []

# Function to create a WordPress post using XML-RPC
def create_wordpress_post(title, content):
    # Set up the XML-RPC client
    client = Client(WORDPRESS_XMLRPC_URL, WORDPRESS_USERNAME, WORDPRESS_PASSWORD)
    
    # Create a new post
    post = WordPressPost()
    post.title = title
    post.content = content
    post.post_status = 'publish'  # You can use 'draft' if you don't want to publish immediately
    
    try:
        post_id = client.call(NewPost(post))
        post_url = f"{WORDPRESS_XMLRPC_URL}?p={post_id}"
        return post_url
    except Exception as e:
        return f"Error: {str(e)}"

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
        content = f"<h2>{title}</h2><p>Release Date: {selected_movie['release_date']}</p>"
        post_url = create_wordpress_post(title, content)
        if "http" in post_url:
            await query.edit_message_text(f"Post successfully created: {post_url}")
        else:
            await query.edit_message_text(f"Error posting to WordPress: {post_url}")
    else:
        await query.edit_message_text("Invalid selection.")

# Main Function
def main():
    TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"  # Replace with your Telegram bot token
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    application.add_handler(CallbackQueryHandler(handle_movie_selection))

    application.run_polling()

if __name__ == "__main__":
    main()
