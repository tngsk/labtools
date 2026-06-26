import unittest
from unittest.mock import patch
import runpy
import os
import pingouin  # Pre-import to prevent pandas.read_csv side effect during test

class TestRmAnova(unittest.TestCase):
    @patch('pandas.read_csv', side_effect=FileNotFoundError)
    def test_file_not_found_raises_systemexit(self, mock_read_csv):
        script_path = os.path.join(os.path.dirname(__file__), "..", "rm_anova.py")
        with self.assertRaises(SystemExit) as cm:
            runpy.run_path(script_path, run_name="__main__")
        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()
