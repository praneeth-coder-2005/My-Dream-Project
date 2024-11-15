import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from requests.auth import HTTPBasicAuth

# WordPress REST API configuration
WORDPRESS_SITE_URL = "https://clawfilezz.in"
WORDPRESS_USERNAME = "admin"
WORDPRESS_APP_PASSWORD = "Ehvh Ryr0 WXnI Z61H wdI6 ilVP"

# TMDB API configuration
TMDB_API_KEY = "bb5f40c5be4b24660cbdc20c2409835e"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

# Telegram bot token and channel ID
BOT_TOKEN = "8148506170:AAHPk5Su4ADx3pg2iRlbLTVOv7PlnNIDNqo"
CHANNEL_ID = -1002260555414

# WordPress REST API endpoint
POSTS_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"
MEDIA_API_ENDPOINT = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/media"

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
        return None

# Function to upload a featured image to WordPress
def upload_image_to_wordpress(image_url):
    try:
        if image_url:
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
    except Exception as e:
        pass
    return None

# Function to create or update WordPress posts
def create_or_update_wordpress_post(title, content, download_links=None, poster_id=None, video_player_code=None):
    headers = {"Content-Type": "application/json"}

    # Check if post exists
    response = requests.get(POSTS_API_ENDPOINT, params={"search": title}, auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD))
    existing_posts = response.json()

    if existing_posts:
        post_id = existing_posts[0]["id"]
        current_content = existing_posts[0]["content"]["rendered"]
        for link in download_links or []:
            current_content += f'<br><a href="{link["url"]}">{link["title"]}</a>'
        if video_player_code:
            current_content += f"<br>{video_player_code}"
        update_data = {"content": current_content}
        requests.post(f"{POSTS_API_ENDPOINT}/{post_id}", headers=headers, json=update_data, auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD))
        return existing_posts[0]["link"]

    else:
        data = {
            "title": title,
            "content": content,
            "status": "publish"
        }
        if poster_id:
            data["featured_media"] = poster_id

        if download_links:
            for link in download_links:
                data["content"] += f'<br><a href="{link["url"]}">{link["title"]}</a>'
        if video_player_code:
            data["content"] += f"<br>{video_player_code}"

        response = requests.post(
            POSTS_API_ENDPOINT,
            headers=headers,
            json=data,
            auth=HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD)
        )
        if response.status_code == 201:
            return response.json().get("link")
    return None

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the WordPress automation bot!")

async def process_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CHANNEL_ID:
        message_text = update.channel_post.text
        if not message_text:
            await update.channel_post.reply_text("No valid content found in the message.")
            return

        # Extract movie name and links
        lines = message_text.splitlines()
        movie_name = None
        download_links = []

        for line in lines:
            if line.startswith("📂 Fɪʟᴇ ɴᴀᴍᴇ :"):
                movie_name = line.split(":", 1)[1].strip()
            elif line.startswith("📥 Dᴏᴡɴʟᴏᴀᴅ :"):
                download_links.append({"title": "Download Link", "url": line.split(":", 1)[1].strip()})

        if not movie_name or not download_links:
            await update.channel_post.reply_text("Could not extract movie details or download links.")
            return

        # Fetch movie details from TMDB
        movie_details = get_movie_details_tmdb(movie_name)
        if not movie_details:
            await update.channel_post.reply_text(f"Could not find movie '{movie_name}' on TMDB.")
            return

        # Prepare post content
        content = (
            f"<h2>{movie_details['title']}</h2>"
            f"<p>Release Date: {movie_details['release_date']}</p>"
            f"<p>Overview: {movie_details['overview']}</p>"
        )

        # Video player code
        video_player_code = f"""
        <script src="//content.jwplatform.com/libraries/IDzF9Zmk.js"></script>
        <div id="my-video1"></div>
        <script>
        // <![CDATA[
        jwplayer('my-video1').setup({{
          "playlist": [
            {{
              "sources": [
                {{
                  "default": true,
                  "type": "mp4",
                  "file": "{download_links[0]['url']}",
                  "label": "HD"
                }}
              ]
            }}
          ],
          "primary": "html5",
          "hlshtml": true,
          "autostart": false
        }});
        // ]]>
        </script>
        """

        # Upload poster and create/update post
        poster_id = upload_image_to_wordpress(movie_details["poster_path"])
        post_url = create_or_update_wordpress_post(movie_details["title"], content, download_links, poster_id, video_player_code)

        if post_url:
            await update.channel_post.reply_text(f"Movie '{movie_details['title']}' uploaded successfully: {post_url}")
        else:
            await update.channel_post.reply_text(f"Failed to upload movie '{movie_details['title']}'.")

# Main function
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL, process_channel_message))

    application.run_polling()

if __name__ == "__main__":
    main()
