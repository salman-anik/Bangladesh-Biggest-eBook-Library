"""
Subject Classifier for Bangladesh eBook Library.
Enforces the 23 standard taxonomy categories and handles subcategories.
"""

from typing import Tuple

TAXONOMY_CATEGORIES = [
    "Agriculture and Nature",
    "Arts and Culture",
    "Biography and Autobiography",
    "Business and Finance",
    "Children and Young Adult",
    "Computer and Technology",
    "Education and Academics",
    "Engineering",
    "Fiction",
    "History",
    "Language and Linguistics",
    "Law and Legal",
    "Literature",
    "Magazines and Periodicals",
    "Medicine and Health",
    "Philosophy",
    "Politics and Government",
    "Reference Books",
    "Religion",
    "Science",
    "Self Development",
    "Social Science",
    "Travel and Geography"
]

CATEGORY_ALIASES = {
    "agriculture": "Agriculture and Nature",
    "nature": "Agriculture and Nature",
    "farming": "Agriculture and Nature",
    "fisheries": "Agriculture and Nature",
    "arts": "Arts and Culture",
    "culture": "Arts and Culture",
    "music": "Arts and Culture",
    "cinema": "Arts and Culture",
    "biography": "Biography and Autobiography",
    "autobiography": "Biography and Autobiography",
    "memoir": "Biography and Autobiography",
    "business": "Business and Finance",
    "finance": "Business and Finance",
    "economics": "Business and Finance",
    "banking": "Business and Finance",
    "children": "Children and Young Adult",
    "comics": "Children and Young Adult",
    "juvenile": "Children and Young Adult",
    "computer": "Computer and Technology",
    "technology": "Computer and Technology",
    "programming": "Computer and Technology",
    "software": "Computer and Technology",
    "education": "Education and Academics",
    "academics": "Education and Academics",
    "textbook": "Education and Academics",
    "nctb": "Education and Academics",
    "engineering": "Engineering",
    "civil": "Engineering",
    "electrical": "Engineering",
    "mechanical": "Engineering",
    "fiction": "Fiction",
    "novel": "Fiction",
    "detective": "Fiction",
    "thriller": "Fiction",
    "history": "History",
    "liberation war": "History",
    "muktijuddho": "History",
    "linguistics": "Language and Linguistics",
    "language": "Language and Linguistics",
    "grammar": "Language and Linguistics",
    "dictionary": "Reference Books",
    "encyclopedia": "Reference Books",
    "law": "Law and Legal",
    "legal": "Law and Legal",
    "constitution": "Law and Legal",
    "literature": "Literature",
    "poetry": "Literature",
    "drama": "Literature",
    "kobita": "Literature",
    "magazines": "Magazines and Periodicals",
    "periodicals": "Magazines and Periodicals",
    "journal": "Magazines and Periodicals",
    "medicine": "Medicine and Health",
    "health": "Medicine and Health",
    "medical": "Medicine and Health",
    "anatomy": "Medicine and Health",
    "philosophy": "Philosophy",
    "politics": "Politics and Government",
    "government": "Politics and Government",
    "reference": "Reference Books",
    "religion": "Religion",
    "islam": "Religion",
    "quran": "Religion",
    "hadith": "Religion",
    "hinduism": "Religion",
    "science": "Science",
    "physics": "Science",
    "chemistry": "Science",
    "biology": "Science",
    "mathematics": "Science",
    "self development": "Self Development",
    "motivation": "Self Development",
    "social science": "Social Science",
    "sociology": "Social Science",
    "anthropology": "Social Science",
    "travel": "Travel and Geography",
    "geography": "Travel and Geography"
}

def classify_book(top_cat: str, leaf_cat: str, leaf_path: str, title: str) -> Tuple[str, str]:
    """
    Returns (normalized_subject, subcategory).
    Ensures primary subject is one of the 23 standard taxonomy categories.
    """
    # 1. Exact match in taxonomy categories
    if top_cat in TAXONOMY_CATEGORIES:
        primary = top_cat
    else:
        # Check alias
        top_lower = top_cat.lower().strip()
        primary = CATEGORY_ALIASES.get(top_lower, None)
        if not primary:
            # Check path tokens
            path_lower = leaf_path.lower()
            for key, val in CATEGORY_ALIASES.items():
                if key in path_lower:
                    primary = val
                    break
        if not primary:
            primary = "Reference Books"
    
    subcat = leaf_cat.strip() if leaf_cat and leaf_cat.strip() else "General"
    if subcat == primary or subcat == "":
        subcat = "General"
        
    return primary, subcat
