import re
from typing import Callable, TypeVar, Union
from uuid import UUID

import pandas as pd

_T = TypeVar("_T")
_R = TypeVar("_R")


def parse_bool(value: bool):
    """Parses boolean input values.

    Parameters
    ----------
    value : bool
        The input value.

    Returns
    -------
    bool
        The input value.
        Works as an identity function for valid input.

    Raises
    ------
    ValueError
        If the input is not explicitly of boolean type.

    """
    if type(value) != bool:
        raise ValueError("Boolean arguments must be either `True` or `False`")
    return value


def parse_optional(value: _T, parser: Callable[[_T], _R]):
    """Applies parsing only if input is not None.

    Parameters
    ----------
    value : T or None
        The input value to parse if not None.
    parser : callable, of type T -> R
        The parser to use if the input is not None.

    Returns
    -------
    R or None
        The result of applying the parser.

    """
    return None if value is None else parser(value)


def parse_time(value: Union[str, int, pd.Timestamp]):
    """Parses input to a Timestamp object.

    Parameters
    ----------
    value : datetime-like
        Can be anything parsable by pandas.
        Integer is expected to be nanoseconds since UNIX epoch.

    Returns
    -------
    Timestamp
        The parsed input value.
        Timezone is set to UTC if undefined.

    """
    time = pd.Timestamp(value)
    if time.tz is None:
        return time.tz_localize("UTC")
    return time


def parse_uuid(value: str) -> str:
    """Parses strings expected to be UUIDs.

    Parameters
    ----------
    value : str
        The input value.

    Returns
    -------
    str
        The input value.
        Works as an identity function for valid input.

    Raises
    ------
    ValueError
        If the input value is not a valid UUID.

    """
    return str(UUID(value))


def to_snake_case(camelCase: str):
    """Converts camel case API naming conventions to snake case.

    Parameters
    ----------
    camelCase : str
        A string written in camel case, e.g. 'profileId'.

    Returns
    -------
    str
        The string converted to snake case, e.g. 'profile_id'.

    """
    return "_".join(re.findall("[A-Z]?[a-z]+", camelCase)).lower()
