import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# TMDb API Configuration
TMDB_API_KEY = 'your_tmdb_api_key'
TMDB_BASE_URL = 'https://api.themoviedb.org/3/search/movie'

# Blogger API Configuration
SCOPES = ['https://www.googleapis.com/auth/blogger']
BLOG_ID = 'your_blog_id'  # Your Blog ID from Blogger

# Step 1: Fetch movie details using TMDb API
def get_movie_details(movie_name):
    url = f'{TMDB_BASE_URL}?api_key={TMDB_API_KEY}&query={movie_name}'
    response = requests.get(url)
    data = response.json()
    
    if data['results']:
        return data['results']  # Return the list of search results
    return []

# Step 2: Authenticate with Google OAuth
def authenticate_blogger():
    flow = InstalledAppFlow.from_client_secrets_file(
        'your_client_secrets.json', SCOPES)
    credentials = flow.run_local_server(port=8080)
    blogger_service = build('blogger', 'v3', credentials=credentials)
    return blogger_service

# Step 3: Create a blog post on Blogger
def post_to_blogger(blogger_service, title, description, download_link):
    try:
        post_data = {
            'title': title,
            'content': f'<h2>{title}</h2><p>{description}</p><a href="{download_link}">Download Here</a>'
        }
        blogger_service.posts().insert(blogId=BLOG_ID, body=post_data).execute()
        print("Post successfully created!")
    except HttpError as err:
        print(f"An error occurred: {err}")

# Step 4: Display multiple movie options and allow selection
def select_movie(movies):
    print("Multiple movies found with the same title. Please choose the correct one:")
    for index, movie in enumerate(movies):
        print(f"{index + 1}. {movie['title']} ({movie.get('release_date', 'Unknown')})")
    
    # Get user input for movie selection
    try:
        choice = int(input("Enter the number of the movie to select: ")) - 1
        if 0 <= choice < len(movies):
            return movies[choice]
        else:
            print("Invalid choice. Exiting.")
            return None
    except ValueError:
        print("Invalid input. Exiting.")
        return None

# Main Execution
def main():
    movie_name = input("Enter the movie name: ")  # Input movie name
    download_link = input("Enter the download link: ")  # Input download link
    
    # Step 1: Fetch movie details
    movies = get_movie_details(movie_name)
    
    if movies:
        # Step 4: Display multiple movie options and allow selection
        selected_movie = select_movie(movies)
        
        if selected_movie:
            title = selected_movie['title']
            description = selected_movie['overview']
            
            # Step 2: Authenticate with Blogger API
            blogger_service = authenticate_blogger()
            
            # Step 3: Post movie details to Blogger
            post_to_blogger(blogger_service, title, description, download_link)
        else:
            print("No movie selected. Exiting.")
    else:
        print(f"No movies found with the title '{movie_name}'.")

if __name__ == '__main__':
    main()
