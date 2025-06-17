"""Utility functions for authentication and credential caching."""

import logging
import os
from pathlib import Path
from typing import List

from types import TracebackType
from typing import Any, ClassVar, Self

from azure.identity import (
    AuthenticationRecord,
    ClientSecretCredential,
    DeviceCodeCredential,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
)

from azure.identity.aio import DefaultAzureCredential

from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential


logger = logging.getLogger("fiberoptics.common")


def get_preferred_credential_type():
    use_browser_credentials = os.getenv("USE_BROWSER_CREDENTIALS", "false").lower() == "true"

    if use_browser_credentials:
        return InteractiveBrowserCredential
    else:
        return DeviceCodeCredential


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

    def __init__(self, name: str):
        allow_unencrypted_storage = os.getenv("ALLOW_UNENCRYPTED_STORAGE", "false").lower() == "true"
        self.persistence_options = TokenCachePersistenceOptions(
            name=name,
            allow_unencrypted_storage=allow_unencrypted_storage,
        )
        # This is where the session information is stored
        self.authentication_record_filepath = Path.home() / ".authentication-records" / self.persistence_options.name
        # This is where the actual credentials are stored
        self.identity_service_filepath = Path.home() / ".IdentityService" / self.persistence_options.name

    def get_cached_credential(self):
        """Retrieves a cached credential object if it exists."""
        authentication_record = self.read_authentication_record()

        if not authentication_record or not self.is_cache_available():
            return None

        return get_preferred_credential_type()(
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
            get_preferred_credential_type()(cache_persistence_options=self.persistence_options)
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
    credential.get_token = lambda *args, **kwargs: type(credential).get_token(credential, *(args or scopes), **kwargs)


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
        CredentialType = get_preferred_credential_type()

        if cache and cache.is_cache_available():
            authentication_record = cache.read_authentication_record()

            if authentication_record:
                logger.info(
                    f"Reusing cached credentials from \
{cache.authentication_record_filepath}..."
                )
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


class NoCredentialsAvailable(Exception):
    pass


class Credential(AsyncTokenCredential):
    _credential: DefaultAzureCredential | None = None
    _instances: ClassVar[dict[str | None, Self]] = {}

    def __new__(cls, resource_id: str | None = None):
        if resource_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[resource_id] = instance
        return cls._instances[resource_id]

    def __init__(self, resource_id: str | None = None):
        if not hasattr(self, "initialized"):
            self.scope = f"{resource_id}/.default" if resource_id else None
            self.initialized = True

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        return await Credential.get_credential().get_token(*[*([self.scope] if len(scopes) == 0 else []), *scopes], **kwargs)

    @classmethod
    def get_credential(cls) -> DefaultAzureCredential:
        if cls._credential is None:
            options = {
                "exclude_developer_cli_credential": True,
                "exclude_environment_credential": True,
                "exclude_powershell_credential": True,
                "exclude_visual_studio_code_credential": True,
                "exclude_interactive_browser_credential": True,
            }
            cls._credential = DefaultAzureCredential(**options)
            if not cls._credential:
                raise NoCredentialsAvailable("No credentials are available")

        return cls._credential

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> AsyncTokenCredential:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None = None,
        _exc_value: BaseException | None = None,
        _traceback: TracebackType | None = None,
    ) -> None:
        pass
