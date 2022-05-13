import os

from .interval import (
    add_interval,
    combine_continuous_intervals,
    find_continuous_intervals,
    subtract_interval,
    with_interval_cache,
)

__version__ = "0.1.0"


def get_filepaths(folder):
    """Retrieves a list of all filepaths in the given folder and its subfolders.

    Parameters
    ----------
    folder : str
        Path to a given folder.

    list, of type str
        Containing paths to all files in the given folder.

    """
    return [os.path.join(dp, f) for dp, ds, fs in os.walk(folder) for f in fs]
