"""
Index Generator and Search Engine for Bangladesh eBook Library.
Generates search_index.json and provides high-speed multilingual querying.
"""

import os
import re
import json
import unicodedata
from collections import defaultdict
from typing import Dict, Any, List

def normalize_text(text: str) -> str:
    """Normalizes Unicode text and whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    return " ".join(text.lower().split())

def tokenize(text: str) -> List[str]:
    """Tokenizes text into search keywords."""
    norm = normalize_text(text)
    # Split on whitespace and non-alphanumeric (while preserving Bangla/Arabic chars)
    tokens = re.findall(r'[\u0980-\u09FF\u0600-\u06FF\w]{2,}', norm)
    return tokens

def build_search_index(catalog: List[Dict[str, Any]], base_dir: str, output_dir: str = "data") -> Dict[str, Any]:
    """
    Builds an inverted index for title, author, subject, language, keywords.
    """
    index = {
        "metadata": {
            "total_books": len(catalog),
            "generated_at": "2026-11-20T12:00:00Z"
        },
        "books": {},
        "tokens": defaultdict(list),
        "subjects": defaultdict(list),
        "languages": defaultdict(list),
        "authors": defaultdict(list),
        "years": defaultdict(list)
    }
    
    for b in catalog:
        bid = b["book_id"]
        # Compact book summary for search results
        compact_entry = {
            "id": bid,
            "title": b["title"],
            "author": b["author"],
            "subject": b["subject"],
            "subcategory": b["subcategory"],
            "language": b["language"],
            "year": b["publication_year"],
            "format": b["format"],
            "size": b["file_size_bytes"],
            "drive_link": b["direct_drive_link"]
        }
        index["books"][bid] = compact_entry
        
        # Facets
        index["subjects"][b["subject"]].append(bid)
        index["languages"][b["language"]].append(bid)
        if b["author"] and b["author"] != "Various / Unknown":
            index["authors"][b["author"]].append(bid)
        if b["publication_year"] != "Unknown":
            index["years"][str(b["publication_year"])].append(bid)
            
        # Text tokens from title, author, subject, keywords
        search_blob = f"{b['title']} {b.get('alt_title', '')} {b['author']} {b['subject']} {b['subcategory']} {b['keywords']}"
        tokens = set(tokenize(search_blob))
        for token in tokens:
            index["tokens"][token].append(bid)
            
    # Convert token dict to regular dict
    index["tokens"] = dict(index["tokens"])
    index["subjects"] = dict(index["subjects"])
    index["languages"] = dict(index["languages"])
    index["authors"] = dict(index["authors"])
    index["years"] = dict(index["years"])
    
    os.makedirs(os.path.join(base_dir, output_dir), exist_ok=True)
    out_path = os.path.join(base_dir, output_dir, "search_index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
        
    return index

class SearchEngine:
    def __init__(self, index_path: str):
        with open(index_path, "r", encoding="utf-8") as f:
            self.index = json.load(f)
            
    def search(self, query: str, subject: str = None, language: str = None, year: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        candidates = set()
        
        if query_tokens:
            for token in query_tokens:
                # Exact token match
                if token in self.index["tokens"]:
                    candidates.update(self.index["tokens"][token])
                # Prefix match
                for idx_token, b_ids in self.index["tokens"].items():
                    if idx_token.startswith(token) or token in idx_token:
                        candidates.update(b_ids)
        else:
            candidates = set(self.index["books"].keys())
            
        results = []
        for bid in candidates:
            b = self.index["books"][bid]
            if subject and b["subject"].lower() != subject.lower():
                continue
            if language and b["language"].lower() != language.lower():
                continue
            if year and str(b["year"]) != str(year):
                continue
            results.append(b)
            if len(results) >= limit:
                break
                
        return results
