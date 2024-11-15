import os
import json
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


# Authenticate Blogger API using Service Account
def authenticate_blogger():
    service_account_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not service_account_json:
        raise ValueError("Environment variable GOOGLE_APPLICATION_CREDENTIALS_JSON not found.")
    
    credentials_info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/blogger"]
    )
    return build('blogger', 'v3', credentials=credentials)


# Fetch movies from TMDB API
def fetch_movies_from_tmdb(query):
    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    if not tmdb_api_key:
        raise ValueError("TMDB_API_KEY environment variable not set.")

    url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={query}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("results", [])
    else:
        raise ValueError(f"Failed to fetch movies from TMDB: {response.status_code}")


# Post to Blogger
async def post_to_blogger(service, blog_id, title, content):
    body = {
        "title": title,
        "content": content,
        "labels": ["Telegram Bot", "Movies"],
    }
    post = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
    return post


# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a movie name to search and post to Blogger!")


# Handle Search Query
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    context.user_data["query"] = query
    await update.message.reply_text(f"Searching for movies related to '{query}'...")

    try:
        movies = fetch_movies_from_tmdb(query)
        if not movies:
            await update.message.reply_text(f"No movies found for '{query}'. Please try another search.")
            return

        context.user_data["movies"] = movies  # Save movies in context
        response = "Found movies:\n"
        for i, movie in enumerate(movies, start=1):
            response += f"{i}. {movie['title']} ({movie.get('release_date', 'Unknown Date')})\n"
        response += "Please reply with the movie number to post to Blogger."
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"An error occurred while searching for movies: {str(e)}")


# Handle Movie Selection
async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = context.user_data.get("movies", [])
    if not movies:
        await update.message.reply_text("No movies found. Please search again.")
        return

    try:
        # Make sure the input is a valid number and within the range of available movie numbers
        user_input = update.message.text.strip()
        movie_index = int(user_input) - 1  # Convert input to index
        if movie_index < 0 or movie_index >= len(movies):
            await update.message.reply_text("Invalid movie number. Please enter a number between 1 and " + str(len(movies)) + ".")
            return
        
        selected_movie = movies[movie_index]
        service = authenticate_blogger()
        blog_id = "2426657398890190336"  # Your Blogger blog ID

        # Build content with movie details
        title = selected_movie["title"]
        content = f"**Title:** {selected_movie['title']}<br>"
        content += f"**Overview:** {selected_movie.get('overview', 'No description available.')}<br>"
        content += f"**Release Date:** {selected_movie.get('release_date', 'Unknown Date')}<br>"

        # Post to Blogger
        post = await post_to_blogger(service, blog_id, title, content)
        await update.message.reply_text(f"Posted to Blogger! View it here: {post['url']}")
    except ValueError:
        await update.message.reply_text("Please enter a valid movie number.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")


# Main Function
def main():
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable not set.")

    application = Application.builder().token(bot_token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^\d+$"), handle_message))
    application.add_handler(MessageHandler(filters.Regex(r"^\d+$"), handle_movie_selection))

    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
