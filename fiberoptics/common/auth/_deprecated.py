import logging

from fiberoptics.common.auth._sync import Credential


logger = logging.getLogger("fiberoptics.common")


def get_default_credential(name: str = None, scopes: list[str] | None = None, **kwargs):
    """Retrieves default credential.
    Deprecated: get_default_credential is deprecated and will be removed in future versions. Use AsyncCredential or Credential classes directly.
    """
    logger.warning(
        "Deprecated: get_default_credential is deprecated and will be removed in future versions. \
                   Use AsyncCredential or Credential classes directly."
    )

    if scopes is None:
        scopes = []

    if "tenant_id" not in kwargs:
        # This is not a secret and can be found on https://www.whatismytenantid.com/
        kwargs["tenant_id"] = "3aa4a235-b6e2-48d5-9195-7fcf05b459b0"

    return Credential(*scopes, **kwargs)
