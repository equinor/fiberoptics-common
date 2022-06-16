import pandas as pd
import pytest

from fiberoptics.common._parsing import (
    is_valid_uuid,
    parse_bool,
    parse_optional,
    parse_time,
    parse_uuid,
    to_snake_case,
)


@pytest.mark.parametrize("value", [True, False])
def test_parse_bool(value):
    assert parse_bool(value) == value


@pytest.mark.parametrize("value", ["True", 1, "", 0])
def test_parse_bool__invalid_input__should_raise(value):
    with pytest.raises(ValueError):
        parse_bool(value)


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
