import functools
import inspect
import re
from typing import Any, Callable, Literal, TypeVar, Union, get_args, get_origin
from uuid import UUID

import pandas as pd

_T = TypeVar("_T")
_R = TypeVar("_R")


def auto_parse(types: dict = {}):
    def decorator(fn):
        signature = inspect.signature(fn)
        keys = list(signature.parameters)
        types_ = {k: v.annotation for k, v in signature.parameters.items()}
        types_.update(types)

        @functools.wraps(fn)
        def fn_with_auto_parse(*args, **kwargs):
            args = tuple(parse_type(v, types_[k]) for k, v in zip(keys, args))
            kwargs = {k: parse_type(v, types_[k]) for k, v in kwargs.items()}
            return fn(*args, **kwargs)

        return fn_with_auto_parse

    if callable(types):
        fn = types
        types = {}
        return decorator(fn)

    return decorator


def parse_type(value, Type):
    if Type == "ignore" or Type == inspect._empty:
        return value
    if Type == bool:
        return parse_bool(value)
    if Type == str:
        return parse_str(value)
    if Type == UUID:
        return parse_uuid(value)
    if Type == pd.Timestamp:
        return parse_time(value)
    if hasattr(Type, "__annotations__") and isinstance(value, dict):
        return {k: parse_type(v, Type.__annotations__[k]) for k, v in value.items()}

    origin = get_origin(Type)

    if origin == Union:
        # Handle optional type
        try:
            ActualType, MaybeNoneType = get_args(Type)
        except ValueError:
            pass
        else:
            if MaybeNoneType == type(None):  # noqa: E721
                return parse_optional(value, lambda x: parse_type(x, ActualType))
        raise ValueError(f"Unable to parse value with multiple types '{Type}'")
    if origin == Literal:
        if value in get_args(Type):
            return value
        raise ValueError(f"Expected one of {get_args(Type)} but got '{value}'")
    if origin == list:
        try:
            SubType = get_args(Type)[0]
        except KeyError:
            return list(value)
        else:
            return [parse_type(item, SubType) for item in value]

    try:
        return Type(value)
    except TypeError:
        raise ValueError(f"Failed to parse value '{value}' of type '{Type}'")


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


def parse_str(value: Any):
    """Parses string input values.

    Using this function prevents unintentional conversion of objects to strings.

    Parameters
    ----------
    value : Any
        The input value.

    Returns
    -------
    str
        The input converted to a string.

    Raises
    ------
    ValueError
        If the input cannot be safely convert to a string, such as lists.

    """
    if type(value) not in (str, int, UUID):
        raise ValueError(f"Attempted to convert '{value}' to string")
    return str(value)


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


def is_valid_uuid(value):
    """Checks whether the given value is a UUID.

    Parameters
    ----------
    value : Any
        The value to check.

    Returns
    -------
    bool
        True if the input is a valid UUID and false otherwise.

    """
    try:
        parse_uuid(str(value))
        return True
    except ValueError:
        return False


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
