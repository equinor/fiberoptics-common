import warnings

import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd


class IndexConverterMixin:
    def __init__(self, index: pd.Index):
        self.d0, self.d1 = index[[0, 1]]

    def index2num(self, index: pd.Index):
        return (index - self.d0) / (self.d1 - self.d0)

    def num2index(self, num: float):
        return self.d0 + (self.d1 - self.d0) * num


class MyDateLocator(matplotlib.ticker.Locator, IndexConverterMixin):
    def __init__(self, index: pd.DatetimeIndex):
        super().__init__(index)
        self._delta = pd.TimedeltaIndex(
            [
                *["1us", "2us", "5us"],
                *["10us", "20us", "50us"],
                *["100us", "200us", "500us"],
                *["1000us", "2000us", "5000us"],
                *["10000us", "20000us", "50000us"],
                *["100000us", "200000us", "500000us"],
                *["1s", "5s", "10s", "15s", "30s"],
                *["1m", "5m", "10m", "15m", "30m"],
                *["1h", "2h", "3h", "6h", "12h"],
                *["1d", "3d", "7d", "14d"],
            ]
        )

    def _get_freq(self, target_freq: pd.Timedelta):
        return next(filter(lambda x: target_freq < x, self._delta))

    def __call__(self):
        numticks = max(2, self.axis.get_tick_space() // 2)
        vmin, vmax = self.axis.get_view_interval()
        dmin, dmax = self.num2index(vmin), self.num2index(vmax)
        freq = self._get_freq((dmax - dmin) / numticks)
        dates = pd.date_range(dmin.ceil(freq), dmax.floor(freq), freq=freq)
        return self.index2num(dates)


class MyDateFormatter(matplotlib.ticker.Formatter, IndexConverterMixin):
    def __init__(self, index: pd.DatetimeIndex):
        super().__init__(index)

    def _get_diff_component(self, ts1, ts2):
        components = ("year", "month", "day", "hour", "minute", "second", "microsecond")

        for component in components:
            if getattr(ts1, component) != getattr(ts2, component):
                return component
        return component

    def get_offset(self):
        if not len(self.locs):
            return ""
        dates: pd.DatetimeIndex = self.num2index(self.locs).round("us")
        component = self._get_diff_component(dates[0], dates[-1])
        format = {
            "microsecond": "%d/%m/%Y %H:%M:%S",
            "second": "%d/%m/%Y %H:%M",
            "minute": "%d/%m/%Y %H",
            "hour": "%d/%m/%Y",
            "day": "%Y",
            "month": "%Y",
            "year": "",
        }[component]
        return dates[0].strftime(format)

    def format_ticks(self, values):
        dates: pd.DatetimeIndex = self.num2index(values).round("us")
        component = self._get_diff_component(dates[0], dates[-1])
        format = {
            "microsecond": ".%f",
            "second": "%S.%f",
            "minute": ":%M:%S",
            "hour": "%H:%M",
            "day": "%d/%m %H",
            "month": "%d/%m",
            "year": "%m/%Y",
        }[component]

        formatted = dates.strftime(format)
        if "%f" in format:
            while all(formatted.str[-1] == "0"):
                formatted = formatted.str[:-1]
            if all(formatted.str[-1] == "."):
                formatted = formatted.str[:-1]
        return formatted

    def __call__(self, value, pos=None):
        return ""


class MyLociLocator(matplotlib.ticker.AutoLocator):
    def __call__(self):
        return list(filter(lambda x: x == int(x), super().__call__()))


class MyLociFormatter(matplotlib.ticker.Formatter, IndexConverterMixin):
    def __init__(self, index: pd.Index):
        super().__init__(index)

    def __call__(self, x, pos=None):
        return int(self.num2index(x))


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

    facecolor : str, default "white"
        The figure's background color.

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
    facecolor = kwargs.pop("facecolor", "white")
    kwargs["cmap"] = kwargs.get("cmap", "seismic")
    kwargs["aspect"] = kwargs.get("aspect", "auto")
    kwargs["interpolation"] = kwargs.get("interpolation", "none")
    vmax = df.abs().max().max()
    kwargs["vmax"] = kwargs.get("vmax", vmax)
    kwargs["vmin"] = kwargs.get("vmin", -vmax)

    if "ax" not in kwargs:
        plt.figure(figsize=figsize, facecolor=facecolor)

    ax = kwargs.pop("ax", plt.gca())
    iax = ax.imshow(df.T, **kwargs)

    if colorbar:
        plt.colorbar(iax, ax=ax)

    ax.xaxis.set_major_locator(MyDateLocator(df.index))
    ax.xaxis.set_major_formatter(MyDateFormatter(df.index))
    ax.yaxis.set_major_locator(MyLociLocator())
    ax.yaxis.set_major_formatter(MyLociFormatter(df.columns))


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
        if isinstance(df[column].dtype, pd.IntervalDtype):
            df[column] = df[column].array.mid

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
            warnings.warn(
                "Pass a list of integers as 'c' to enable automatic legend generation"
            )
