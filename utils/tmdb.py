import requests

TMDB_API_KEY = "YOUR_TMDB_API_KEY"
TMDB_API_URL = "https://api.themoviedb.org/3/search/movie"

def search_tmdb_movie(movie_name):
    params = {"api_key": TMDB_API_KEY, "query": movie_name}
    response = requests.get(TMDB_API_URL, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            movie = results[0]
            title = movie.get("title")
            release_date = movie.get("release_date", "Unknown Date")
            overview = movie.get("overview", "No overview available.")
            content = f"<h2>{title}</h2><p>Release Date: {release_date}</p><p>{overview}</p>"
            image_url = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
            return title, content, image_url
    return None
