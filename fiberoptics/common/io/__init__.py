import os

import h5py
import pandas as pd


def get_filepaths(folder):
    """Retrieves a list of all filepaths in the given folder and its subfolders.

    Parameters
    ----------
    folder : str
        Path to a given folder.

    list, of type str
        Containing paths to all files in the given folder.

    """
    return [os.path.join(dp, f) for dp, ds, fs in os.walk(folder) for f in fs]


def read_hdf(filepath: str):
    """Read dataframe and metadata from HDF file.

    Parameters
    ----------
    filepath : str
        The path to the HDF file.

    Returns
    -------
    (DataFrame, dict)
        The written dataframe and associated metadata.

    """
    with h5py.File(filepath, mode="r") as file:
        df = pd.DataFrame(
            data=file["values"],
            index=pd.DatetimeIndex(file["index"], tz="UTC"),
            columns=file["columns"],
        )
        df.index.freq = df.index.inferred_freq
        metadata = dict(file.attrs)
        return df, metadata


def read_hdf_metadata(filepath: str):
    """Read metadata from HDF file.

    Parameters
    ----------
    filepath : str
        The path to the HDF file.

    Returns
    -------
    dict
        The metadata associated with the file.

    """
    with h5py.File(filepath, mode="r") as file:
        return dict(file.attrs)


def write_hdf(filepath: str, df: pd.DataFrame, metadata: dict):
    """Write dataframe and metadata to HDF file.

    Parameters
    ----------
    filepath : str
        The path to the HDF file.
    df : DataFrame
        The dataframe to write.
    metadata : dict
        Metadata to add as file attributes.

    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with h5py.File(filepath, mode="w") as file:
        file.create_dataset("values", data=df.values)
        file.create_dataset("index", data=df.index.view(int))
        file.create_dataset("columns", data=df.columns)
        for k, v in metadata.items():
            file.attrs[k] = v
