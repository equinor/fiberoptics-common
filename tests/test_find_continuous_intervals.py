import pandas as pd

from fiberoptics.common import find_continuous_intervals


def test_empty_intervals():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([])

    # Act
    result = find_continuous_intervals(intervals)

    # Assert
    assert result == []


def test_single_intervals():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(1, 2)])

    # Act
    result = find_continuous_intervals(intervals)

    # Assert
    assert len(result) == 1
    pd.testing.assert_index_equal(result[0], intervals)


def test_multiple_intervals():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)])

    # Act
    result = find_continuous_intervals(intervals)

    # Assert
    assert len(result) == 2
    pd.testing.assert_index_equal(
        result[0], pd.IntervalIndex.from_tuples([(1, 2), (2, 3)])
    )
    pd.testing.assert_index_equal(result[1], pd.IntervalIndex.from_tuples([(5, 6)]))


def test_unsorted_intervals():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(2, 3), (1, 2)])

    # Act
    result = find_continuous_intervals(intervals)

    # Assert
    assert len(result) == 1
    pd.testing.assert_index_equal(
        result[0], pd.IntervalIndex.from_tuples([(1, 2), (2, 3)])
    )


def test_nonzero_threshold():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)])
    threshold = 2

    # Act
    result = find_continuous_intervals(intervals, threshold)

    # Assert
    assert len(result) == 1
    pd.testing.assert_index_equal(result[0], intervals)


def test_datetime_intervals():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)])
    intervals = pd.IntervalIndex.from_arrays(
        pd.DatetimeIndex(intervals.left), pd.DatetimeIndex(intervals.right)
    )

    # Act
    result = find_continuous_intervals(intervals)

    # Assert
    assert len(result) == 2


def test_datetime_intervals_nonzero_theshold():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)])
    intervals = pd.IntervalIndex.from_arrays(
        pd.DatetimeIndex(intervals.left), pd.DatetimeIndex(intervals.right)
    )
    threshold = pd.Timedelta(2)

    # Act
    result = find_continuous_intervals(intervals, threshold)

    # Assert
    assert len(result) == 1
    pd.testing.assert_index_equal(result[0], intervals)


def test_maintains_dtype():
    # Arrange
    intervals = pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)])
    intervals = pd.IntervalIndex.from_arrays(
        pd.DatetimeIndex(intervals.left, tz="Europe/Oslo"),
        pd.DatetimeIndex(intervals.right, tz="Europe/Oslo"),
        closed="left",
    )

    # Act
    result = find_continuous_intervals(intervals)

    # Assert
    for item in result:
        assert item.dtype == "interval[datetime64[ns, Europe/Oslo], left]"
