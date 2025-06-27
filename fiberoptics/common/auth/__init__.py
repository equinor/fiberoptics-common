"""Utility functions for authentication and credential caching."""

import logging
import os
from pathlib import Path
import time
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

import azure.identity.aio

from azure.identity.aio import DefaultAzureCredential, AzureCliCredential

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


class Credential(AsyncTokenCredential):
    """
    Azure credential class supporting async authentication.

    This class provides a singleton credential instance per resource ID, using
    Azure's DefaultAzureCredential with selected flows excluded. It implements
    the async TokenCredential protocol for use with Azure SDK clients.

    Attributes
    ----------
    _credential : DefaultAzureCredential | None
        Cached credential instance.
    _instances : ClassVar[dict[str | None, Self]]
        Dictionary of singleton instances keyed by resource_id.
     _azure_cli_access_tokens : ClassVar[dict[tuple[str], AccessToken]]
        In-memory cache for Azure CLI access tokens, keyed by scopes tuple.

    Methods
    -------
    __new__(cls, resource_id: str | None = None)
        Returns a singleton instance for the given resource_id.
    __init__(self, resource_id: str | None = None)
        Initializes the credential with an optional resource_id.
    async get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken
        Asynchronously acquires an access token for the specified scopes.
    @classmethod
    get_credential(cls) -> DefaultAzureCredential
        Returns the cached DefaultAzureCredential instance, creating it if necessary.
    async close(self) -> None
        Placeholder for closing resources (no-op).
    async __aenter__(self) -> AsyncTokenCredential
        Async context manager entry.
    async __aexit__(self, _exc_type, _exc_value, _traceback) -> None
        Async context manager exit.
    """

    _credential: DefaultAzureCredential | None = None
    _instances: ClassVar[dict[str | None, Self]] = {}
    _azure_cli_access_tokens: ClassVar[dict[tuple[str], AccessToken]] = {}

    def __new__(cls, resource_id: str | None = None):
        """
        Returns a singleton instance of Credential for the given resource_id.

        Parameters
        ----------
        resource_id : str | None
            The resource ID for which to create or retrieve the credential instance.

        Returns
        -------
        Credential
            The singleton credential instance for the specified resource_id.
        """
        if resource_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[resource_id] = instance
        return cls._instances[resource_id]

    def __init__(self, resource_id: str | None = None):
        """
        Initializes the Credential instance.

        Parameters
        ----------
        resource_id : str | None
            The resource ID to use for scoping the token, if provided.
        """
        if not hasattr(self, "initialized"):
            self.scope = f"{resource_id}/.default" if resource_id else None
            self.initialized = True

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        """
        Asynchronously acquires an access token for the specified scopes.
        If the underlying credential is AzureCliCredential, applies in-memory caching.
        """
        credential = Credential.get_credential()
        scopes_tuple = tuple([self.scope] if len(scopes) == 0 and self.scope else scopes)

        # The following code is required to optimize token retrieval when using Azure CLI credentials.
        # See: https://github.com/Azure/azure-sdk-for-go/issues/23533#issuecomment-2387072175
        # Should be removed once the Azure SDK for Python supports caching of Azure CLI credentials.
        if isinstance(credential._successful_credential, AzureCliCredential):
            token = self._azure_cli_access_tokens.get(scopes_tuple, None)
            if token is not None and int(time.time()) < token.expires_on - 300:
                return token

        token = await credential.get_token(*scopes_tuple, **kwargs)

        if isinstance(credential._successful_credential, AzureCliCredential):
            self._azure_cli_access_tokens[scopes_tuple] = token

        return token

    @classmethod
    def get_credential(cls) -> DefaultAzureCredential:
        """
        Returns the cached DefaultAzureCredential instance, creating it if necessary.

        Returns
        -------
        DefaultAzureCredential
            The credential instance with selected flows excluded.

        Raises
        ------
        NoCredentialsAvailable
            If no credentials are available.
        """
        if cls._credential is None:
            options = {
                "exclude_developer_cli_credential": True,
                "exclude_environment_credential": True,
                "exclude_powershell_credential": True,
                "exclude_visual_studio_code_credential": True,
                "exclude_interactive_browser_credential": True,
            }
            cls._credential = DefaultAzureCredential(**options)

        return cls._credential

    async def close(self) -> None:
        """
        Placeholder for closing resources. No operation is performed.
        """
        pass

    async def __aenter__(self) -> AsyncTokenCredential:
        """
        Async context manager entry.

        Returns
        -------
        AsyncTokenCredential
            The credential instance itself.
        """
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None = None,
        _exc_value: BaseException | None = None,
        _traceback: TracebackType | None = None,
    ) -> None:
        """
        Async context manager exit. No operation is performed.

        Parameters
        ----------
        _exc_type : type[BaseException] | None
            Exception type, if any.
        _exc_value : BaseException | None
            Exception value, if any.
        _traceback : TracebackType | None
            Traceback, if any.
        """
        pass
