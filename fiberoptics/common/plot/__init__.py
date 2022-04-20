import matplotlib.pyplot as plt
import pandas as pd


def rawdata(df: pd.DataFrame, **kwargs):
    """Plots raw data using a set of default arguments.

    Parameters
    ----------
    df : DataFrame
        The raw data.
    kwargs : dict
        Keyword arguments passed to the `imshow` function with the following default
        contents:
        - cmap: "seismic"
        - aspect: "auto"
        - interpolation: "none"
        - vmax: max(abs(df))
        - vmin: -max(abs(df))

    """

    figsize = kwargs.pop("figsize", (12, 6))
    kwargs["cmap"] = kwargs.get("cmap", "seismic")
    kwargs["aspect"] = kwargs.get("aspect", "auto")
    kwargs["interpolation"] = kwargs.get("interpolation", "none")
    vmax = df.abs().max().max()
    kwargs["vmax"] = kwargs.get("vmax", vmax)
    kwargs["vmin"] = kwargs.get("vmin", -vmax)

    plt.figure(figsize=figsize, facecolor="white")
    plt.imshow(df.T, **kwargs)

    ax, row0, col0 = plt.gca(), df.index[0], df.columns[0]
    ax.xaxis.set_major_formatter(
        lambda x, pos: (row0 + pd.Timedelta("100us") * x).strftime("%S.%f")
    )
    ax.yaxis.set_major_formatter(lambda x, pos: str(int(col0 + x)))
    ax.text(-0.05, -0.1, row0.strftime("%Y-%m-%d %H:%M%z"), transform=ax.transAxes)
