"""Powerful plotting functions for ease-of-use."""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def rawdataplot(df: pd.DataFrame, **kwargs):
    """Plots raw data using a set of default arguments.

    See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.imshow.html for more
    information on the input parameters.

    Parameters
    ----------
    df : DataFrame
        The raw data.

    figsize : (float, float)
        The size of the figure to create.

    colorbar : bool
        Whether or not to include a colorbar.

    cmap : str, default "seismic"
        The color map to use.
        See https://matplotlib.org/stable/tutorials/colors/colormaps.html for a list of
        available color maps.

    aspect : {'equal', 'auto'} or float, default "auto"
        The aspect ratio of the plot.

    interpolation : str, default "none"
        The interpolation method used.

    vmax, vmin : float, default +/-max(abs(df))
        The range covered by the color map.

    resample : bool, default True
        Dates are resampled to the minimum frequency present in the index.
        A linear time index is necessary to display correct labels.

    skip_single_gaps : bool, default True
        If there is only missing one sample at a time, it will be interpolated.
        Uses .ffill(limit=2) instead .first().
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected 'df' to be of type DataFrame")

    if isinstance(df.columns, pd.MultiIndex):
        if len(df.columns.levels[0]) == 1:
            df = df[df.columns.levels[0][0]]  # Flatten multi-index
        else:
            raise TypeError("Expected 'df' to be two-dimensional")

    if isinstance(df.index, pd.IntervalIndex):
        df = df.set_index(df.index.mid)

    figsize = kwargs.pop("figsize", (12, 6))
    colorbar = kwargs.pop("colorbar", False)
    resample = kwargs.pop("resample", True)
    skip_single_gaps = kwargs.pop("skip_single_gaps", True)

    if isinstance(df.index, pd.DatetimeIndex) and resample:
        min_index_gap = min(df.index[1:] - df.index[:-1])
        df = df.resample(min_index_gap, origin="start")
        if skip_single_gaps:
            df = df.ffill(limit=2)
        else:
            df = df.first()
    else:
        df = df.set_index(np.arange(len(df.index)))

    kwargs["cmap"] = kwargs.get("cmap", "seismic")
    kwargs["aspect"] = kwargs.get("aspect", "auto")
    kwargs["interpolation"] = kwargs.get("interpolation", "none")
    kwargs["vmax"] = kwargs.get("vmax", np.nanquantile(df, 0.99))
    kwargs["vmin"] = kwargs.get("vmin", np.nanquantile(df, 0.01))

    if "ax" not in kwargs:
        plt.figure(figsize=figsize)

    ax = kwargs.pop("ax", plt.gca())
    iax = ax.imshow(df.values.T, extent=[df.index[0], df.index[-1], df.columns[-1], df.columns[0]], **kwargs)

    if colorbar:
        plt.colorbar(iax, ax=ax)


def scatterplot(df: pd.DataFrame, **kwargs):
    """Plots timeseries data or a two-column dataframe as a scatter plot.

    See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.plot.scatter.html
    for more information on the input parameters.

    Parameters
    ----------
    df : Series or DataFrame
        - Series are plotted using the index as x-axis and values as y-axis.
        - Dataframes are plotted using first column as x-axis and second as y-axis.

        Intervals are converted to points using their middle values.

    figsize : (int, int), optional
        The size of the figure.

    c : str, int or array-like, optional
        The color of each data point.

    s : str, scalar or array-like, optional
        The size of each data point.

    legend : bool, optional
        Whether or not to include a legend in the scatter plot.
        Defaults to True if `c` is given.

    """
    if isinstance(df, pd.Series):
        df = df.to_frame(name=df.name or "value").reset_index()

        # Smaller defaults for series
        kwargs["figsize"] = kwargs.get("figsize", (16, 6))
        kwargs["s"] = kwargs.get("s", 5)

    # Convert intervals to points
    for column in df.columns[:2]:
        if df[column].dtype == "interval":
            df[column] = df[column].array.mid
        if df[column].dtype == "bool":
            df[column] = df[column].astype("int")

    kwargs["figsize"] = kwargs.get("figsize", (16, 10))
    kwargs["s"] = kwargs.get("s", 10)
    kwargs["colormap"] = kwargs.get("colormap", "tab10")
    kwargs["colorbar"] = kwargs.get("colorbar", False)
    legend = kwargs.pop("legend", None)

    # Convert column labels to strings to use 0 and 1 as arguments
    ax: plt.Axes = df.rename(str, axis=1).plot.scatter(0, 1, **kwargs)

    if legend is not False:
        if "c" in kwargs:
            ax.legend(*ax.get_children()[0].legend_elements())
        elif legend is True:
            # Only warn if legend is explicitly set to True
            warnings.warn("Pass a list of integers as 'c' to enable automatic legend generation")
