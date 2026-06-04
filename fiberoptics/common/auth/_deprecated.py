import logging
import warnings

from fiberoptics.common.auth._sync import Credential


logger = logging.getLogger("fiberoptics.common")


def get_default_credential(scopes: list[str] | None = None, **kwargs):
    """Retrieves default credential.

    .. deprecated::
        Use :class:`Credential` or :class:`AsyncCredential` directly.
    """
    warnings.warn(
        "get_default_credential is deprecated and will be removed in a future version. "
        "Use Credential or AsyncCredential directly.",
        DeprecationWarning,
        stacklevel=2,
    )

    resource_id = scopes[0] if scopes else None
    return Credential(resource_id=resource_id, **kwargs)
