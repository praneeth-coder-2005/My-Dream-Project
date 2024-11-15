import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# Bot token and channel ID
BOT_TOKEN = "8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo"
CHANNEL_ID = -1002260555414  # Replace with your channel ID

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

# TMDB configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Function to create or update a WordPress post
def create_wordpress_post(title, content, download_links=None):
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "content": content,
        "status": "publish",  # Change to "draft" if needed
    }
    if download_links:
        data["content"] += f"<br><strong>Download Links:</strong><ul>"
        for link in download_links:
            data["content"] += f'<li><a href="{link["url"]}">{link["title"]}</a></li>'
        data["content"] += "</ul>"

    response = requests.post(
        POSTS_API_ENDPOINT,
        headers=headers,
        json=data,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 201:
        return response.json().get("link")
    else:
        print(f"Failed to create post: {response.status_code} - {response.text}")
        return None

# Function to fetch movie details from TMDB
def get_movie_details_tmdb(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    try:
        response = requests.get(TMDB_API_URL, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                movie = results[0]
                return {
                    "title": movie.get("title"),
                    "release_date": movie.get("release_date", "Unknown Date"),
                    "overview": movie.get("overview", "No overview available."),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
                }
        return None
    except Exception as e:
        print(f"Error fetching movie details: {str(e)}")
        return None

# Function to fetch WordPress post content
def fetch_wordpress_post_content(post_id):
    response = requests.get(
        f"{POSTS_API_ENDPOINT}/{post_id}",
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        return response.json().get("content", {}).get("rendered", "")
    return ""

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
    response = requests.get(
        POSTS_API_ENDPOINT,
        auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
    )
    if response.status_code == 200:
        posts = response.json()
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
        [InlineKeyboardButton("Add Video Player", callback_data=f"addvideo_{post_id}")],
        [InlineKeyboardButton("Add Download Link", callback_data=f"addlink_{post_id}")]
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
    context.user_data["awaiting_video_url"] = True
    await query.edit_message_text("Send the source URL for the video file:")

async def handle_video_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_video_url"):
        post_id = context.user_data["addvideo_post_id"]
        video_url = update.message.text
        context.user_data["awaiting_video_url"] = False

        # JWPlayer code
        video_player_code = f"""
        <script src="//content.jwplatform.com/libraries/IDzF9Zmk.js"></script>
        <div id="my-video1"></div>
        <script>
        jwplayer('my-video1').setup({{
            "playlist": [
                {{
                    "sources": [
                        {{
                            "file": "{video_url}",
                            "label": "HD"
                        }}
                    ]
                }}
            ],
            "primary": "html5",
            "autostart": false
        }});
        </script>
        """

        # Fetch current post content
        current_content = fetch_wordpress_post_content(post_id)
        new_content = f"{current_content}<br>{video_player_code}"
        success = update_wordpress_post(post_id, new_content)
        if success:
            await update.message.reply_text(f"Video player added successfully to Post {post_id}!")
        else:
            await update.message.reply_text(f"Failed to add video player to Post {post_id}.")

# Function to process channel messages
async def process_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CHANNEL_ID:
        message_text = update.channel_post.text
        if "http" in message_text:
            lines = message_text.splitlines()
            movie_name = lines[0].strip()
            links = [{"title": "Download Link", "url": line.strip()} for line in lines[1:] if line.startswith("http")]

            movie_details = get_movie_details_tmdb(movie_name)
            if movie_details:
                content = (
                    f"<h2>{movie_details['title']}</h2>"
                    f"<p>Release Date: {movie_details['release_date']}</p>"
                    f"<p>Overview: {movie_details['overview']}</p>"
                )
                post_url = create_wordpress_post(movie_details["title"], content, download_links=links)
                if post_url:
                    await update.channel_post.reply_text(f"Movie uploaded successfully: {post_url}")
                else:
                    await update.channel_post.reply_text("Failed to upload movie to WordPress.")

# Main Function
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list_posts", list_posts))
    application.add_handler(CallbackQueryHandler(handle_post_action, pattern="^post_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_add_video_player, pattern="^addvideo_\\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_player_input))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, process_channel_message))

    application.run_polling()

if __name__ == "__main__":
    main()
