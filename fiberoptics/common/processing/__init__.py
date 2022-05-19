import pandas as pd


def rolling_rms_window(
    df: pd.DataFrame, window: pd.Timedelta, min_periods=None
) -> pd.DataFrame:
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


def low_cut_filter(
    df: pd.DataFrame, numtaps: int, cutoff: int, fs: int = 10000
) -> pd.DataFrame:
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
    """Performs a median filter along the depth axis

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
