from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

TOPICS = [
    {"name": "Exercises", "slug": "exercises"},
    {"name": "Funny", "slug": "funny"},
    {"name": "History", "slug": "history"},
    {"name": "Information", "slug": "information"},
    {"name": "Interesting", "slug": "interesting"},
    {"name": "Nature", "slug": "nature"},
    {"name": "News", "slug": "news"},
    {"name": "Sport", "slug": "sport"},
]

def get_current_topic() -> dict:
    """Calculates the current topic using a 2-day rotation cycle based on GMT+7 date."""
    epoch = date(2026, 1, 1)
    # Get current date in Vietnam time (GMT+7)
    vn_now = datetime.utcnow() + timedelta(hours=7)
    today = vn_now.date()
    
    days = (today - epoch).days
    index = (days // 2) % len(TOPICS)
    topic = TOPICS[index]
    logger.info(f"Days since epoch: {days}. Topic Index: {index}. Current Topic: '{topic['name']}' (slug: '{topic['slug']}')")
    return topic

def get_this_week_topic() -> str:
    """Legacy compatibility function. Returns the current topic name."""
    return get_current_topic()["name"]
