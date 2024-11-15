import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# TMDB API configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Function to fetch movie details from TMDB
def get_movie_details_tmdb(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    try:
        response = requests.get(TMDB_API_URL, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                movie = results[0]  # Assuming first result is most relevant
                return {
                    "title": movie.get("title"),
                    "release_date": movie.get("release_date", "Unknown Date"),
                    "overview": movie.get("overview", "No overview available."),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
                }
    except Exception as e:
        return None
    return None

# Function to list posts from WordPress
def list_wordpress_posts():
    response = requests.get(
        POSTS_API_ENDPOINT,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        return response.json()
    else:
        return []

# Function to update a WordPress post
def update_wordpress_post(post_id, content):
    headers = {"Content-Type": "application/json"}
    data = {"content": content}
    response = requests.post(
        f"{POSTS_API_ENDPOINT}/{post_id}",
        headers=headers,
        json=data,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    return response.status_code == 200

# Function to generate download link HTML
def generate_download_link_html(download_title, download_url):
    return f'<a href="{download_url}" target="_blank">{download_title}</a><br>'

# Function to create or update WordPress post with download link handling
def create_or_update_wordpress_post(title, content, download_links):
    headers = {"Content-Type": "application/json"}
    
    # Check if the post already exists based on title
    existing_posts = requests.get(POSTS_API_ENDPOINT, params={'search': title}, auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD))
    if existing_posts.status_code == 200 and existing_posts.json():
        # Post exists, update it
        post_id = existing_posts.json()[0]['id']
        new_content = f"{content}<br><br>{download_links}"  # Append download links to existing content
        data = {"content": new_content}
        response = requests.post(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            headers=headers,
            json=data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
    else:
        # Create new post
        data = {
            "title": title,
            "content": f"{content}<br><br>{download_links}",
            "status": "publish"
        }
        response = requests.post(
            POSTS_API_ENDPOINT,
            headers=headers,
            json=data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
    return response.status_code == 200

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /list_posts to see available posts or type /help for guidance.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available Commands:\n"
        "/list_posts - List all posts on your WordPress site.\n"
        "Interact with posts to edit, delete, or add links and video players."
    )

async def list_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = list_wordpress_posts()
    if posts:
        keyboard = [
            [InlineKeyboardButton(f"{post['title']['rendered']}", callback_data=f"post_{post['id']}")]
            for post in posts
        ]
        await update.message.reply_text(
            "Select a post to manage:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("No posts found.")

async def handle_post_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]

    keyboard = [
        [InlineKeyboardButton("Edit Post", callback_data=f"edit_{post_id}")],
        [InlineKeyboardButton("Delete Post", callback_data=f"delete_{post_id}")],
        [InlineKeyboardButton("Add Download Link", callback_data=f"addlink_{post_id}")],
        [InlineKeyboardButton("Add Video Player", callback_data=f"addvideo_{post_id}")]
    ]
    await query.edit_message_text(
        f"What would you like to do with Post ID {post_id}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_add_video_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split("_")[1]
    context.user_data["addvideo_post_id"] = post_id
    context.user_data["awaiting_video_url"] = True  # Set state for awaiting video URL
    await query.edit_message_text("Send the source URL for the video file:")

async def handle_video_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_video_url"):
        post_id = context.user_data.get("addvideo_post_id")
        video_url = update.message.text
        context.user_data["awaiting_video_url"] = False

        # JWPlayer code with the provided source URL
        video_player_code = f"""
        <script src="//content.jwplatform.com/libraries/IDzF9Zmk.js"></script>
        <div id="my-video1"></div>
        <script>
        jwplayer('my-video1').setup({{
          "playlist": [
            {{
              "sources": [
                {{
                  "default": true,
                  "type": "mp4",
                  "file": "{video_url}",
                  "label": "HD"
                }}
              ]
            }}
          ],
          "primary": "html5",
          "hlshtml": true,
          "autostart": false
        }});
        </script>
        """

        post_response = requests.get(
            f"{POSTS_API_ENDPOINT}/{post_id}",
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if post_response.status_code == 200:
            post_content = post_response.json().get("content", {}).get("rendered", "")
            new_content = f"{post_content}<br>{video_player_code}"
            success = update_wordpress_post(post_id, new_content)
            if success:
                await update.message.reply_text(f"Video player added successfully to Post {post_id}!")
            else:
                await update.message.reply_text(f"Failed to add video player to Post {post_id}.")
        else:
            await update.message.reply_text("Failed to fetch post content.")
        context.user_data.clear()
    else:
        await update.message.reply_text("Unexpected input. Please use /list_posts to start again.")

async def process_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    if "Download link" in message and message.startswith("https://"):
        movie_name = "Extracted movie name"  # Placeholder for extraction logic
        download_url = message.strip()
        
        movie_details = get_movie_details_tmdb(movie_name)
        if movie_details:
            title = movie_details['title']
            content = (
                f"<h2>{title}</h2>"
                f"<p>Release Date: {movie_details['release_date']}</p>"
                f"<p>Overview: {movie_details['overview']}</p>"
            )
            download_link_html = generate_download_link_html("Download Link", download_url)
            success = create_or_update_wordpress_post(title, content, download_link_html)
            if success:
                await update.message.reply_text(f"Movie '{title}' posted or updated on WordPress with download link.")
            else:
                await update.message.reply_text("Failed to post movie details to WordPress.")
        else:
            await update.message.reply_text("Could not fetch movie details from TMDB.")

# Main Function
def main():
    application = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_player_input))
    
    # Channel message handler to process messages from a specific channel
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.CHANNEL, process_channel_message))

    application.run_polling()

if __name__ == "__main__":
    main()
