import unittest
import sys
import os

# Adjust path to find app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.preflight_check import PreflightChecker

class TestPreflight(unittest.TestCase):
    def test_check_os(self):
        res = PreflightChecker.check_os()
        self.assertIn("status", res)
        self.assertIn("name", res)
        # Check output contains Windows or Unsupported
        self.assertTrue(res["status"] in ["green", "yellow"])

    def test_check_python(self):
        res = PreflightChecker.check_python()
        self.assertEqual(res["status"], "green") # assuming test environment is >= 3.8

    def test_check_disk(self):
        res = PreflightChecker.check_disk_space()
        self.assertIn(res["status"], ["green", "yellow", "red"])
        self.assertIsNotNone(res["desc"])

if __name__ == '__main__':
    unittest.main()
