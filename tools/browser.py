"""
Browser and Web Controller Tool (open_website, web_search, play_youtube)
"""

import webbrowser
import urllib.parse
from config import log_event

KNOWN_SITES = {
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "leetcode": "https://leetcode.com",
    "codeforces": "https://codeforces.com",
    "chatgpt": "https://chatgpt.com",
    "google": "https://www.google.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
}

def open_website(url_or_query: str) -> str:
    """
    Open any website in the default browser.
    Known sites map to their URLs. Anything unknown becomes a Google search.
    """
    log_event("TOOL:OPEN_WEBSITE", f"Query: '{url_or_query}'")
    q = url_or_query.strip().lower()

    # Check known sites
    for key, url in KNOWN_SITES.items():
        if key in q or q in key:
            webbrowser.open(url)
            log_event("TOOL:OPEN_WEBSITE", f"Matched known site: '{key}' -> {url}")
            return f"Opening {key.title()}, Sir."

    # Direct URL check
    if q.startswith("http://") or q.startswith("https://"):
        webbrowser.open(url_or_query.strip())
        return f"Opening link, Sir."
    elif "." in q and " " not in q:
        url = "https://" + q
        webbrowser.open(url)
        return f"Opening {q}, Sir."

    # Fallback to Google Search
    encoded = urllib.parse.quote(url_or_query)
    search_url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(search_url)
    log_event("TOOL:OPEN_WEBSITE", f"No direct site matched. Searching Google for: '{url_or_query}'")
    return f"Searching Google for '{url_or_query}', Sir."

def web_search(query: str) -> str:
    """Perform a web search on Google."""
    log_event("TOOL:WEB_SEARCH", f"Searching for: '{query}'")
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    return f"Here are the search results for '{query}', Sir."

def play_youtube(query: str) -> str:
    """Search and play a video or topic on YouTube."""
    log_event("TOOL:PLAY_YOUTUBE", f"Query: '{query}'")
    encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    return f"Searching YouTube for '{query}', Sir."
