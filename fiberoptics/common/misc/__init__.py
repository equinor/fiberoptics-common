"""Collection of miscellaneous dependency-free functionality."""

from . import Parser
from ._interval import (
    add_interval,
    combine_continuous_intervals,
    deserialize_interval_index,
    find_continuous_intervals,
    serialize_interval_index,
    subtract_interval,
    with_interval_cache,
)
from ._version import SemanticVersion
