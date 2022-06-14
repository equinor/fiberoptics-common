import pytest

from fiberoptics.common._version import SemanticVersion


@pytest.mark.parametrize(
    "args,kwargs,expected",
    [
        ((1,), {}, (1, 0, 0)),
        ((1, 2), {}, (1, 2, 0)),
        ((1, 2, 3), {}, (1, 2, 3)),
        (("1.2.3",), {}, (1, 2, 3)),
        (((1, 2, 3),), {}, (1, 2, 3)),
        ((), dict(major=1), (1, 0, 0)),
        ((), dict(major=1, minor=2, patch=3), (1, 2, 3)),
        ((), dict(major=1, minor=2), (1, 2, 0)),
        ((), dict(major=1, patch=3), (1, 0, 3)),
    ],
)
def test_constructor__valid_input(args, kwargs, expected):
    assert SemanticVersion(*args, **kwargs) == expected


@pytest.mark.parametrize(
    "args,kwargs",
    [
        ((1, 2, 3, 4), {}),
        (("1",), {}),
        (("1.2",), {}),
        (("1.2.3a",), {}),
        (("1.2.3.4",), {}),
        (((1, 2),), {}),
        (((1, 2, 3, 4),), {}),
        ((1,), dict(major=2)),
    ],
)
def test_constructor__invalid_input(args, kwargs):
    with pytest.raises((TypeError, ValueError)):
        SemanticVersion(*args, **kwargs)
