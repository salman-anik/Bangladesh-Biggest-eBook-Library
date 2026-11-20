"""
Unit tests for Drive link generation and integrity.
"""

import unittest

class TestDriveLinks(unittest.TestCase):
    def test_drive_url_format(self):
        file_id = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
        url = f"https://drive.google.com/file/d/{file_id}/view"
        self.assertTrue(url.startswith("https://drive.google.com/file/d/"))
        self.assertTrue(url.endswith("/view"))
        self.assertIn(file_id, url)

if __name__ == "__main__":
    unittest.main()
