import numpy as np
import pandas as pd

def fmt_p(x):
    """
    Format a p-value for display.

    If the input is NaN, returns it as is.
    Otherwise, formats it using numpy's format_float_positional.
    """
    if pd.isna(x):
        return x
    return np.format_float_positional(x, precision=4, fractional=False, trim="-")
