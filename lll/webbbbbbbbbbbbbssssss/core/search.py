import requests
import os

GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
SEARCH_ENGINE_ID = "YOUR_CSE_ID"

def google_search(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query,
        "num": 5
    }

    r = requests.get(url, params=params)
    results = r.json().get("items", [])
    return [item["link"] for item in results]
