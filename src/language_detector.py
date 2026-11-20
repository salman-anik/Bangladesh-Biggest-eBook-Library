"""
Language Detector for Bangladesh eBook Library.
Supports detection of Bangla, English, Arabic, and other languages.
Distinguishes between Bangla script, Arabic script, and romanized text.
"""

import re
from typing import Tuple

# Unicode regex ranges
BANGLA_REGEX = re.compile(r'[\u0980-\u09FF]')
ARABIC_REGEX = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')

# Common romanized Bangla tokens
ROMANIZED_BANGLA_TOKENS = {
    "amar", "amarer", "bangla", "boi", "boier", "chhelebela", "diner", "ekhon",
    "golpo", "gaan", "ganer", "ghor", "jibon", "jiboni", "kabita", "kobita",
    "khondo", "kichhu", "manush", "mukto", "natok", "nobel", "porbo", "prothom",
    "dwitij", "tritij", "rachanabali", "rachanavali", "shomogro", "somogro", "upanyas",
    "krishi", "shikkhok", "sahitya", "shobdo", "itihas", "desh", "desher", "dhormo"
}

def detect_language(text: str, leaf_path: str = "") -> Tuple[str, float]:
    """
    Detects language based on text content and metadata folder path.
    Returns (language_name, confidence_score).
    """
    if not text:
        text = ""
    
    # Priority 1: Arabic script or Arabic Language folder
    if ARABIC_REGEX.search(text) or "Arabic Language" in leaf_path or "/Arabic" in leaf_path:
        return "Arabic", 0.95
    
    # Priority 2: Native Bangla script
    bangla_chars = len(BANGLA_REGEX.findall(text))
    if bangla_chars >= 2:
        confidence = min(0.99, 0.70 + (bangla_chars / max(len(text), 1)) * 0.3)
        return "Bangla", round(confidence, 2)
    
    # Priority 3: Check leaf path hints
    if "/Bangla" in leaf_path or "Bangla Literature" in leaf_path or "Bangla Language" in leaf_path:
        return "Bangla", 0.90
    
    # Priority 4: Romanized Bangla detection in words
    words = set(re.findall(r'[a-zA-Z]{3,}', text.lower()))
    romanized_matches = words.intersection(ROMANIZED_BANGLA_TOKENS)
    if len(romanized_matches) >= 2 or (len(romanized_matches) >= 1 and ("Literature" in leaf_path or "Fiction" in leaf_path)):
        return "Bangla", 0.85
    
    # Priority 5: English text
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    if latin_chars >= 3:
        return "English", 0.90
    
    return "Unknown", 0.50
