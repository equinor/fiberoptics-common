import functools
import os
from typing import Callable, List

import pandas as pd

__version__ = "0.0.1"


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

    right_sorted = intervals.sort_values(key=lambda x: getattr(x, "right", x))
    left_continuous = intervals.left[1:] - intervals.right[:-1] <= threshold
    right_continuous = right_sorted.left[1:] - right_sorted.right[:-1] <= threshold

    def generator():
        continuous = [intervals[0]]

        for interval, is_continuous in zip(
            intervals[1:], left_continuous | right_continuous
        ):
            if is_continuous:
                continuous.append(interval)
            else:
                yield pd.IntervalIndex(continuous, dtype=intervals.dtype)
                continuous = [interval]

        yield pd.IntervalIndex(continuous, dtype=intervals.dtype)

    return list(generator())


def combine_continuous_intervals(intervals: pd.IntervalIndex, threshold=0):
    """Combines continuous (or overlapping) intervals.

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
    IntervalIndex
        Containing non-overlapping intervals with a gap larger than `threshold`.
        The length of the returned index is smaller or equal to the input index.

    """

    def combine(item: pd.IntervalIndex):
        return pd.Interval(min(item.left), max(item.right), closed=item.closed)

    result = find_continuous_intervals(intervals, threshold)
    return pd.IntervalIndex(list(map(combine, result)))


def add_interval(self: pd.IntervalIndex, other: pd.Interval):
    """Add an interval to the existing intervals."""
    other = pd.IntervalIndex([other], dtype=self.dtype)
    return combine_continuous_intervals(self.append(other))


def subtract_interval(self: pd.IntervalIndex, other: pd.Interval):
    """Subtract an interval from the existing intervals."""

    def generator():
        for interval in self:
            if not interval.overlaps(other):
                yield interval
            else:
                if interval.left < other.left:
                    yield pd.Interval(interval.left, other.left)
                if other.right < interval.right:
                    yield pd.Interval(other.right, interval.right)

    return pd.IntervalIndex(list(generator()))


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


def cache_decorator(get_data_function: Callable):
    """Wraps a `get_data_function` with cache functionality.

    Should only be used when you expect to request the same or overlapping intervals.
    The decorator makes sure you only request the missing data. E.g. when requesting
    data for the period [3, 4) and then [2, 5), the last request is transformed into
    two requests, namely [2, 3) and [4, 5).

    """

    cached_intervals = dict()
    cached_data = dict()

    @functools.wraps(get_data_function)
    def wrapped_function(
        id: str, start_time: pd.Timestamp, end_time: pd.Timestamp, **kwargs
    ):
        start_time = pd.Timestamp(start_time)
        end_time = pd.Timestamp(end_time)
        missing_intervals = pd.IntervalIndex.from_tuples([(start_time, end_time)])

        if id not in cached_intervals:
            cached_intervals[id] = pd.IntervalIndex([], dtype=missing_intervals.dtype)
            cached_data[id] = pd.DataFrame()

        for interval in cached_intervals[id]:
            missing_intervals = subtract_interval(missing_intervals, interval)

        for interval in missing_intervals:
            df = get_data_function(id, interval.left, interval.right, **kwargs)
            cached_intervals[id] = add_interval(cached_intervals[id], interval)
            cached_data[id] = pd.concat([cached_data[id], df]).sort_index()

        return cached_data[id][start_time:end_time]

    return wrapped_function
