import pandas as pd
import pytest
from pytest_mock import MockerFixture

from fiberoptics.common.misc._interval import (
    add_interval,
    combine_continuous_intervals,
    deserialize_interval_index,
    find_continuous_intervals,
    serialize_interval_index,
    subtract_interval,
    with_interval_cache,
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
def test_with_interval_cache(mocker: MockerFixture, args_list, expected):
    def get_data(id, start_time, end_time):
        index = pd.date_range(start_time, end_time, freq=pd.Timedelta("0.8192s"))
        columns = pd.RangeIndex(450, 460)
        return pd.DataFrame(0, index, columns)

    get_data_mock = mocker.MagicMock()
    get_data_mock.side_effect = get_data

    get_data_with_cache = with_interval_cache(get_data_mock)

    for args in args_list:
        get_data_with_cache(*args)

    result = get_data_mock.call_args_list

    assert len(result) == len(expected)
    for r, e in zip(result, expected):
        assert r[0] == e


@pytest.mark.parametrize(
    "input,expected",
    [
        pytest.param(
            pd.IntervalIndex([], dtype="interval[int64, right]"),
            dict(left=[], right=[], dtype="interval[int64, right]"),
            id="empty",
        ),
        pytest.param(
            pd.IntervalIndex([], closed="left", dtype="interval[int64, left]"),
            dict(left=[], right=[], dtype="interval[int64, left]"),
            id="empty_closed",
        ),
        pytest.param(
            pd.IntervalIndex([], dtype="interval[datetime64[ns], right]"),
            dict(left=[], right=[], dtype="interval[datetime64[ns], right]"),
            id="empty_datetime",
        ),
        pytest.param(
            pd.IntervalIndex.from_breaks(pd.DatetimeIndex([], tz="Europe/Oslo")),
            dict(
                left=[], right=[], dtype="interval[datetime64[ns, Europe/Oslo], right]"
            ),
            id="empty_datetime_timezone",
        ),
        pytest.param(
            pd.IntervalIndex.from_breaks(range(10)),
            dict(start=0, end=9, freq=1, dtype="interval[int64, right]"),
            id="continuous",
        ),
        pytest.param(
            pd.IntervalIndex.from_breaks(range(10), closed="left"),
            dict(start=0, end=9, freq=1, dtype="interval[int64, left]"),
            id="continuous_closed",
        ),
        pytest.param(
            pd.IntervalIndex.from_breaks([1, 2, 6, 10]),
            dict(left=[1, 2, 6], right=[2, 6, 10], dtype="interval[int64, right]"),
            id="noncontinuous",
        ),
        pytest.param(
            pd.IntervalIndex.from_arrays(
                pd.date_range(start=10e9, end=20e9, freq=pd.Timedelta(1e9)),
                pd.date_range(start=11e9, end=21e9, freq=pd.Timedelta(1e9)),
            ),
            dict(
                start=10e9,
                end=21e9,
                freq=1e9,
                dtype="interval[datetime64[ns], right]",
            ),
            id="continuous_datetime",
        ),
        pytest.param(
            pd.IntervalIndex.from_arrays(
                pd.date_range(start=10e9, end=20e9, freq=pd.Timedelta(1e9)),
                pd.date_range(start=11e9, end=21e9, freq=pd.Timedelta(1e9)),
                closed="left",
            ),
            dict(
                start=10e9,
                end=21e9,
                freq=1e9,
                dtype="interval[datetime64[ns], left]",
            ),
            id="continuous_datetime_closed",
        ),
        pytest.param(
            pd.IntervalIndex.from_arrays(
                pd.date_range(10e9, 20e9, freq=pd.Timedelta(1e9), tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
                pd.date_range(11e9, 21e9, freq=pd.Timedelta(1e9), tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
            ),
            dict(
                start=10e9,
                end=21e9,
                freq=1e9,
                dtype="interval[datetime64[ns, Europe/Oslo], right]",
            ),
            id="continuous_datetime_timezone",
        ),
        pytest.param(
            pd.IntervalIndex.from_arrays(
                left=pd.DatetimeIndex([10e9, 12e9, 15e9, 20e9]),
                right=pd.DatetimeIndex([11e9, 13e9, 16e9, 21e9]),
            ),
            dict(
                left=[10e9, 12e9, 15e9, 20e9],
                right=[11e9, 13e9, 16e9, 21e9],
                dtype="interval[datetime64[ns], right]",
            ),
            id="noncontinuous_datetime",
        ),
        pytest.param(
            pd.IntervalIndex.from_arrays(
                left=pd.DatetimeIndex([10e9, 12e9, 15e9, 20e9]),
                right=pd.DatetimeIndex([11e9, 13e9, 16e9, 21e9]),
                closed="left",
            ),
            dict(
                left=[10e9, 12e9, 15e9, 20e9],
                right=[11e9, 13e9, 16e9, 21e9],
                dtype="interval[datetime64[ns], left]",
            ),
            id="noncontinuous_datetime_closed",
        ),
        pytest.param(
            pd.IntervalIndex.from_arrays(
                left=pd.DatetimeIndex([10e9, 12e9, 15e9, 20e9], tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
                right=pd.DatetimeIndex([11e9, 13e9, 16e9, 21e9], tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
                closed="left",
            ),
            dict(
                left=[10e9, 12e9, 15e9, 20e9],
                right=[11e9, 13e9, 16e9, 21e9],
                dtype="interval[datetime64[ns, Europe/Oslo], left]",
            ),
            id="noncontinuous_datetime_timezone",
        ),
    ],
)
def test_serialize_interval_index(input, expected):
    result = serialize_interval_index(input)
    assert result == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        pytest.param(
            dict(left=[], right=[], dtype="interval[int64, right]"),
            pd.IntervalIndex([], dtype="interval[int64, right]"),
            id="empty",
        ),
        pytest.param(
            dict(left=[], right=[], dtype="interval[int64, left]"),
            pd.IntervalIndex([], closed="left", dtype="interval[int64, left]"),
            id="empty_closed",
        ),
        pytest.param(
            dict(left=[], right=[], dtype="interval[datetime64[ns], right]"),
            pd.IntervalIndex([], dtype="interval[datetime64[ns], right]"),
            id="empty_datetime",
        ),
        pytest.param(
            dict(
                left=[], right=[], dtype="interval[datetime64[ns, Europe/Oslo], right]"
            ),
            pd.IntervalIndex.from_breaks(pd.DatetimeIndex([], tz="Europe/Oslo")),
            id="empty_datetime_timezone",
        ),
        pytest.param(
            dict(start=0, end=9, freq=1, dtype="interval[int64, right]"),
            pd.IntervalIndex.from_breaks(range(10)),
            id="continuous",
        ),
        pytest.param(
            dict(start=0, end=9, freq=1, dtype="interval[int64, left]"),
            pd.IntervalIndex.from_breaks(range(10), closed="left"),
            id="continuous_closed",
        ),
        pytest.param(
            dict(left=[1, 2, 6], right=[2, 6, 10], dtype="interval[int64, right]"),
            pd.IntervalIndex.from_breaks([1, 2, 6, 10]),
            id="noncontinuous",
        ),
        pytest.param(
            dict(
                start=10e9,
                end=21e9,
                freq=1e9,
                dtype="interval[datetime64[ns], right]",
            ),
            pd.IntervalIndex.from_arrays(
                pd.date_range(start=10e9, end=20e9, freq=pd.Timedelta(1e9)),
                pd.date_range(start=11e9, end=21e9, freq=pd.Timedelta(1e9)),
            ),
            id="continuous_datetime",
        ),
        pytest.param(
            dict(
                start=10e9,
                end=21e9,
                freq=1e9,
                dtype="interval[datetime64[ns], left]",
            ),
            pd.IntervalIndex.from_arrays(
                pd.date_range(start=10e9, end=20e9, freq=pd.Timedelta(1e9)),
                pd.date_range(start=11e9, end=21e9, freq=pd.Timedelta(1e9)),
                closed="left",
            ),
            id="continuous_datetime_closed",
        ),
        pytest.param(
            dict(
                start=10e9,
                end=21e9,
                freq=1e9,
                dtype="interval[datetime64[ns, Europe/Oslo], right]",
            ),
            pd.IntervalIndex.from_arrays(
                pd.date_range(10e9, 20e9, freq=pd.Timedelta(1e9), tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
                pd.date_range(11e9, 21e9, freq=pd.Timedelta(1e9), tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
            ),
            id="continuous_datetime_timezone",
        ),
        pytest.param(
            dict(
                left=[10e9, 12e9, 15e9, 20e9],
                right=[11e9, 13e9, 16e9, 21e9],
                dtype="interval[datetime64[ns], right]",
            ),
            pd.IntervalIndex.from_arrays(
                left=pd.DatetimeIndex([10e9, 12e9, 15e9, 20e9]),
                right=pd.DatetimeIndex([11e9, 13e9, 16e9, 21e9]),
            ),
            id="noncontinuous_datetime",
        ),
        pytest.param(
            dict(
                left=[10e9, 12e9, 15e9, 20e9],
                right=[11e9, 13e9, 16e9, 21e9],
                dtype="interval[datetime64[ns], left]",
            ),
            pd.IntervalIndex.from_arrays(
                left=pd.DatetimeIndex([10e9, 12e9, 15e9, 20e9]),
                right=pd.DatetimeIndex([11e9, 13e9, 16e9, 21e9]),
                closed="left",
            ),
            id="noncontinuous_datetime_closed",
        ),
        pytest.param(
            dict(
                left=[10e9, 12e9, 15e9, 20e9],
                right=[11e9, 13e9, 16e9, 21e9],
                dtype="interval[datetime64[ns, Europe/Oslo], left]",
            ),
            pd.IntervalIndex.from_arrays(
                left=pd.DatetimeIndex([10e9, 12e9, 15e9, 20e9], tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
                right=pd.DatetimeIndex([11e9, 13e9, 16e9, 21e9], tz="UTC").tz_convert(
                    "Europe/Oslo"
                ),
                closed="left",
            ),
            id="noncontinuous_datetime_timezone",
        ),
    ],
)
def test_deserialize_interval_index(input, expected):
    result = deserialize_interval_index(input)
    pd.testing.assert_index_equal(result, expected)
