"""
Unit tests for duplicate detection.
"""

import unittest
from src.duplicate_detector import detect_duplicates

class TestDuplicates(unittest.TestCase):
    def test_exact_duplicate_detection(self):
        sample_catalog = [
            {
                "book_id": "BK000001",
                "title": "Introduction to Algorithms",
                "author": "Cormen",
                "file_size_bytes": 5000000,
                "drive_file_id": "FID_001",
                "direct_drive_link": "https://drive.google.com/file/d/FID_001/view",
                "original_folder": "Computer and Technology",
                "duplicate_status": "Unique"
            },
            {
                "book_id": "BK000002",
                "title": "Introduction to Algorithms (Copy)",
                "author": "Cormen",
                "file_size_bytes": 5000000,
                "drive_file_id": "FID_002",
                "direct_drive_link": "https://drive.google.com/file/d/FID_002/view",
                "original_folder": "Computer and Technology/Algorithms",
                "duplicate_status": "Unique"
            }
        ]
        dups = detect_duplicates(sample_catalog, base_dir=".")
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["match_type"], "Exact Duplicate")
        self.assertEqual(sample_catalog[1]["duplicate_status"], "Duplicate Candidate")

if __name__ == "__main__":
    unittest.main()
