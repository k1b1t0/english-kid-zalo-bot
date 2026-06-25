import argparse
import sys
import os
import logging
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add project root to sys.path to allow importing from shared
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from shared.zalo import send_zalo_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("workout_bot")

# Hardcoded data from plan-workout.md
WEEKLY_PLAN = {
    6: {"type": "strength", "session": "A"},   # CN
    0: {"type": "other",    "session": "Mobility + Đi bộ sau ăn"},  # T2
    1: {"type": "strength", "session": "B"},   # T3
    2: {"type": "other",    "session": "Zone 2 (30-45 phút đi bộ nhanh / bơi / đạp xe)"},  # T4
    3: {"type": "strength", "session": "C"},   # T5
    4: {"type": "other",    "session": "Norwegian 4x4"},  # T6
    5: {"type": "other",    "session": "Đá bóng nhẹ / Active Recovery"},  # T7
}

STRENGTH_SESSIONS = {
    "A": [
        "Pull-up × 3",
        "Pike Push-up × 3",
        "Bulgarian Squat × 3",
        "Hanging Knee Raise × 3",
        "Hollow Hold × 3",
    ],
    "B": [
        "Pull-up × 3",
        "Feet Elevated Push-up × 3",
        "Pistol Squat (support) × 3",
        "Single Leg Glute Bridge × 3",
        "Hollow Hold × 3",
    ],
    "C": [
        "Pull-up / Row × 3",
        "Push-up × 3",
        "Bulgarian Squat × 3",
        "Single Leg Calf Raise × 3",
        "Hanging Knee Raise × 3",
    ],
}

WARMUP = ["Cat Cow", "World's Greatest Stretch", "Deep Squat Hold", "Arm Circles / Shoulder Rolls", "Scapular Pull-up"]
COOLDOWN = ["Child's Pose", "Downward Dog", "Hip Flexor Stretch", "Thoracic Rotation", "Breathing"]

DAILY = {
    "morning":    ["Cat Cow", "Child's Pose", "World's Greatest Stretch", "Wall Angel"],
    "evening":    ["Downward Dog", "Thoracic Rotation", "Deep Squat Hold"],
    "after_meal": ["Đi bộ 10 phút sau bữa trưa", "Đi bộ 10 phút sau bữa tối"],
    "work_break": ["Chin Tuck", "Shoulder Rolls", "Torso Twists", "Hip Flexor Stretch", "Wrist Stretch", "Single Leg Stand"],
}

GOALS = [
    "Pull-up: 2 → 8+",
    "Hollow Hold: 30s → 60s",
    "Giảm vòng bụng đều",
    "Hoàn thành ≥ 80% số buổi tập",
]

TRACKING_URL = "https://docs.google.com/spreadsheets/d/1F-Xtgi105P8qNpkaVMAwnhNNEP7qVscW0R6Fh1CI6mo/edit?usp=sharing"

WEEKDAY_NAMES = {
    0: "Thứ 2",
    1: "Thứ 3",
    2: "Thứ 4",
    3: "Thứ 5",
    4: "Thứ 6",
    5: "Thứ 7",
    6: "Chủ Nhật"
}

def generate_motivation_quote(mock: bool = False) -> str:
    """Generates a random motivational quote from quotes.txt."""
    if mock:
        logger.info("Using mock motivation quote.")
        return "\"Không cần hoàn hảo, chỉ cần không bỏ.\""
    quotes_path = os.path.join(os.path.dirname(__file__), "quotes.txt")
    if not os.path.exists(quotes_path):
        logger.warning(f"Quotes file not found at {quotes_path}. Using fallback.")
        return "\"Không cần hoàn hảo, chỉ cần không bỏ.\""
    try:
        with open(quotes_path, "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f if line.strip()]
        if not quotes:
            return "\"Không cần hoàn hảo, chỉ cần không bỏ.\""
        return random.choice(quotes)
    except Exception as e:
        logger.error(f"Error reading quotes file: {e}")
        return "\"Không cần hoàn hảo, chỉ cần không bỏ.\""

def build_workout_message(weekday: int, date_str: str, quote: str) -> str:
    """Builds the workout reminder message text with quote at the top."""
    header = f"🌅 5:00 SA — {WEEKDAY_NAMES[weekday]}, {date_str}"
    
    # 1. Workout Session
    plan = WEEKLY_PLAN.get(weekday)
    if not plan:
        workout_section = "💪 Hôm nay: Nghỉ ngơi"
    elif plan["type"] == "strength":
        session_name = plan["session"]
        exercises = STRENGTH_SESSIONS.get(session_name, [])
        warmup_str = " · ".join(WARMUP)
        cooldown_str = " · ".join(COOLDOWN)
        
        workout_lines = [
            f"💪 Hôm nay: Strength {session_name}",
            f"• Warm-up: {warmup_str}"
        ]
        for ex in exercises:
            workout_lines.append(f"• {ex}")
        workout_lines.append(f"• Cooldown: {cooldown_str}")
        workout_section = "\n".join(workout_lines)
    else:
        # type is 'other' or something else
        session_name = plan["session"]
        workout_section = f"💪 Hôm nay: {session_name}"
        
    # 2. Daily Routines
    daily_parts = []
    if DAILY.get("morning"):
        daily_parts.append(f"Sáng: {' · '.join(DAILY['morning'])}")
    if DAILY.get("after_meal"):
        # We can format it either by listing them or compacting
        daily_parts.append(f"Sau ăn: {' · '.join(DAILY['after_meal'])}")
    if DAILY.get("work_break"):
        daily_parts.append(f"Nghỉ giờ: {' · '.join(DAILY['work_break'])}")
    if DAILY.get("evening"):
        daily_parts.append(f"Tối: {' · '.join(DAILY['evening'])}")
        
    daily_section = "🌿 Daily hôm nay:\n" + "\n".join(daily_parts)
    
    # 3. Tracking Section
    tracking_section = f"📊 Tracking: {TRACKING_URL}"
    
    # Combine all parts (putting quote at the top)
    message = f"{header}\n\n✨ {quote}\n\n{workout_section}\n\n{daily_section}\n\n{tracking_section}"
    return message

def main():
    # Load .env file for local testing
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Daily Workout Reminder Bot via Zalo")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Print the formatted message to console without calling Zalo API"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock quote response instead of calling live Gemini API (useful for testing without keys)"
    )
    parser.add_argument(
        "--day", 
        type=int, 
        choices=range(7),
        help="Manually override the weekday (0=Monday, 6=Sunday) for testing"
    )
    parser.add_argument(
        "--date", 
        type=str, 
        help="Manually override the date string (e.g. '17/06') for testing"
    )
    args = parser.parse_args()
    
    logger.info("Starting Daily Workout Bot pipeline...")
    
    # Get current Vietnam time
    vn_now = datetime.now(timezone(timedelta(hours=7)))
    
    # Apply overrides if provided
    weekday = args.day if args.day is not None else vn_now.weekday()
    date_str = args.date if args.date is not None else vn_now.strftime("%d/%m")
    
    logger.info(f"Target day: {WEEKDAY_NAMES[weekday]} (index: {weekday}), date: {date_str}")
    
    # 1. Generate motivation quote
    quote = generate_motivation_quote(mock=args.mock)
    
    # 2. Build the message
    message = build_workout_message(weekday, date_str, quote)
    
    # 3. Send Zalo message
    success = send_zalo_message(message, dry_run=args.dry_run)
    if not success:
        logger.error("Failed to send message via Zalo Bot API.")
        sys.exit(1)
        
    logger.info("Workout Bot pipeline completed successfully.")

if __name__ == "__main__":
    main()
