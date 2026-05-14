import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Mock heavy modules before importing the script
mock_pd = MagicMock()
mock_np = MagicMock()
sys.modules['pandas'] = mock_pd
sys.modules['numpy'] = mock_np

# Ensure the gummy directory is in the path so we can import the script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import scripts.williams_latin_square as wls

class TestWilliamsLatinSquare(unittest.TestCase):
    def test_generate_williams_design(self):
        conditions = ['A', 'B', 'C', 'D']
        design = wls.generate_williams_design(conditions)
        self.assertEqual(len(design), 4)
        for row in design:
            self.assertEqual(len(row), 4)
            self.assertEqual(set(row), set(conditions))

    @patch('secrets.SystemRandom')
    def test_create_experiment_sheet(self, mock_sys_random):
        # Mock the shuffle to ensure it's called
        mock_shuffle = MagicMock()
        mock_sys_random.return_value.shuffle = mock_shuffle

        # Mock DataFrame behavior
        mock_df_instance = MagicMock()
        mock_pd.DataFrame.return_value = mock_df_instance
        mock_df_instance.__len__.return_value = 8

        conditions = ['A', 'B', 'C', 'D']
        n_participants = 8
        summary = wls.create_experiment_sheet(
            n_participants=n_participants,
            conditions=conditions,
            output_csv=False
        )

        self.assertEqual(len(summary), n_participants)
        mock_shuffle.assert_called()

if __name__ == '__main__':
    unittest.main()
