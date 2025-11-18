import logging

from fiberoptics.common.auth._sync import Credential


logger = logging.getLogger("fiberoptics.common")


def get_default_credential(name: str = None, scopes: list[str] = [], **kwargs):
    """Retrieves default credential.
    Deprecated: get_default_credential is deprecated and will be removed in future versions. Use AsyncCredential or Credential classes directly.
    """
    logger.warning(
        "Deprecated: get_preferred_credential_type is deprecated and will be removed in future versions. \
                   Use AsyncCredential or Credential classes directly."
    )

    if "tenant_id" not in kwargs:
        # This is not a secret and can be found on https://www.whatismytenantid.com/
        kwargs["tenant_id"] = "3aa4a235-b6e2-48d5-9195-7fcf05b459b0"

    return Credential(*scopes, **kwargs)


# def get_default_credential():

#     return Credential
