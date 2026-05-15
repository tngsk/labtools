import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the directory containing the module to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

class TestFmtP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only mock if they are actually missing
        cls.mocks = {}
        for mod in ['numpy', 'pandas', 'pingouin', 'visualize', 'kaleido', 'plotly', 'plotly.express', 'plotly.graph_objects', 'plotly.subplots']:
            if mod not in sys.modules:
                mock = MagicMock()
                sys.modules[mod] = mock
                cls.mocks[mod] = mock

    @classmethod
    def tearDownClass(cls):
        for mod in cls.mocks:
            del sys.modules[mod]

    def setUp(self):
        # Reset mocks before each test
        for mock in self.mocks.values():
            mock.reset_mock(side_effect=True, return_value=True)

    def test_fmt_p_handles_nan(self):
        """Test that fmt_p returns the input when it is NaN."""
        from utils import fmt_p
        import pandas as pd

        nan_val = float('nan')
        pd.isna.return_value = True

        result = fmt_p(nan_val)

        pd.isna.assert_called_with(nan_val)
        self.assertTrue(pd.isna(result))
        # Since we use mocks, result will be a Mock if return_value is True,
        # but for NaN we returned the input.
        self.assertIs(result, nan_val)

    def test_fmt_p_formats_number(self):
        """Test that fmt_p formats a number correctly."""
        from utils import fmt_p
        import pandas as pd
        import numpy as np

        pd.isna.return_value = False
        np.format_float_positional.return_value = "formatted_string"

        input_val = 0.05
        result = fmt_p(input_val)

        np.format_float_positional.assert_called_once_with(
            input_val, precision=4, fractional=False, trim="-"
        )
        self.assertEqual(result, "formatted_string")

    def test_fmt_p_handles_none(self):
        """Test that fmt_p handles None."""
        from utils import fmt_p
        import pandas as pd

        pd.isna.return_value = True

        result = fmt_p(None)

        pd.isna.assert_called_with(None)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
