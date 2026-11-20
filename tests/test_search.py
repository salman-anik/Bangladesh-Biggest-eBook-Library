"""
Unit tests for search indexing and retrieval.
"""

import unittest
from src.index_generator import build_search_index, SearchEngine

class TestSearch(unittest.TestCase):
    def test_search_index_and_query(self):
        sample_catalog = [
            {
                "book_id": "BK000001",
                "title": "Machine Learning Yearning",
                "alt_title": "ML Yearning",
                "author": "Andrew Ng",
                "subject": "Computer and Technology",
                "subcategory": "Artificial Intelligence",
                "language": "English",
                "publication_year": 2018,
                "format": "PDF",
                "file_size_bytes": 1024000,
                "keywords": "Computer and Technology, Artificial Intelligence, English",
                "direct_drive_link": "https://drive.google.com/file/d/test123/view"
            },
            {
                "book_id": "BK000002",
                "title": "গীতাঞ্জলি",
                "alt_title": "Gitanjali",
                "author": "রবীন্দ্রনাথ ঠাকুর",
                "subject": "Literature",
                "subcategory": "Poetry",
                "language": "Bangla",
                "publication_year": 1910,
                "format": "PDF",
                "file_size_bytes": 2048000,
                "keywords": "Literature, Poetry, Bangla",
                "direct_drive_link": "https://drive.google.com/file/d/test456/view"
            }
        ]
        build_search_index(sample_catalog, base_dir=".", output_dir="data")
        engine = SearchEngine("data/search_index.json")
        
        # Test English query
        res_en = engine.search("Machine Learning")
        self.assertEqual(len(res_en), 1)
        self.assertEqual(res_en[0]["id"], "BK000001")
        
        # Test Bangla query
        res_bn = engine.search("গীতাঞ্জলি")
        self.assertEqual(len(res_bn), 1)
        self.assertEqual(res_bn[0]["id"], "BK000002")

if __name__ == "__main__":
    unittest.main()
