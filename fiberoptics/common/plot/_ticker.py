import math

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
        self._valid_freqs = pd.TimedeltaIndex(
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

    def _get_valid_freq(self, target_freq: pd.Timedelta) -> pd.Timedelta:
        try:
            return next(filter(lambda x: target_freq < x, self._valid_freqs))
        except StopIteration:
            return self._valid_freqs[-1]

    def __call__(self):
        numticks = max(2, self.axis.get_tick_space() // 2)
        vmin, vmax = self.axis.get_view_interval()
        dmin, dmax = self.num2index(vmin), self.num2index(vmax)
        target_freq = (dmax - dmin) / numticks
        if target_freq > pd.Timedelta("365d") / 2:
            num_years = math.ceil(target_freq / pd.Timedelta("365d"))
            dates = pd.date_range(dmin.floor("d"), dmax, freq=f"{num_years}YS")
        elif target_freq > pd.Timedelta("31d") / 2:
            num_months = math.ceil(target_freq / pd.Timedelta("31d"))
            dates = pd.date_range(dmin.floor("d"), dmax, freq=f"{num_months}MS")
        else:
            freq = self._get_valid_freq(target_freq)
            dates = pd.date_range(dmin.ceil(freq), dmax.floor(freq), freq=freq)
        return self.index2num(dates)


class MyDateFormatter(matplotlib.ticker.Formatter, IndexConverterMixin):
    def __init__(self, index: pd.DatetimeIndex):
        super().__init__(index)

    def _get_diff_component(self, ts1, ts2, reversed=False):
        components = ("year", "month", "day", "hour", "minute", "second", "microsecond")
        components = tuple(enumerate(components))

        if reversed:
            components = components[::-1]

        for i, component in components:
            if getattr(ts1, component) != getattr(ts2, component):
                return i
        return components[0][0]

    def get_offset(self):
        if not len(self.locs):
            return ""
        dates: pd.DatetimeIndex = self.num2index(self.locs).round("us")
        largest = self._get_diff_component(dates[0], dates[-1])
        format = "%Y-%m-%d %H:%M:%S.%f"[: largest * 3]
        return dates[0].strftime(format)

    def format_ticks(self, values):
        dates: pd.DatetimeIndex = self.num2index(values).round("us")
        if len(dates) < 2:
            return list(dates.tz_localize(None).astype(str))
        largest = self._get_diff_component(dates[0], dates[-1])
        smallest = self._get_diff_component(dates[0], dates[1], reversed=True)
        format = "%Y-%m-%d %H:%M:%S.%f"[largest * 3 : smallest * 3 + 2]
        formatted = dates.strftime(format)
        if ".%f" in format:
            while all(formatted.str[-1] == "0"):
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
