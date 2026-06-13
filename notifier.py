import os
import requests
import logging
import time
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def format_message(data: dict) -> list[str]:
    """Formats the curated 3-level article JSON into a list of structured text messages."""
    title = data.get("title", "Bài đọc hôm nay")
    url = data.get("url", "")
    topic = data.get("topic", "General")
    
    # Get current date in Vietnam time (GMT+7)
    vn_date = (datetime.utcnow() + timedelta(hours=7)).strftime("%d/%m/%Y")
    
    level_headers = {
        "Level 1": "━━━ 🟢 LEVEL 1 — Người mới bắt đầu ━━━",
        "Level 2": "━━━ 🟡 LEVEL 2 — Trung cấp ━━━",
        "Level 3": "━━━ 🔴 LEVEL 3 — Nâng cao ━━━"
    }
    
    messages = []
    
    levels = data.get("levels", [])
    for idx, lvl_data in enumerate(levels):
        level_name = lvl_data.get("level", "Level")
        level_num = level_name.split()[-1] # "1", "2", "3"
        header = level_headers.get(level_name, f"━━━ {level_name} ━━━")
        
        # Predict level-specific URL
        level_url = url
        if url:
            match = re.search(r'-level-\d/?$', url)
            if match:
                has_slash = url.endswith('/')
                suffix = f"-level-{level_num}/" if has_slash else f"-level-{level_num}"
                level_url = re.sub(r'-level-\d/?$', suffix, url)
                
        # Adapt title to the current level if it contains level info
        lvl_title = title
        lvl_title = re.sub(r'(?i)[-–]\s*level\s*\d', f"– level {level_num}", lvl_title)
        
        passage = lvl_data.get("passage", "")
        vocab_list = lvl_data.get("vocab_words", [])
        phrases_list = lvl_data.get("phrases", [])
        
        vocab_str = "  • ".join(vocab_list)
        if vocab_str:
            vocab_str = f"• {vocab_str}"
            
        phrases_str = "\n".join(f"{i}. \"{phrase}\"" for i, phrase in enumerate(phrases_list, start=1))
        
        # Build block header for this level
        block_header_parts = []
        if idx == 0:
            block_header_parts.extend([
                f"📚 BÀI ĐỌC TIẾNG ANH HÔM NAY - Ngày {vn_date}",
                f"🗂 Chủ đề: {topic}",
            ])
            
        block_header_parts.extend([
            f"🔗 {lvl_title} ({level_url})" if level_url else f"🔗 {lvl_title}",
            ""
        ])
        block_header_text = "\n".join(block_header_parts)
        
        lvl_parts = [
            block_header_text,
            header,
            "",
            "🔤 5 TỪ MỚI — tự tìm nghĩa nhé!",
            vocab_str,
            "",
            "💬 5 CỤM TỪ HAY — tự khám phá:",
            phrases_str,
            "",
            "📖 BÀI ĐỌC VÍ DỤ:",
            passage
        ]
        lvl_text = "\n".join(lvl_parts)
        messages.append(lvl_text)
            
    return messages

def send_zalo_message(messages: list[str] | str, dry_run: bool = False) -> bool:
    """Sends the formatted text messages to Zalo Bot API or prints to stdout in dry-run mode."""
    bot_token = os.environ.get("ZALO_BOT_TOKEN")
    chat_id = os.environ.get("ZALO_CHAT_ID")
    
    if isinstance(messages, str):
        msg_list = [messages]
    else:
        msg_list = messages
        
    if dry_run or not bot_token or not chat_id:
        logger.info("--- DRY RUN / CONSOLE OUTPUT ---")
        for i, text in enumerate(msg_list, start=1):
            if len(msg_list) > 1:
                print(f"[Message Chunk {i}/{len(msg_list)}]")
            print(text)
            print()
        logger.info("--------------------------------")
        
        if not dry_run and (not bot_token or not chat_id):
            logger.warning("ZALO_BOT_TOKEN or ZALO_CHAT_ID is missing. Defaulted to console print.")
        return True
        
    url = f"https://bot-api.zaloplatforms.com/bot{bot_token}/sendMessage"
    headers = {
        "Content-Type": "application/json"
    }
    
    for i, text in enumerate(msg_list, start=1):
        if len(text) > 2000:
            logger.warning(f"Message chunk {i} length ({len(text)}) exceeds 2000 characters. Truncating to avoid Zalo error.")
            text = text[:1990] + "..."
            
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        
        logger.info(f"Sending message chunk {i}/{len(msg_list)} to Zalo chat_id: {chat_id}...")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            res_json = response.json()
            logger.info(f"Zalo API response for chunk {i}: {res_json}")
            
            if not res_json.get("ok"):
                logger.error(f"Zalo API returned failure: {res_json}")
                return False
                
            if i < len(msg_list):
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to send Zalo message chunk {i}: {e}")
            return False
            
    logger.info("All message chunks sent successfully via Zalo Bot API.")
    return True
