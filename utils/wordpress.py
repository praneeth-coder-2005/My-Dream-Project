import requests
from requests.auth import HTTPBasicAuth

WORDPRESS_SITE_URL = "https://yourwordpresssite.com"
USERNAME = "admin"
PASSWORD = "application_password"

POSTS_API = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/posts"

def list_posts():
    response = requests.get(POSTS_API, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    return response.json() if response.status_code == 200 else []

def create_post(title, content, image_url=None):
    data = {"title": title, "content": content, "status": "publish"}
    response = requests.post(POSTS_API, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    return response.json().get("link") if response.status_code == 201 else None
