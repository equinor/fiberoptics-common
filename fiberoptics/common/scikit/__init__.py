"""Wrappers around sklearn classes to handle dataframes."""

from typing import Union

import pandas as pd
import sklearn.decomposition
import sklearn.manifold
import sklearn.preprocessing


def _generic_dataclass(cls):
    """Decorator for classes that allow any input arguments."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        parse = lambda v: f"'{v}'" if isinstance(v, str) else str(v)  # noqa: E731
        args = [parse(v) for v in self.args]
        kwargs = [f"{k}={parse(v)}" for k, v in self.kwargs.items()]
        return f"{self.__class__.__name__}({', '.join([*args, *kwargs])})"

    cls.__init__ = __init__
    cls.__repr__ = __repr__

    return cls


class PCA(sklearn.decomposition.PCA):
    """Overrides methods to handle dataframes."""

    def fit_transform(self, X: pd.DataFrame, y=None):
        return pd.DataFrame(super().fit_transform(X), index=X.index)


class TSNE(sklearn.manifold.TSNE):
    """Overrides methods to handle dataframes."""

    def fit_transform(self, X: pd.DataFrame, y=None):
        return pd.DataFrame(super().fit_transform(X), index=X.index)


class MinMaxScaler(sklearn.preprocessing.MinMaxScaler):
    """Overrides methods to handle dataframes."""

    def fit(self, df: pd.DataFrame):
        super().fit(df)
        return self

    def transform(self, df: pd.DataFrame):
        result = df if df.empty else super().transform(df)
        return pd.DataFrame(result, index=df.index, columns=df.columns)

    def fit_transform(self, df: pd.DataFrame):
        return self.fit(df).transform(df)

    def inverse_transform(self, df: pd.DataFrame):
        result = super().inverse_transform(df)
        return pd.DataFrame(result, index=df.index, columns=df.columns)


class MinMax1dScaler(MinMaxScaler):
    """Overrides methods to handle series."""

    def fit(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().fit(df)
        return super().fit(df_or_series)

    def transform(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().transform(df)[0].rename(df_or_series.name)
        return super().transform(df_or_series)

    def inverse_transform(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().inverse_transform(df)[0].rename(df_or_series.name)
        return super().inverse_transform(df_or_series)


class MinMax2dScaler(MinMax1dScaler):
    """Overrides methods to apply to 2d data."""

    def fit(self, df: pd.DataFrame):
        return super().fit(df.stack(dropna=False))

    def transform(self, df: pd.DataFrame):
        return super().transform(df.stack(dropna=False)).unstack()

    def inverse_transform(self, df: pd.DataFrame):
        return super().inverse_transform(df.stack(dropna=False)).unstack()


class RobustScaler(sklearn.preprocessing.RobustScaler):
    """Overrides methods to handle dataframes."""

    def fit(self, df: pd.DataFrame):
        super().fit(df)
        return self

    def transform(self, df: pd.DataFrame):
        result = df if df.empty else super().transform(df)
        return pd.DataFrame(result, index=df.index, columns=df.columns)

    def fit_transform(self, df: pd.DataFrame):
        return self.fit(df).transform(df)

    def inverse_transform(self, df: pd.DataFrame):
        result = super().inverse_transform(df)
        return pd.DataFrame(result, index=df.index, columns=df.columns)


class Robust1dScaler(RobustScaler):
    """Overrides methods to handle series."""

    def fit(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().fit(df)
        return super().fit(df_or_series)

    def transform(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().transform(df)[0].rename(df_or_series.name)
        return super().transform(df_or_series)

    def inverse_transform(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().inverse_transform(df)[0].rename(df_or_series.name)
        return super().inverse_transform(df_or_series)


class Robust2dScaler(Robust1dScaler):
    """Overrides methods to apply to 2d data."""

    def fit(self, df: pd.DataFrame):
        return super().fit(df.stack(dropna=False))

    def transform(self, df: pd.DataFrame):
        return super().transform(df.stack(dropna=False)).unstack()

    def inverse_transform(self, df: pd.DataFrame):
        return super().inverse_transform(df.stack(dropna=False)).unstack()


class StandardScaler(sklearn.preprocessing.StandardScaler):
    """Overrides methods to handle dataframes."""

    def fit(self, df: pd.DataFrame):
        super().fit(df)
        return self

    def transform(self, df: pd.DataFrame):
        result = df if df.empty else super().transform(df)
        return pd.DataFrame(result, index=df.index, columns=df.columns)

    def fit_transform(self, df: pd.DataFrame):
        return self.fit(df).transform(df)

    def inverse_transform(self, df: pd.DataFrame):
        result = super().inverse_transform(df)
        return pd.DataFrame(result, index=df.index, columns=df.columns)


class Standard1dScaler(StandardScaler):
    """Overrides methods to handle series."""

    def fit(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().fit(df)
        return super().fit(df_or_series)

    def transform(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().transform(df)[0].rename(df_or_series.name)
        return super().transform(df_or_series)

    def inverse_transform(self, df_or_series: Union[pd.DataFrame, pd.Series]):
        if isinstance(df_or_series, pd.Series):
            df = df_or_series.rename(None).to_frame()
            return super().inverse_transform(df)[0].rename(df_or_series.name)
        return super().inverse_transform(df_or_series)


class Standard2dScaler(Standard1dScaler):
    """Overrides methods to apply to 2d data."""

    def fit(self, df: pd.DataFrame):
        return super().fit(df.stack(dropna=False))

    def transform(self, df: pd.DataFrame):
        return super().transform(df.stack(dropna=False)).unstack()

    def inverse_transform(self, df: pd.DataFrame):
        return super().inverse_transform(df.stack(dropna=False)).unstack()


@_generic_dataclass
class TimeseriesStandardScaler:
    """Applies standard scaling over a rolling window.

    See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rolling.html
    for supported input arguements.
    """

    def _transform(self, df: pd.DataFrame):
        mean = df.rolling(*self.args, **self.kwargs).mean()
        std = df.rolling(*self.args, **self.kwargs).std().bfill()
        return df.sub(mean, axis=0).div(std, axis=0)

    def fit_transform(self, df: pd.DataFrame):
        if isinstance(df.index, pd.IntervalIndex):
            return self._transform(df.set_index(df.index.mid)).set_index(df.index)
        return self._transform(df)


@_generic_dataclass
class TimeseriesRobustScaler:
    """Applies robust scaling over a rolling window.

    See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rolling.html
    for supported input arguements.
    """

    def _transform(self, df: pd.DataFrame):
        q25 = df.rolling(*self.args, **self.kwargs).quantile(0.25)
        q50 = df.rolling(*self.args, **self.kwargs).quantile(0.50)
        q75 = df.rolling(*self.args, **self.kwargs).quantile(0.75)
        return df.sub(q50, axis=0).div(q75 - q25, axis=0)

    def fit_transform(self, df: pd.DataFrame):
        if isinstance(df.index, pd.IntervalIndex):
            return self._transform(df.set_index(df.index.mid)).set_index(df.index)
        return self._transform(df)
