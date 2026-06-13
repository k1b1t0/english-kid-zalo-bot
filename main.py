import argparse
import sys
import logging
from dotenv import load_dotenv

import feeds
import topic_rotation
import dedup
import curator
import notifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

def main():
    # Load .env file for local testing
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Daily English Learning Bot for Kids")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Print the formatted message to console without calling Zalo API and without updating sent_urls.txt"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock curated article response instead of calling live Gemini API (useful for testing without keys)"
    )
    parser.add_argument(
        "--topic", 
        type=str, 
        help="Manually override the weekly topic (e.g. 'Space & Universe')"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=100, 
        help="Max candidate articles to fetch from the RSS feed (default: 100)"
    )
    args = parser.parse_args()
    
    logger.info("Starting Daily English Bot pipeline...")
    
    # 1. Determine the topic and category slug
    category_slug = None
    if args.topic:
        weekly_topic = args.topic
        slug_map = {
            "exercises": "exercises",
            "funny": "funny",
            "history": "history",
            "information": "information",
            "interesting": "interesting",
            "nature": "nature",
            "news": "news",
            "sport": "sport"
        }
        category_slug = slug_map.get(weekly_topic.lower().strip())
        logger.info(f"Weekly topic overridden by command line argument: '{weekly_topic}' (slug: '{category_slug}')")
    else:
        topic_info = topic_rotation.get_current_topic()
        weekly_topic = topic_info["name"]
        category_slug = topic_info["slug"]
        
    # 2. Fetch RSS feed articles (from the specific category feed)
    all_articles = feeds.fetch_articles(category_slug=category_slug, max_items=args.limit)
    if not all_articles:
        logger.warning(f"No articles fetched from category '{category_slug}' RSS feed. Falling back to general feed.")
        all_articles = feeds.fetch_articles(category_slug=None, max_items=args.limit)
        
    if not all_articles:
        logger.error("No articles fetched from RSS feed. Pipeline execution aborted.")
        sys.exit(1)
        
    # 3. Filter out already sent URLs using deduplication
    sent_urls = dedup.load_sent_urls()
    candidates = [art for art in all_articles if art["url"] not in sent_urls]
    
    logger.info(f"Filtered {len(all_articles)} articles down to {len(candidates)} unsent candidates.")
    
    if not candidates:
        logger.warning("All fetched articles have already been sent in previous runs. Falling back to the latest 10 RSS articles to avoid skipping delivery.")
        candidates = all_articles[:10]
        
    # 4. Generate 3-level simplified article packages using Gemini
    curated_data = curator.curate_article(candidates, weekly_topic, mock=args.mock)
    if not curated_data:
        logger.error("Gemini curation returned no results. Pipeline execution aborted.")
        sys.exit(1)
        
    # 5. Format the message for Zalo
    formatted_msg = notifier.format_message(curated_data)
    
    # 6. Deliver the message
    delivery_success = notifier.send_zalo_message(formatted_msg, dry_run=args.dry_run)
    if not delivery_success:
        logger.error("Failed to send message via Zalo Bot API.")
        sys.exit(1)
        
    # 7. Update sent_urls.txt cache (only if actual delivery succeeded and not dry-run)
    if not args.dry_run:
        selected_url = curated_data.get("url")
        if selected_url:
            dedup.add_sent_url(selected_url)
            logger.info("Pipeline finished successfully. State updated.")
        else:
            logger.warning("Selected article is missing a URL. State file was not updated.")
    else:
        logger.info("Dry run completed. Console output generated, state file unchanged.")

if __name__ == "__main__":
    main()
