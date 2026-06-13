import os
import logging

logger = logging.getLogger(__name__)

def load_sent_urls(filepath: str = "sent_urls.txt") -> set[str]:
    """Loads previously sent URLs from the state file."""
    if not os.path.exists(filepath):
        logger.info(f"State file {filepath} not found. Creating a new one.")
        return set()
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            urls = {line.strip() for line in f if line.strip()}
        logger.info(f"Loaded {len(urls)} URLs from state file.")
        return urls
    except Exception as e:
        logger.error(f"Failed to read state file {filepath}: {e}")
        return set()

def add_sent_url(url: str, filepath: str = "sent_urls.txt", max_limit: int = 300) -> None:
    """Appends a new URL to the state file and maintains the max limit."""
    if not url:
        return
        
    try:
        # Load existing URLs in order of appearance
        ordered_urls = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                ordered_urls = [line.strip() for line in f if line.strip()]
        
        # Append new URL if it isn't already in the list
        if url not in ordered_urls:
            ordered_urls.append(url)
            
        # Trim list to last max_limit entries
        if len(ordered_urls) > max_limit:
            ordered_urls = ordered_urls[-max_limit:]
            
        # Write back to file
        with open(filepath, "w", encoding="utf-8") as f:
            for item in ordered_urls:
                f.write(f"{item}\n")
                
        logger.info(f"Updated state file {filepath} with '{url}'. Total entries: {len(ordered_urls)}.")
    except Exception as e:
        logger.error(f"Failed to write state file {filepath}: {e}")
