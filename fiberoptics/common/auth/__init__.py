"""Utility functions for authentication and credential caching."""
import os
from pathlib import Path
from typing import List

from azure.identity import (
    AuthenticationRecord,
    ClientSecretCredential,
    DeviceCodeCredential,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
)


class CredentialCache:
    """Convenience class to facility credential caching.

    Credential caching is achieved by writing two files to disk:
    - An authentication record containing session information
    - An identity service file containing the actual credentials

    The authentication record contains no secrets and is stored in plaintext,
    but the identity service file on the other hand contains secrets and should
    be encrypted when storing it in the filesystem.

    Encryption is however not supported in headless sessions, e.g. when using
    the Kubeflow server. The only way to cache credentials on Kubeflow is by
    setting the 'ALLOW_UNENCRYPTED_STORAGE' environment variable to 'true'.
    Note that this will store secrets in plaintext, and should only be used
    if you know what you're doing.

    """

    use_browser_credentials: bool

    def __init__(self, name: str):
        self.use_browser_credentials = (
            os.getenv("USE_BROWSER_CREDENTIALS", "false").lower() == "true"
        )
        allow_unencrypted_storage = (
            os.getenv("ALLOW_UNENCRYPTED_STORAGE", "false").lower() == "true"
        )
        self.persistence_options = TokenCachePersistenceOptions(
            name=name,
            allow_unencrypted_storage=allow_unencrypted_storage,
        )
        # This is where the session information is stored
        self.authentication_record_filepath = (
            Path.home() / ".authentication-records" / self.persistence_options.name
        )
        # This is where the actual credentials are stored
        self.identity_service_filepath = (
            Path.home() / ".IdentityService" / self.persistence_options.name
        )

    def get_credential_type(self):
        if self.use_browser_credentials:
            return InteractiveBrowserCredential
        else:
            return DeviceCodeCredential

    def get_cached_credential(self):
        """Retrieves a cached credential object if it exists."""
        authentication_record = self.read_authentication_record()

        if not authentication_record or not self.is_cache_available():
            return None

        return self.get_credential_type()(
            authentication_record=authentication_record,
            cache_persistence_options=self.persistence_options,
        )

    def remove_cached_credential(self):
        """Removes a cached credential object if it exists."""
        os.remove(self.authentication_record_filepath)
        os.remove(self.identity_service_filepath)

    def is_cache_available(self):
        """Checks whether caching is currently supported."""
        try:
            self.get_credential_type()(
                cache_persistence_options=self.persistence_options
            )
            return True
        except ValueError as e:
            return not str(e).startswith("Cache encryption is impossible")

    def read_authentication_record(self):
        """Read an authentication record from file."""
        try:
            with open(self.authentication_record_filepath, "r") as f:
                return AuthenticationRecord.deserialize(f.read())
        except FileNotFoundError:
            return None

    def write_authentication_record(self, authentication_record: AuthenticationRecord):
        """Write an authentication record to file."""
        os.makedirs(self.authentication_record_filepath.parent, exist_ok=True)
        with open(self.authentication_record_filepath, "w") as f:
            f.write(authentication_record.serialize())


def add_default_scopes(credential: DeviceCodeCredential, scopes: List[str]):
    """Add default scopes to use when fetching tokens.

    This method overrides `credential.get_token` to use `scopes` when the get token
    method is called without any arguments. Normally, calling `get_token` without
    arguments will fail, since at least one scope is required.

    Parameters
    ----------
    credential : DeviceCodeCredential
        The credential to modify.
    scopes : list, of type str
        The list of scopes to use by default.

    Returns
    -------
    None
        The credential is modified in place.

    """
    credential.get_token = lambda *args, **kwargs: type(credential).get_token(
        credential, *(args or scopes), **kwargs
    )


def get_default_credential(name: str = None, scopes: List[str] = [], **kwargs):
    """Retrieves default credential (using cache if available).

    Parameters
    ----------
    name : str, optional
        Name of the cache, used to isolate credentials for different clients.
        Caching is disabled if no name is given.
    scopes : list, of type str, optional
        The scopes used to authenticate the credential.
        This argument is added as a default to the `get_token` method.
    kwargs : dict, optional
        Keyword arguments passed to the credential constructors.
        If `client_secret` is present, the `ClientSecretCredential` is used. Otherwise,
        the `DeviceCodeCredential` is used.

    """
    if "tenant_id" not in kwargs:
        # This is not a secret and can be found on https://www.whatismytenantid.com/
        kwargs["tenant_id"] = "3aa4a235-b6e2-48d5-9195-7fcf05b459b0"

    # Should handle kwargs containing `client_secret=None`
    if kwargs.get("client_secret") is not None:
        credential = ClientSecretCredential(**kwargs)
    else:
        cache = CredentialCache(name) if name else None

        if cache and cache.is_cache_available():
            authentication_record = cache.read_authentication_record()

            CredentialType = cache.get_credential_type()

            if authentication_record:
                # Retrieve cached credentials
                credential = CredentialType(
                    authentication_record=authentication_record,
                    cache_persistence_options=cache.persistence_options,
                )
            else:
                # Instantiate credentials with cache options
                credential = CredentialType(
                    **kwargs,
                    cache_persistence_options=cache.persistence_options,
                )
                authentication_record = credential.authenticate(scopes=scopes)
                cache.write_authentication_record(authentication_record)
        else:
            credential = CredentialType(**kwargs)
            # Prompt the user for a device code immediately
            credential.authenticate(scopes=scopes)

    if len(scopes):
        add_default_scopes(credential, scopes)

    return credential


def get_cached_credential(name: str, scopes: List[str] = []):
    """Retrieves cached credential if there is one.

    Parameters
    ----------
    name : str
        Name of the cache, used to isolate credentials for different clients.
    scopes : list, of type str, optional
        Scopes to use by default in `get_token`.

    Returns
    -------
    DeviceCodeCredential or None
        None is returned if no cached credential is found or if caching is not
        possible due to lack of encyption support.

    """
    credential = CredentialCache(name).get_cached_credential()

    if credential and len(scopes):
        add_default_scopes(credential, scopes)

    return credential


def remove_cached_credential(name: str):
    """Removes cached credential by name.

    Parameters
    ----------
    name : str
        Name of previously cached credential.

    """
    CredentialCache(name).remove_cached_credential()
