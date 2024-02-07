"""Functions for parsing input arguments."""

import functools
import inspect
import re
import typing
import uuid

import pandas as pd

_T = typing.TypeVar("_T")
_R = typing.TypeVar("_R")


def auto_parse(types: typing.Dict[str, typing.Type] = {}):
    """Function decorator to perform automatic parsing of input arguments.

    Parameters
    ----------
    types : dict of types, optional
        The function's type annotations are used as defaults, which can be overridden by
        specifying a dictionary of argument names together with their types.

    """

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


def parse_type(value: typing.Any, Type: _T) -> _T:
    """Parses a value given a specific type.

    Parameters
    ----------
    value : Any
        The value to parse.
    Type : T
        The type used to decide how to parse the value.

    Returns
    -------
    T
        The parsed value.

    Raises
    ------
    ValueError
        If the target type is ambiguous or the value cannot be parsed to the given type.

    """
    if Type == "ignore" or Type == inspect._empty:
        return value
    if Type == bool:
        return parse_bool(value)
    if Type == str:
        return parse_str(value)
    if Type == uuid.UUID:
        return parse_uuid(value)
    if Type == pd.Timestamp:
        return parse_time(value)
    if hasattr(Type, "__annotations__") and isinstance(value, dict):
        return {k: parse_type(v, Type.__annotations__[k]) for k, v in value.items()}

    origin = typing.get_origin(Type)
    args = typing.get_args(Type)

    if origin == typing.Union:
        # Handle optional type
        try:
            ActualType, MaybeNoneType = args
        except ValueError:
            pass
        else:
            if MaybeNoneType == type(None):  # noqa: E721
                return parse_optional(value, lambda x: parse_type(x, ActualType))
        raise ValueError(f"Unable to parse value with multiple types '{Type}'")
    if origin == typing.Literal:
        if value in args:
            return value
        raise ValueError(f"Expected one of {args} but got '{value}'")
    if origin == list:
        try:
            SubType = args[0]
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
    if not isinstance(value, bool):
        raise ValueError("Boolean arguments must be either `True` or `False`")
    return value


def parse_str(value: typing.Any):
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
    if type(value) not in (str, int, uuid.UUID):
        raise ValueError(f"Attempted to convert '{value}' to string")
    return str(value)


def parse_optional(value: _T, parser: typing.Callable[[_T], _R]):
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


def parse_time(value: typing.Union[str, int, pd.Timestamp]):
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


def parse_list(value: typing.Any):
    """Parses input value to be of type list

    Example {} -> [{}]
            [{}] -> [{}]

    Parameters
    --------
    value : Any
        the input value

    Returns
    -------
    list
        the value wrapped within a list
    """

    return [value] if not isinstance(value, list) else value


def parse_uuid(value: typing.Any) -> str:
    """Parses strings expected to be UUIDs.

    Parameters
    ----------
    value : Any
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
    return str(uuid.UUID(str(value)))


def is_valid_uuid(value: typing.Any) -> bool:
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
        parse_uuid(value)
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


def to_camel_case(snake_case: str):
    """Convert snake case fotonepy naming convention to camelCase

    example: user_classifications -> userClassifications

    Parameters
    ------------
    snake_case : str
        A string written in snake case, e.g. user_classifications

    Returns
    -----------
    str
        The 'snake_case' string converted to camelCase
    """

    s = "".join([x.title() for x in snake_case.split("_")])

    return s[:1].lower() if len(s) <= 1 else s[0].lower() + s[1:]
