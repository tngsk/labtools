import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure the gummy directory is in the path so we can import the script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestWilliamsLatinSquare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_pd = MagicMock()
        cls.mock_np = MagicMock()
        cls.patcher_pd = patch.dict("sys.modules", {"pandas": cls.mock_pd})
        cls.patcher_np = patch.dict("sys.modules", {"numpy": cls.mock_np})
        cls.patcher_pd.start()
        cls.patcher_np.start()

        # Import after patching
        global wls
        import scripts.williams_latin_square as wls

    @classmethod
    def tearDownClass(cls):
        cls.patcher_pd.stop()
        cls.patcher_np.stop()

    def test_generate_williams_design(self):
        conditions = ["A", "B", "C", "D"]
        design = wls.generate_williams_design(conditions)
        self.assertEqual(len(design), 4)
        for row in design:
            self.assertEqual(len(row), 4)
            self.assertEqual(set(row), set(conditions))

    @patch("secrets.SystemRandom")
    def test_create_experiment_sheet(self, mock_sys_random):
        # Mock the shuffle to ensure it's called
        mock_shuffle = MagicMock()
        mock_sys_random.return_value.shuffle = mock_shuffle

        # Mock DataFrame behavior
        mock_df_instance = MagicMock()
        self.mock_pd.DataFrame.return_value = mock_df_instance
        mock_df_instance.__len__.return_value = 8

        conditions = ["A", "B", "C", "D"]
        n_participants = 8
        summary = wls.create_experiment_sheet(
            n_participants=n_participants, conditions=conditions, output_csv=False
        )

        self.assertEqual(len(summary), n_participants)
        mock_shuffle.assert_called()


if __name__ == "__main__":
    unittest.main()
