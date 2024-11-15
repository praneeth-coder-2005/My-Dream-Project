import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Initialize global variables
search_results = []
last_query = ""

# Blogger API Setup
SCOPES = ['https://www.googleapis.com/auth/blogger']
SERVICE_ACCOUNT_FILE = 'path/to/client_secrets.json'  # Update with the path to your service account JSON

# Authenticate using the service account JSON file
def authenticate_blogger():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('blogger', 'v3', credentials=credentials)
    return service

# Function to create a post on Blogger
def create_blogger_post(service, blog_id, title, content):
    post_body = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    post = service.posts().insert(blogId=blog_id, body=post_body).execute()
    return post.get("url")  # Returns the URL of the created post

# Function to fetch movie details (Mockup example for demonstration)
def get_movie_details(query):
    # Mockup data; replace with API call (e.g., TMDb API)
    return [
        {
            "title": "Kanguva",
            "release_date": "2024-11-14",
            "overview": "A story of courage and vengeance set in a mythical era.",
            "genres": ["Action", "Adventure"],
            "rating": "8.5",
            "runtime": "120 minutes",
            "poster": "https://example.com/poster.jpg"  # Mock poster URL
        },
        {
            "title": "Kanguva - Part Two",
            "release_date": "2027-01-13",
            "overview": "The thrilling continuation of the Kanguva saga.",
            "genres": ["Action", "Fantasy"],
            "rating": "8.8",
            "runtime": "130 minutes",
            "poster": "https://example.com/poster2.jpg"  # Mock poster URL
        }
    ]

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Please send me a movie name to search.")

# Handle movie search
async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global search_results, last_query

    user_input = update.message.text.strip()
    if user_input.isdigit() and search_results:  # User selects a movie
        movie_index = int(user_input) - 1
        if 0 <= movie_index < len(search_results):
            selected_movie = search_results[movie_index]
            response = (
                f"**Title:** {selected_movie['title']}\n"
                f"**Release Date:** {selected_movie['release_date']}\n"
                f"**Overview:** {selected_movie['overview']}\n"
                f"**Genres:** {', '.join(selected_movie['genres'])}\n"
                f"**Rating:** {selected_movie['rating']}/10\n"
                f"**Runtime:** {selected_movie['runtime']}"
            )
            await update.message.reply_text(response, parse_mode="Markdown")

            # Prepare the content for the blog post
            blog_content = (
                f"<h2>{selected_movie['title']}</h2>"
                f"<p><strong>Release Date:</strong> {selected_movie['release_date']}</p>"
                f"<p><strong>Overview:</strong> {selected_movie['overview']}</p>"
                f"<p><strong>Genres:</strong> {', '.join(selected_movie['genres'])}</p>"
                f"<p><strong>Rating:</strong> {selected_movie['rating']}/10</p>"
                f"<p><strong>Runtime:</strong> {selected_movie['runtime']}</p>"
                f"<img src='{selected_movie['poster']}' alt='Movie Poster'>"
            )

            # Authenticate and post to Blogger
            service = authenticate_blogger()
            blog_id = '2426657398890190336'  # Replace with your Blogger blog ID
            post_url = create_blogger_post(service, blog_id, selected_movie['title'], blog_content)

            await update.message.reply_text(f"Posted to Blogger! Check it here: {post_url}")
        else:
            await update.message.reply_text("Invalid selection. Please try again.")
    else:  # User inputs a new movie query
        last_query = user_input
        search_results = get_movie_details(user_input)
        if search_results:
            response = "Found movies:\n"
            for idx, movie in enumerate(search_results, start=1):
                response += f"{idx}. {movie['title']} ({movie['release_date']})\n"
            response += "Please reply with the movie number."
        else:
            response = "No movies found. Please try a different query."
        await update.message.reply_text(response)

# Main function to set up the bot
def main():
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))

    application.run_polling()

if __name__ == "__main__":
    main()
