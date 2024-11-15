import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Function to authenticate with Blogger API
def authenticate_blogger():
    # Get the service account JSON from Heroku's environment variable
    service_account_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not service_account_json:
        raise ValueError("Environment variable GOOGLE_APPLICATION_CREDENTIALS_JSON not found.")
    
    # Parse the JSON from the environment variable
    credentials_info = json.loads(service_account_json)
    
    # Authenticate using service account credentials
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/blogger"]
    )
    
    # Build the Blogger service
    service = build('blogger', 'v3', credentials=credentials)
    return service

# Function to post to Blogger
async def post_to_blogger(service, blog_id, title, content):
    body = {
        "title": title,
        "content": content,
        "labels": ["Telegram Bot", "Movies"],
    }
    post = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
    return post

# Telegram bot command to start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a movie name to search and post to Blogger!")

# Telegram bot message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    await update.message.reply_text(f"Searching for movies related to '{query}'...")

    # Simulate movie details (replace this with your movie API logic)
    movies = [
        {"title": "Example Movie 1", "overview": "Overview for Example Movie 1"},
        {"title": "Example Movie 2", "overview": "Overview for Example Movie 2"},
    ]

    # Send movie options to the user
    response = "Found movies:\n"
    for i, movie in enumerate(movies, start=1):
        response += f"{i}. {movie['title']}\n"
    response += "Please reply with the movie number to post to Blogger."
    await update.message.reply_text(response)

    # Save movies to context for later use
    context.user_data["movies"] = movies

# Telegram bot handler for movie selection
async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get the selected movie index
        movie_index = int(update.message.text) - 1
        movies = context.user_data.get("movies", [])

        if 0 <= movie_index < len(movies):
            selected_movie = movies[movie_index]

            # Post the selected movie to Blogger
            service = authenticate_blogger()
            blog_id = "2426657398890190336"  # Your Blogger blog ID
            post = await post_to_blogger(service, blog_id, selected_movie["title"], selected_movie["overview"])

            await update.message.reply_text(f"Posted to Blogger! View it here: {post['url']}")
        else:
            await update.message.reply_text("Invalid selection. Please try again.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")

# Main function to run the bot
def main():
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable not set.")

    application = Application.builder().token(bot_token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), handle_movie_selection))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
