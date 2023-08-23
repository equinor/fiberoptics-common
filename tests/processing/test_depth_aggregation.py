import math
from datetime import datetime, timedelta
from functools import reduce

import numpy as np
import pandas as pd
import pytest

from fiberoptics.common.processing import depth_aggregation


@pytest.mark.parametrize(
    "start,end,aggregation_window,top_level_length",
    [
        (0, 1000, 10, 1),
        (10, 100, 5, 2),
        (500, 5000, 2, 5),
    ],
)
def test_depth_aggregation(
    start: int, end: int, aggregation_window: int, top_level_length: int
):
    # Arrange
    # Generate example data
    num_intervals = 10
    interval_length = timedelta(seconds=1)
    loci_range = range(start, end + 1)  # From start to end, inclusive

    # Create the multiindex column
    feature_ids = [f"feature{i}" for i in range(0, top_level_length)]
    loci = loci_range

    columns = pd.MultiIndex.from_product(
        [feature_ids, loci], names=["featureId", "loci"]
    )

    # Generate the index with IntervalIndex
    start_time = datetime(2023, 8, 21, 0, 0, 0)
    end_time = start_time + interval_length * num_intervals
    index = pd.IntervalIndex.from_tuples(
        [
            (t, t + interval_length)
            for t in pd.date_range(
                start_time, end_time - interval_length, freq=interval_length
            )
        ],
        closed="left",
    )

    # Create the DataFrame with random data
    data = np.random.rand(len(index), len(columns))
    df = pd.DataFrame(data, index=index, columns=columns)

    # Act
    aggregated_df = depth_aggregation(df, aggregation_window=aggregation_window)
    grouped = df.groupby(level=0, axis=1)
    grouped_dfs = [grouped.get_group(group_name) for group_name in grouped.groups]
    expected = reduce(
        lambda acc, obj: acc + obj,
        map(
            lambda x: math.ceil(len(x.columns.levels[1]) / aggregation_window),
            grouped_dfs,
        ),
        0,
    )

    # Assert
    assert expected == len(aggregated_df.columns)


@pytest.mark.parametrize(
    "start,end,aggregation_window",
    [
        (0, 1000, 10),
        (10, 100, 5),
        (500, 5000, 2),
    ],
)
def test_depth_aggregation_no_multiindex(start: int, end: int, aggregation_window: int):
    # Arrange
    # Generate example data
    num_intervals = 1000
    interval_length = timedelta(seconds=1)
    loci_range = range(start, end + 1)  # From start to end, inclusive

    # Create the index with IntervalIndex
    start_time = datetime(2023, 8, 21, 0, 0, 0)
    end_time = start_time + interval_length * num_intervals
    index = pd.IntervalIndex.from_tuples(
        [
            (t, t + interval_length)
            for t in pd.date_range(
                start_time, end_time - interval_length, freq=interval_length
            )
        ],
        closed="left",
    )

    # Create the DataFrame with random data and "loci" columns
    data = np.random.rand(len(index), len(loci_range))
    df = pd.DataFrame(data, index=index, columns=loci_range)

    # Act
    aggregated_df = depth_aggregation(df, aggregation_window=aggregation_window)
    expected = math.ceil(len(df.columns) / aggregation_window)

    # Assert
    assert expected == len(aggregated_df.columns)
