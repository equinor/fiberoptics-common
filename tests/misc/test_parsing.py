import typing
import uuid

import pandas as pd
import pytest

from fiberoptics.common.misc.Parser import (
    auto_parse,
    is_valid_uuid,
    parse_bool,
    parse_optional,
    parse_str,
    parse_time,
    parse_uuid,
    to_snake_case,
)


@pytest.mark.parametrize(
    "Type,input,expected",
    [
        (str, 1, "1"),
        (int, 1.1, 1),
        (int, "1", 1),
        (bool, True, True),
        (typing.Optional[bool], True, True),
        (typing.Optional[bool], None, None),
        (typing.Literal["a", "b"], "b", "b"),
        (typing.Optional[typing.Literal["a", "b"]], "b", "b"),
        (typing.Optional[typing.Literal["a", "b"]], None, None),
        (
            uuid.UUID,
            str(uuid.uuid5(uuid.NAMESPACE_OID, "1")),
            str(uuid.uuid5(uuid.NAMESPACE_OID, "1")),
        ),
        (pd.Timedelta, 1, pd.Timedelta(1)),
        (pd.Timedelta, "10ms", pd.Timedelta("10ms")),
        (pd.Timestamp, 1, pd.Timestamp(1, tz="UTC")),
        (pd.Timestamp, "2020-01-01", pd.Timestamp("2020-01-01", tz="UTC")),
        (
            typing.TypedDict("TypedDict", {"a": int, "b": int}),
            dict(a=1, b="2"),
            dict(a=1, b=2),
        ),
    ],
)
def test_auto_parse(Type, input, expected):
    @auto_parse
    def fn(value: Type):
        return value

    assert fn(input) == expected


@pytest.mark.parametrize(
    "Type,input",
    [
        (int, None),
        (int, "a"),
        (bool, None),
        (bool, 1),
        (str, None),
        (str, ["a"]),
        (uuid.UUID, "c"),
        (typing.Literal["a", "b"], "c"),
        (typing.Union[str, typing.List[str]], ["a"]),
    ],
)
def test_auto_parse__invalid_input__should_raise(Type, input):
    @auto_parse
    def fn(value: Type):
        return value

    with pytest.raises(ValueError):
        fn(input)


@pytest.mark.parametrize(
    "Type,types,input,expected",
    [
        (int, dict(value=str), 1, "1"),
        (int, dict(value="ignore"), "1", "1"),
        (
            typing.Union[str, int, pd.Timestamp],
            dict(value=pd.Timestamp),
            1e9,
            pd.Timestamp(1e9, tz="UTC"),
        ),
        (
            str,
            dict(value=uuid.UUID),
            str(uuid.uuid5(uuid.NAMESPACE_OID, "1")),
            str(uuid.uuid5(uuid.NAMESPACE_OID, "1")),
        ),
    ],
)
def test_auto_parse__with_types(Type, types, input, expected):
    @auto_parse(types)
    def fn(value: Type):
        return value

    assert fn(input) == expected


@pytest.mark.parametrize("input", [1, "a", dict(a=1)])
def test_auto_parse__no_type_annotation(input):
    @auto_parse
    def fn(value):
        return value

    assert fn(input) == input


@pytest.mark.parametrize("value", [True, False])
def test_parse_bool(value):
    assert parse_bool(value) == value


@pytest.mark.parametrize("value", ["True", 1, "", 0])
def test_parse_bool__invalid_input__should_raise(value):
    with pytest.raises(ValueError):
        parse_bool(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("abcd", "abcd"),
        (1, "1"),
        (
            uuid.uuid5(uuid.NAMESPACE_OID, "abcd"),
            str(uuid.uuid5(uuid.NAMESPACE_OID, "abcd")),
        ),
    ],
)
def test_parse_str(value, expected):
    assert parse_str(value) == expected


@pytest.mark.parametrize("value", [None, 1.1, [1, 2, 3], pd.Timestamp(1e9)])
def test_parse_str__invalid_input__should_raise(value):
    with pytest.raises(ValueError):
        parse_str(value)


@pytest.mark.parametrize("value,expected", [(None, None), (1, 2), (4.5, 5.5)])
def test_parse_optional(value, expected):
    assert parse_optional(value, lambda x: x + 1) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (5e9, pd.Timestamp(5e9, tz="UTC")),
        ("2021-01-01", pd.Timestamp("2021-01-01", tz="UTC")),
        (
            pd.Timestamp("2021-01-01", tz="Europe/Oslo"),
            pd.Timestamp("2021-01-01", tz="Europe/Oslo"),
        ),
    ],
)
def test_parse_time(value, expected):
    assert parse_time(value) == expected


@pytest.mark.parametrize("value", ["a9cbdf2c-78a4-4e12-a3be-80082c8b8138"])
def test_parse_uuid(value):
    assert parse_uuid(value) == value


@pytest.mark.parametrize("value", ["acd4"])
def test_parse_uuid__invalid_input__should_raise(value):
    with pytest.raises(ValueError):
        parse_uuid(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("a9cbdf2c-78a4-4e12-a3be-80082c8b8138", True),
        (["a9cbdf2c-78a4-4e12-a3be-80082c8b8138"], False),
        ("acd4", False),
        (12342, False),
        (True, False),
    ],
)
def test_is_valid_uuid(value, expected):
    assert is_valid_uuid(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("fiberOpticalPathId", "fiber_optical_path_id"),
        ("StartTime", "start_time"),
        ("", ""),
    ],
)
def test_to_snake_case(value, expected):
    assert to_snake_case(value) == expected
