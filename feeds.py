import feedparser
import re
import logging

logger = logging.getLogger(__name__)

def clean_summary(raw_html: str, max_chars: int = 400) -> str:
    """Removes HTML tags and normalizes whitespace in the feed summary."""
    if not raw_html:
        return ""
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
    # Replace multiple spaces/newlines with a single space
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    # Trim to max_chars
    if len(clean_text) > max_chars:
        clean_text = clean_text[:max_chars].rsplit(' ', 1)[0] + "..."
    return clean_text

def fetch_articles(category_slug: str = None, max_items: int = 100) -> list[dict]:
    """Fetches up to max_items articles from the News in Levels feed (optionally filtered by category)."""
    if category_slug:
        url = f"https://www.newsinlevels.com/category/{category_slug}/feed/"
    else:
        url = "https://www.newsinlevels.com/feed/"
        
    logger.info(f"Fetching RSS feed from {url}")
    try:
        feed = feedparser.parse(url)
        
        # Check for parsing errors
        if getattr(feed, "bozo", 0) == 1 and not feed.entries:
            logger.error(f"Failed to parse RSS feed. Bozo exception: {feed.bozo_exception}")
            return []
            
        if not feed.entries:
            logger.warning("No entries found in the RSS feed.")
            return []
        
        articles = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "Untitled").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            
            articles.append({
                "title": title,
                "url": link,
                "summary": clean_summary(summary)
            })
        
        logger.info(f"Successfully fetched {len(articles)} articles.")
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles from feed: {e}")
        return []
