import pandas as pd
import pytest
from pytest_mock import MockerFixture

from fiberoptics.common import (
    add_interval,
    cache_decorator,
    combine_continuous_intervals,
    find_continuous_intervals,
    subtract_interval,
)


@pytest.mark.parametrize(
    "args,expected",
    [
        pytest.param(
            (pd.IntervalIndex.from_tuples([]),),
            [],
            id="empty_intervals",
        ),
        pytest.param(
            (pd.IntervalIndex.from_tuples([(1, 2)]),),
            [pd.IntervalIndex.from_tuples([(1, 2)])],
            id="single_intervals",
        ),
        pytest.param(
            (pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)]),),
            [
                pd.IntervalIndex.from_tuples([(1, 2), (2, 3)]),
                pd.IntervalIndex.from_tuples([(5, 6)]),
            ],
            id="multiple_intervals",
        ),
        pytest.param(
            (
                pd.IntervalIndex.from_arrays(
                    pd.Index([1, 3, 5, 6, 7, 9, 10, 11, 12, 15, 17, 19, 20, 21]),
                    pd.Index([1, 3, 5, 6, 7, 9, 10, 11, 12, 15, 17, 19, 20, 21]) + 1,
                ),
            ),
            [
                pd.IntervalIndex.from_breaks([1, 1 + 1]),
                pd.IntervalIndex.from_breaks([3, 3 + 1]),
                pd.IntervalIndex.from_breaks([5, 6, 7, 7 + 1]),
                pd.IntervalIndex.from_breaks([9, 10, 11, 12, 12 + 1]),
                pd.IntervalIndex.from_breaks([15, 15 + 1]),
                pd.IntervalIndex.from_breaks([17, 17 + 1]),
                pd.IntervalIndex.from_breaks([19, 20, 21, 21 + 1]),
            ],
            id="several_intervals",
        ),
        pytest.param(
            (pd.IntervalIndex.from_tuples([(2, 3), (1, 2)]),),
            [pd.IntervalIndex.from_tuples([(1, 2), (2, 3)])],
            id="unsorted_intervals",
        ),
        pytest.param(
            (pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)]), 2),
            [pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)])],
            id="nonzero_threshold",
        ),
        pytest.param(
            (
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([1, 2, 5]),
                    pd.DatetimeIndex([2, 3, 6]),
                ),
            ),
            [
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([1, 2]),
                    pd.DatetimeIndex([2, 3]),
                ),
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([5]),
                    pd.DatetimeIndex([6]),
                ),
            ],
            id="datetime_intervals",
        ),
        pytest.param(
            (
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([1, 2, 5]),
                    pd.DatetimeIndex([2, 3, 6]),
                ),
                pd.Timedelta(2),
            ),
            [
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([1, 2, 5]),
                    pd.DatetimeIndex([2, 3, 6]),
                ),
            ],
            id="datetime_intervals_nonzero_threshold",
        ),
        pytest.param(
            (
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([1, 2, 5], tz="Europe/Oslo"),
                    pd.DatetimeIndex([2, 3, 6], tz="Europe/Oslo"),
                    closed="left",
                ),
            ),
            [
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([1, 2], tz="Europe/Oslo"),
                    pd.DatetimeIndex([2, 3], tz="Europe/Oslo"),
                    closed="left",
                ),
                pd.IntervalIndex.from_arrays(
                    pd.DatetimeIndex([5], tz="Europe/Oslo"),
                    pd.DatetimeIndex([6], tz="Europe/Oslo"),
                    closed="left",
                ),
            ],
            id="maintains_dtype",
        ),
    ],
)
def test_find_continuous_intervals(args, expected):
    result = find_continuous_intervals(*args)
    assert len(result) == len(expected)
    for r, e in zip(result, expected):
        pd.testing.assert_index_equal(r, e)


@pytest.mark.parametrize(
    "args,expected",
    [
        pytest.param(
            (pd.IntervalIndex.from_tuples([(1, 2)]),),
            pd.IntervalIndex.from_tuples([(1, 2)]),
            id="single_intervals",
        ),
        pytest.param(
            (pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)]),),
            pd.IntervalIndex.from_tuples([(1, 3), (5, 6)]),
            id="multiple_intervals",
        ),
        pytest.param(
            (pd.IntervalIndex.from_tuples([(1, 2), (2, 3), (5, 6)]), 2),
            pd.IntervalIndex.from_tuples([(1, 6)]),
            id="nonzero_threshold",
        ),
    ],
)
def test_combine_intervals(args, expected):
    result = combine_continuous_intervals(*args)
    pd.testing.assert_index_equal(result, expected)


@pytest.mark.parametrize(
    "self,other,expected",
    [
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(0, 20),
            pd.IntervalIndex.from_tuples([(0, 20), (30, 60)]),
            id="no_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(10, 40),
            pd.IntervalIndex.from_tuples([(10, 60)]),
            id="left_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(50, 100),
            pd.IntervalIndex.from_tuples([(30, 100)]),
            id="right_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(40, 50),
            pd.IntervalIndex.from_tuples([(30, 60)]),
            id="both_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(0, 100),
            pd.IntervalIndex.from_tuples([(0, 100)]),
            id="full_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(10, 20), (40, 50), (70, 80)]),
            pd.Interval(15, 75),
            pd.IntervalIndex.from_tuples([(10, 80)]),
            id="multiple_overlap",
        ),
    ],
)
def test_add_interval(self, other, expected):
    result = add_interval(self, other)
    pd.testing.assert_index_equal(result, expected)


@pytest.mark.parametrize(
    "self,other,expected",
    [
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(0, 20),
            pd.IntervalIndex.from_tuples([(30, 60)]),
            id="no_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(10, 40),
            pd.IntervalIndex.from_tuples([(40, 60)]),
            id="left_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(50, 100),
            pd.IntervalIndex.from_tuples([(30, 50)]),
            id="right_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(40, 50),
            pd.IntervalIndex.from_tuples([(30, 40), (50, 60)]),
            id="both_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(30, 60)]),
            pd.Interval(0, 100),
            pd.IntervalIndex.from_tuples([]),
            id="full_overlap",
        ),
        pytest.param(
            pd.IntervalIndex.from_tuples([(10, 20), (40, 50), (70, 80)]),
            pd.Interval(15, 75),
            pd.IntervalIndex.from_tuples([(10, 15), (75, 80)]),
            id="multiple_intervals",
        ),
    ],
)
def test_subtract_interval(self, other, expected):
    result = subtract_interval(self, other)
    pd.testing.assert_index_equal(result, expected)


@pytest.mark.parametrize(
    "args_list,expected",
    [
        pytest.param(
            [
                ("id", "2022-01-10", "2022-01-20"),
                ("id", "2022-01-10", "2022-01-20"),
            ],
            [
                ("id", pd.Timestamp("2022-01-10"), pd.Timestamp("2022-01-20")),
            ],
            id="same_interval",
        ),
        pytest.param(
            [
                ("id", "2022-01-10", "2022-01-20"),
                ("newid", "2022-01-10", "2022-01-20"),
            ],
            [
                ("id", pd.Timestamp("2022-01-10"), pd.Timestamp("2022-01-20")),
                ("newid", pd.Timestamp("2022-01-10"), pd.Timestamp("2022-01-20")),
            ],
            id="same_interval_different_id",
        ),
        pytest.param(
            [
                ("id", "2022-01-10", "2022-01-20"),
                ("id", "2022-01-01", "2022-01-20"),
                ("id", "2022-01-10", "2022-01-30"),
            ],
            [
                ("id", pd.Timestamp("2022-01-10"), pd.Timestamp("2022-01-20")),
                ("id", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-01-10")),
                ("id", pd.Timestamp("2022-01-20"), pd.Timestamp("2022-01-30")),
            ],
            id="single_overlap",
        ),
        pytest.param(
            [
                ("id", "2022-01-10", "2022-01-20"),
                ("id", "2022-01-01", "2022-01-30"),
            ],
            [
                ("id", pd.Timestamp("2022-01-10"), pd.Timestamp("2022-01-20")),
                ("id", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-01-10")),
                ("id", pd.Timestamp("2022-01-20"), pd.Timestamp("2022-01-30")),
            ],
            id="outer_overlap",
        ),
        pytest.param(
            [
                ("id", "2022-01-01", "2022-01-10"),
                ("id", "2022-01-20", "2022-01-30"),
                ("id", "2022-01-01", "2022-01-30"),
            ],
            [
                ("id", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-01-10")),
                ("id", pd.Timestamp("2022-01-20"), pd.Timestamp("2022-01-30")),
                ("id", pd.Timestamp("2022-01-10"), pd.Timestamp("2022-01-20")),
            ],
            id="inner_overlap",
        ),
    ],
)
def test_cache_decorator(mocker: MockerFixture, args_list, expected):
    def get_data(id, start_time, end_time):
        index = pd.date_range(start_time, end_time, freq=pd.Timedelta("0.8192s"))
        columns = pd.RangeIndex(450, 460)
        return pd.DataFrame(0, index, columns)

    get_data_mock = mocker.MagicMock()
    get_data_mock.side_effect = get_data

    get_data_with_cache = cache_decorator(get_data_mock)

    for args in args_list:
        get_data_with_cache(*args)

    result = get_data_mock.call_args_list

    assert len(result) == len(expected)
    for r, e in zip(result, expected):
        assert r[0] == e
