import unittest
import sys
import os

# Add the directory containing the module to sys.path so utils can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestFmtP(unittest.TestCase):
    def test_fmt_p_handles_nan(self):
        """Test that fmt_p handles np.nan and pd.NA properly by returning them."""
        from utils import fmt_p
        import pandas as pd
        import numpy as np
        import math

        nan_val = float('nan')
        result = fmt_p(nan_val)
        self.assertTrue(math.isnan(result))

        na_val = pd.NA
        result_na = fmt_p(na_val)
        self.assertTrue(pd.isna(result_na))

        np_nan_val = np.nan
        result_np_nan = fmt_p(np_nan_val)
        self.assertTrue(np.isnan(result_np_nan))

    def test_fmt_p_formats_number(self):
        """Test that fmt_p formats a number correctly."""
        from utils import fmt_p

        # Test various decimal values to ensure they match precision=4, fractional=False, trim="-"
        self.assertEqual(fmt_p(0.05), "0.05")
        self.assertEqual(fmt_p(0.12345), "0.1235")
        self.assertEqual(fmt_p(1.0), "1")
        self.assertEqual(fmt_p(0.00012), "0.00012")
        self.assertEqual(fmt_p(0.0), "0")
        self.assertEqual(fmt_p(0), "0")

    def test_fmt_p_handles_none(self):
        """Test that fmt_p handles None correctly."""
        from utils import fmt_p

        result = fmt_p(None)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
