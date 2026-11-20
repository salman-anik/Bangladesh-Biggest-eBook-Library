"""
Unit tests for metadata extraction and normalization.
"""

import unittest
from src.language_detector import detect_language
from src.subject_classifier import classify_book

class TestMetadata(unittest.TestCase):
    def test_bangla_language_detection(self):
        lang, conf = detect_language("গীতাঞ্জলি - রবীন্দ্রনাথ ঠাকুর")
        self.assertEqual(lang, "Bangla")
        self.assertGreater(conf, 0.7)

    def test_english_language_detection(self):
        lang, conf = detect_language("Python Data Science Handbook", "Computer and Technology")
        self.assertEqual(lang, "English")
        self.assertGreater(conf, 0.8)

    def test_arabic_language_detection(self):
        lang, conf = detect_language("تفسير ابن كثير", "Religion/Islam")
        self.assertEqual(lang, "Arabic")
        self.assertGreater(conf, 0.9)

    def test_subject_classification(self):
        subject, subcat = classify_book("Computer and Technology", "Artificial Intelligence", "Computer and Technology/AI", "Deep Learning")
        self.assertEqual(subject, "Computer and Technology")
        self.assertEqual(subcat, "Artificial Intelligence")

    def test_fallback_subject_classification(self):
        subject, subcat = classify_book("UnknownCategory", "Textbooks", "Education/School", "Math Class 10")
        self.assertEqual(subject, "Education and Academics")

if __name__ == "__main__":
    unittest.main()
