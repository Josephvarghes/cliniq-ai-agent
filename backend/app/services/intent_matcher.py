import re
from typing import Tuple, Optional
from rapidfuzz import fuzz

INTENT_KEYWORDS = {
    "book_appointment": [
        "book", "schedule", "make an appointment", "need a doctor", "consultation",
        "see doctor", "appointment", "visit", "reserve", "book appointment", "new booking"
    ],
    "cancel_appointment": [
        "cancel", "cancel appointment", "cancel booking", "drop appointment", "call off",
        "stop appointment", "remove booking", "abort"
    ],
    "reschedule_appointment": [
        "reschedule", "change appointment", "move appointment", "postpone",
        "different date", "change time", "modify booking", "adjust appointment", "shift"
    ],
    "check_my_bookings": [
        "my bookings", "check bookings", "my appointments", "view bookings",
        "upcoming appointments", "list appointments", "status", "show bookings"
    ],
    "general_enquiry": [
        "talk to someone", "enquiry", "inquiry", "help", "question", "contact",
        "human", "receptionist", "speak with staff", "ask doctor"
    ]
}

def detect_intent(user_input: str, threshold: float = 65.0) -> Tuple[str, float]:
    """
    Detects intent from user free-text using exact keyword patterns and fuzzy ratio matching.
    Returns (intent_name, confidence_score). If confidence < threshold, returns ('fallback', score).
    """
    cleaned = user_input.lower().strip()
    if not cleaned:
        return "fallback", 0.0

    # 1. Regex / Substring checks (highest confidence)
    if re.search(r"\b(cancel|cancellation|drop)\b", cleaned):
        return "cancel_appointment", 100.0
    if re.search(r"\b(reschedule|postpone|change (date|time|slot)|move)\b", cleaned):
        return "reschedule_appointment", 100.0
    if re.search(r"\b(my booking|my appointment|check booking|show booking)\b", cleaned):
        return "check_my_bookings", 100.0
    if re.search(r"\b(book|reserve|schedule|consult)\b", cleaned):
        return "book_appointment", 100.0
    if re.search(r"\b(talk|enquir|help|human|support|contact|reception)\b", cleaned):
        return "general_enquiry", 100.0

    # 2. Fuzzy token-set matching across intent keyword lists
    best_intent = "fallback"
    best_score = 0.0

    for intent, phrases in INTENT_KEYWORDS.items():
        for phrase in phrases:
            # Token set ratio handles word reordering and partial sentences
            score = fuzz.token_set_ratio(cleaned, phrase)
            if score > best_score:
                best_score = score
                best_intent = intent

    if best_score >= threshold:
        return best_intent, best_score

    return "fallback", best_score
