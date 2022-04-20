from typing import List

import pandas as pd


def find_continuous_intervals(
    intervals: pd.IntervalIndex, threshold=0
) -> List[pd.IntervalIndex]:
    """Splits a list of intervals into multiple lists of continuous intervals.

    Parameters
    ----------
    intervals : IntervalIndex
        A list of (possibly) non-continuous intervals.
    threshold : interval delta, default 0
        The threshold used to determine continuity.
        The threshold type should reflect the type of the intervals, e.g. int for int
        intervals and timedelta for datetime intervals.

    Returns
    -------
    List, of type IntervalIndex
        A list of continuous intervals.

    """
    intervals = pd.IntervalIndex(intervals).sort_values()

    if intervals.empty:
        return list()

    if "datetime" in str(intervals.dtype):
        threshold = pd.Timedelta(threshold)

    def generator():
        continuous = [intervals[0]]

        for interval, is_continuous in zip(
            intervals[1:],
            intervals.left[1:] - intervals.right[:-1] <= threshold,
        ):
            if is_continuous:
                continuous.append(interval)
            else:
                yield pd.IntervalIndex(continuous, dtype=intervals.dtype)
                continuous = [interval]

        yield pd.IntervalIndex(continuous, dtype=intervals.dtype)

    return list(generator())
