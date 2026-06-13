import os
import json
import time
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class LevelContent(BaseModel):
    level: Literal["Level 1", "Level 2", "Level 3"]
    vocab_words: List[str] = Field(description="Exactly 5 interesting or challenging words from that level's passage. Bare words only - no definitions, translations or phonetics.")
    phrases: List[str] = Field(description="Exactly 5 useful expressions, collocations or phrases from that level's passage (mix of noun, verb, adjective phrases, etc.). Bare phrases only - no translations or explanations.")
    passage: str = Field(description="A short, engaging reading passage (60-120 words) that rewrites the selected news article at this level, naturally incorporating all 5 vocab_words and 5 phrases.")

class CuratedArticle(BaseModel):
    title: str = Field(description="The title of the selected article.")
    url: str = Field(description="The URL of the selected article.")
    topic: str = Field(description="The topic name for the current week.")
    levels: List[LevelContent] = Field(description="The three levels of the content.", min_length=3, max_length=3)

def curate_article(candidates: list[dict], weekly_topic: str, mock: bool = False) -> Optional[dict]:
    """Sends candidate articles and the weekly topic to Gemini to select and rewrite one article into 3 levels."""
    if mock:
        logger.info("Using mock curation mode.")
        selected = candidates[0] if candidates else {"title": "A Smart Crow", "url": "https://www.newsinlevels.com/smart-crow"}
        return {
            "title": selected.get("title", "A Smart Crow"),
            "url": selected.get("url", "https://www.newsinlevels.com/smart-crow"),
            "topic": weekly_topic,
            "levels": [
                {
                    "level": "Level 1",
                    "vocab_words": ["thirsty", "pitcher", "reach", "drops", "rises"],
                    "phrases": ["a thirsty crow", "very little water", "cannot reach it", "drops small stones", "water level rises"],
                    "passage": "A thirsty crow finds a pitcher with very little water. He cannot reach it. He drops small stones into the pitcher. The water level rises, and he drinks."
                },
                {
                    "level": "Level 2",
                    "vocab_words": ["scorching", "discovered", "narrow", "pebbles", "satisfy"],
                    "phrases": ["scorching summer day", "discovered a deep pitcher", "small amount of water", "too narrow", "unable to reach it"],
                    "passage": "On a scorching summer day, a thirsty crow discovered a deep pitcher containing a small amount of water. Because the neck was too narrow, he was unable to reach it. He decided to drop pebbles into the pitcher to raise the water level. Gradually, the water rose, allowing him to satisfy his thirst."
                },
                {
                    "level": "Level 3",
                    "vocab_words": ["blistering", "dehydrated", "meager", "ingeniously", "quench"],
                    "phrases": ["blistering heatwave", "dehydrated crow", "came across a pitcher", "meager quantity of water", "physically impossible"],
                    "passage": "Amidst a blistering heatwave, a dehydrated crow came across a pitcher filled with a meager quantity of water. Due to the pitcher's narrow neck, reaching the liquid was physically impossible. Ingeniously, he began collecting small pebbles and dropping them into the vessel. Eventually, the water level rose to the brim, and the clever crow was able to quench his thirst."
                }
            ]
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment variables.")
        return None
        
    if not candidates:
        logger.warning("No candidate articles available for curation.")
        return None
        
    # Format candidate articles for prompt
    articles_text = ""
    for idx, art in enumerate(candidates, start=1):
        articles_text += f"[{idx}] Title: {art['title']}\nURL: {art['url']}\nSummary: {art['summary']}\n\n"
        
    system_prompt = f"""You are a friendly English learning assistant for Vietnamese children aged 8-14.

This week's topic: {weekly_topic}

Given the list of articles below, select ONE article that:
1. Best matches this week's topic. If no article matches well, pick the most interesting one for kids (fallback).
2. Is age-appropriate — no violence, politics, or adult content.
3. Is short and engaging for children.

For the selected article, generate content at ALL THREE levels (Level 1, Level 2, Level 3). The levels must share the same article title and URL.

For each level:
- vocab_words: Exactly 5 interesting or challenging words from the article at this level.
  List ONLY the bare words — no definitions, no phonetics, no translations, no examples.
- phrases: Exactly 5 useful expressions, collocations, or phrases from the article at this level (a mix of verb phrases, noun phrases, adjectives, etc., to help kids learn word combinations).
  List ONLY the phrases — no explanation, no translation.
- passage: A short, engaging reading passage (60-120 words) that rewrites the selected news article at this level, naturally incorporating all 5 vocab_words and all 5 phrases.
  - Level 1: Very simple sentences, common words only. For young beginners.
  - Level 2: Slightly more complex sentences, some new vocabulary. For intermediate learners.
  - Level 3: Close to original news style. For advanced young readers.

CRITICAL RULES:
- DO NOT explain any word or phrase. No definitions. No translations. No phonetics.
- The passage must read naturally as a news rewrite while embedding the selected vocabulary words and phrases.
- Keep all three levels clearly distinct in complexity.

Candidate Articles:
{articles_text}
"""

    logger.info(f"Invoking Gemini Model '{model_name}' to curate article...")
    
    # Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=system_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CuratedArticle,
                    temperature=0.7,
                )
            )
            
            if not response.text:
                raise ValueError("Empty response text from Gemini API")
                
            # Parse & validate response
            result_json = json.loads(response.text)
            # Basic validation of schema structure
            if "title" in result_json and "url" in result_json and "levels" in result_json:
                logger.info(f"Gemini curation successful! Selected article: '{result_json['title']}'")
                return result_json
            else:
                raise ValueError("Invalid structure in Gemini response JSON")
                
        except Exception as e:
            wait_time = 2 ** attempt
            logger.warning(f"Attempt {attempt + 1} failed with error: {e}. Retrying in {wait_time}s...")
            if attempt == max_attempts - 1:
                logger.error("All Gemini API attempts failed.")
                return None
            time.sleep(wait_time)
            
    return None
