import webbrowser
import urllib.parse

class WebControl:
    def __init__(self):
        pass

    def search_google(self, query):
        """Search google for a specific query."""
        encoded_query = urllib.parse.quote(query)
        webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
        print(f"Searching for: {query}")
        return True

    def open_url(self, url):
        """Directly open a URL."""
        if not url.startswith("http"):
            url = f"https://{url}"
        webbrowser.open(url)
        return True
