import unittest
from unittest.mock import patch
import sys
import os

# Ensure the templates directory is reachable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the template file directly.
# We need to use importlib since the filename starts with a number.
import importlib.util

spec = importlib.util.spec_from_file_location(
    "williams_design_template",
    os.path.join(os.path.dirname(__file__), "..", "templates", "02_williams_design.py"),
)
williams_template = importlib.util.module_from_spec(spec)
sys.modules["williams_design_template"] = williams_template
spec.loader.exec_module(williams_template)


class TestWilliamsDesignTemplate(unittest.TestCase):
    @patch("pandas.DataFrame.to_csv")
    def test_create_experiment_sheet_path_traversal(self, mock_to_csv):
        # Malicious filename prefix to test path traversal
        malicious_prefix = "../../../etc/passwd"

        # Call the function with output_csv=True to trigger file saving
        williams_template.create_experiment_sheet(
            n_participants=4,
            conditions=["A", "B"],
            output_csv=True,
            filename_prefix=malicious_prefix,
        )

        # Ensure to_csv was called
        mock_to_csv.assert_called_once()

        # Get the filename passed to to_csv
        called_args, called_kwargs = mock_to_csv.call_args
        actual_fname = called_args[0]

        # Verify the path traversal was mitigated
        self.assertNotIn("../", actual_fname)
        self.assertNotIn("/", actual_fname)
        self.assertTrue(actual_fname.startswith("passwd_"))


if __name__ == "__main__":
    unittest.main()
