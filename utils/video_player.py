def generate_video_player_html(video_url):
    return f"""
    <script src="//content.jwplatform.com/libraries/IDzF9Zmk.js"></script>
    <div id="my-video"></div>
    <script>
    jwplayer('my-video').setup({{
        "file": "{video_url}",
        "autostart": false
    }});
    </script>
    """
