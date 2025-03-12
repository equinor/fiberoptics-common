"""Data processing functions including a variety of filters."""

import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def rolling_rms_window(df: pd.DataFrame, window: pd.Timedelta, min_periods=None) -> pd.DataFrame:
    """Computes the RMS with a given window size.

    Parameters
    ----------
    df : DataFrame
        The raw data with loci as columns and timestamps as rows.
    window : timedelta-like
        The size of the RMS window.
        See `pandas.DataFrame.rolling` for more details.
    min_periods : int, default None
        The minimum number of periods required to compute the window.
        See `pandas.DataFrame.rolling` for more details.

    Returns
    -------
    DataFrame
        The result of applying the RMS window.

    """
    return df.pow(2).rolling(window, min_periods, center=True).mean().pow(0.5)


def low_cut_filter(df: pd.DataFrame, numtaps: int, cutoff: int, fs: int = 10000) -> pd.DataFrame:
    """Performs a low-cut filter.

    Parameters
    ----------
    df : DataFrame
        The data to filter with loci as columns and timestamps as rows.
    numtaps : int
        Length of the filter. See `scipy.signal.firwin` for more details.
    cutoff : int
        Cutoff frequency of the filter. See `scipy.signal.firwin` for more
        details.
    fs : int, default 10000
        The sampling frequency. See `scipy.signal.firwin` for more details.

    Returns
    -------
    DataFrame
        The filtered data.

    """
    import scipy.signal

    window = scipy.signal.firwin(numtaps | 1, cutoff, pass_zero=False, fs=fs)
    return df.apply(lambda x: scipy.signal.convolve(x, window, mode="same"))


def moveout_correction(df: pd.DataFrame, channel: int, moveout: float) -> pd.DataFrame:
    """Performs a moveout correction.

    Parameters
    ----------
    df : DataFrame
        The data to correct with loci as columns and timestamps as rows.
    channel : int
        The reference channel (locus) to use for the moveout correction.
        The data at this locus will stay the same. The further away from
        this locus, the more the data will be moved.
    moveout : float
        Specifies how much to move the data for each loci from the reference
        channel. This value can be negative as well as a fraction. Keep in
        mind that the amount of steps to move is rounded to an integer.
        As an example, if the time sampling interval is 100 microseconds and
        the spatial samping interval is 1.02 meters, a moveout factor of -2
        corresponds to moving data backwards in time with a speed of
        `1.02m / (|-2| * 100us) = 5100m/s` which is approximately the speed
        of sound in steel.

    Returns
    -------
    DataFrame
        The moveout-corrected data.

    """
    return df.apply(lambda col: col.shift(int(abs(col.name - channel) * moveout)))


def median_depth_filter(df: pd.DataFrame, length: int) -> pd.DataFrame:
    """Performs a median filter along the depth axis.

    Parameters
    ----------
    df : DataFrame
        The input data with time as rows and depth as columns.
    length : int
        The number of loci to include in the median filter. A length of 3 allows removal
         of spikes spanning a single depth as seen in Optasense data.

    Returns
    -------
    DataFrame
        The median depth filtered dataframe

    """
    return df.rolling(length, center=True, min_periods=1, axis=1).median()


def depth_aggregation(df: pd.DataFrame, aggregation_window: int = 0, aggregation_function: str = "median") -> pd.DataFrame:
    """Groups input dataframe by columns (depth) and then
    performs aggregation for each of the created groups.
    If input dataframe contains multiindex columns, then
    separates the dataframe over top-level index (0),
    performs all the same actions on each of the sub-frames,
    and merges the result into one dataframe
    with the same structure as the inputted one.

    Parameters
    ----------
    df : DataFrame
        The input data with time as rows and depth as columns.
    aggregation_window : int
        Defines the size of the columns after grouping. For example, for 10
        we will receive columns of size 10, e.g. 0, 10, 20, ... , 4980, 4990, 5000.
    aggregation_function : str
        The name of the function that will be used to aggregate data
        in each of the grouped columns.

    Returns
    -------
    DataFrame
        Dataframe with aggregated columns

    """
    if aggregation_window < 0:
        raise ValueError("Aggregation window cannot be less than zero")

    if aggregation_window == 0:
        return df

    # Split the df into a list of DataFrames by featureIds
    feature_ids = df.columns.get_level_values(0).unique()  # we don't reuse existing featureIds from above just to be sure
    grouped_dfs = (
        [df.xs(feature_id, axis=1, level=0, drop_level=False) for feature_id in feature_ids]
        if df.columns.nlevels > 1
        else [df]
    )

    aggregated_dfs = []
    for grouped_df in grouped_dfs:
        columns = grouped_df.columns.levels[1] if grouped_df.columns.nlevels > 1 else grouped_df.columns
        groups = grouped_df.groupby((columns / aggregation_window).astype("int") * aggregation_window, axis=1)
        grouped_df: pd.DataFrame = getattr(groups, aggregation_function)()
        aggregated_dfs.append(grouped_df)

    merged_df = pd.concat(aggregated_dfs, axis=1, keys=df.columns.levels[0]) if len(aggregated_dfs) > 1 else aggregated_dfs[0]

    return merged_df


def split_around_gaps(df: pd.DataFrame, min_gap_length: str) -> list:
    """Split input DataFrame into multiple DataFrames around the gaps in the index

    Parameters
    ----------
    df : DataFrame
        The input data with time as rows and depth as columns.
    min_gap_length: str
        The timedelta of the minimum possible gap. Specifies what is actually
        considered as an enough duration of gap to split the input dataframe around it.
        F.e. with "1m" value every gap with the duration more than 1 minute
        will be used as a split point.

    Returns
    -------
    list
        List of dataframes

    """
    dataframes_list = []
    start_idx, prev_idx = df.index[0], df.index[0]
    for index in df.index:
        if (index.left - prev_idx.left) > pd.Timedelta(min_gap_length):
            dataframes_list.append(df.loc[pd.Timestamp(start_idx.left) : pd.Timestamp(prev_idx.left)])
            start_idx = index
        prev_idx = index

    # Add the last DataFrame (after the last gap) to the list
    dataframes_list.append(df.loc[pd.Timestamp(start_idx.left) :])

    return dataframes_list


def resample_raw_data(df: pd.DataFrame, dec: int) -> pd.DataFrame:
    """Performs resampling in time using polyphase filtering.

    Parameters
    ----------
    df : DataFrame
        The input data with time as rows and depth as columns.
    dec : int
        Decimation factor, power of 2.

    Returns
    -------
    DataFrame
        Resampled dataframe

    """
    from scipy import signal

    downsampled = signal.resample_poly(df, up=1, down=dec, axis=0, window=10)

    return pd.DataFrame(downsampled, index=df.index[::dec], columns=df.columns)
