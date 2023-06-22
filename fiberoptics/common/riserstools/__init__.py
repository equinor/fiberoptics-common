""""Useful functions for processing riser data"""
import re
from typing import TypedDict

import pandas as pd


class Description(TypedDict, total=False):
    topside_end_fitting: int
    bending_stiffener_start: int
    bending_stiffener_end: int
    sea_start: int
    sea_end: int
    fire_protection_start: int
    fire_protection_end: int
    sag_bend_start: int
    sag_bend_end: int
    hog_bend_start: int
    tether_clamp: int
    touchdown_point_start: int
    touchdown_point_end: int
    seabed_start: int
    seabed_end: int
    subsea_end_fitting_start: int
    subsea_end_fitting_end: int
    bm_count: int
    bm_start: int
    bm_end: int

buoyancy_module_regex = r"(b(ou|uo)yancy module|bm)(\s|_)*(?P<number>\d+)"

def add_loci_to_ties(
    ties: pd.DataFrame,
    spatial_sampling: float,
    offset: float = 0,
) -> pd.DataFrame:
    """
    Adds sensor index to all ties in depth calibration.

    Parameters
    ----------
    ties : DataFrame
        Depth calibration ties sensor index will be added to. Must contain fiber_length column.
    spatial_sampling : float
        Spatial sampling interval (distance between sensors).
    offset : float
        Fiber start depth for measurements.

    Returns
    -------
    DataFrame
        Depth calibration ties with loci.
    """

    ties["locus"] = (round((ties.fiber_length - offset) / spatial_sampling)).apply(int)
    return ties

def get_buoyancy_modules(desc: Description) -> pd.Series:
    """
    Selects only buoyancy modules from the description.

    Parameters
    ----------
    desc : dict | Series
        Description dictionary or pandas Series with element name as index and loci as values.

    Returns
    -------
    Series
        Buoyancy modules' positions.
    """
    desc = pd.Series(desc)
    return desc[desc.index.str.match(buoyancy_module_regex, flags=re.IGNORECASE)]

def mapping(name: str) -> str:
    """Converts depth calibration naming conventions to snake case.

    Parameters
    ----------
    name : str
        A depth calibration name, e.g. 'Bending stiffener start', 'Buoyancy Module 1.

    Returns
    -------
    str
        The string converted to snake case, e.g. 'bending_stiffener', 'bm_1.

    """
    name = name.strip()
    match = re.match(buoyancy_module_regex, name, re.IGNORECASE)
    if match:
        return f"bm_{match.groupdict()['number']}"
    return name.lower().replace(" ", "_")