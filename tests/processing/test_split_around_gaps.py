from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from fiberoptics.common.processing import split_around_gaps


def test_split_around_gaps():
    # Arrange
    # Generate example data
    num_intervals = 10000
    interval_length = timedelta(minutes=1)
    loci_range = range(0, 2)

    # Generate random gaps in the index
    # But make sure they will never overlap
    gap_indices = [np.random.randint(i * 1000, (i + 1) * 1000 - 100) for i in range(0, 5)]
    gap_indices.sort()

    # Create the multiindex column
    feature_ids = ["feature1", "feature2"]
    loci = loci_range

    columns = pd.MultiIndex.from_product([feature_ids, loci], names=["featureId", "loci"])

    # Generate the index with IntervalIndex
    start_time = datetime(2023, 8, 21, 0, 0, 0)
    index = []
    current_time = start_time
    for i in range(num_intervals):
        index.append((current_time, current_time + interval_length))
        current_time += interval_length
        if i in gap_indices:
            current_time += timedelta(minutes=np.random.randint(2, 5))  # Add a random gap

    index = pd.IntervalIndex.from_tuples(index, closed="left")

    # Create the DataFrame with random data
    data = np.random.rand(len(index), len(columns))
    df = pd.DataFrame(data, index=index, columns=columns)

    # Act
    result = split_around_gaps(df, min_gap_length="1m")

    # Assert
    assert len(result) == len(gap_indices) + 1
