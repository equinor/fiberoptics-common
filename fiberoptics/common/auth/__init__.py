"""Utility functions for authentication and credential caching."""

import logging
import os
from pathlib import Path
import time
from typing import List

from abc import ABC, abstractmethod

from typing import Any, ClassVar, Self, TypeAlias

from azure.identity import (
    AuthenticationRecord,
    AzureCliCredential,
    ClientSecretCredential,
    DefaultAzureCredential,
    DeviceCodeCredential,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
    ChainedTokenCredential,
)

from azure.identity.aio import (
    AzureCliCredential as AsyncAzureCliCredential,
    ChainedTokenCredential as AsyncChainedTokenCredential,
    WorkloadIdentityCredential as AsyncWorkloadIdentityCredential,
    ManagedIdentityCredential as AsyncManagedIdentityCredential,
)

from azure.core.credentials import AccessToken, TokenCredential
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


class _BaseCredential(ABC):
    """
    Base class for Azure credential implementations providing shared singleton and caching logic.

    This class implements the singleton pattern per resource_id and provides shared
    token caching functionality for Azure CLI credentials.

    Attributes
    ----------
    _credential : ChainedTokenCredential | AsyncChainedTokenCredential | None
        Cached credential instance (specific to each subclass).
    _instances : ClassVar[dict[str | None, Self]]
        Dictionary of singleton instances keyed by resource_id.
    _azure_cli_access_tokens : ClassVar[dict[tuple[str], AccessToken]]
        In-memory cache for Azure CLI access tokens, keyed by scopes tuple.
    """

    _credential: ClassVar[Any | None] = None
    _instances: ClassVar[dict[str | None, Self]] = {}
    _azure_cli_access_tokens: ClassVar[dict[tuple[str, ...], AccessToken]] = {}
    _cache_skew: ClassVar[int] = 300

    ChainedTokenCredentialAlias: TypeAlias = ChainedTokenCredential | AsyncChainedTokenCredential
    AzureCliCredentialAlias: TypeAlias = AzureCliCredential | AsyncAzureCliCredential

    def __new__(cls, resource_id: str | None = None):
        """
        Returns a singleton instance for the given resource_id.

        Parameters
        ----------
        resource_id : str | None
            The resource ID for which to create or retrieve the credential instance.

        Returns
        -------
        Self
            The singleton credential instance for the specified resource_id.
        """
        if resource_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[resource_id] = instance
        return cls._instances[resource_id]

    def __init__(self, resource_id: str | None = None):
        """
        Initializes the credential instance.

        Parameters
        ----------
        resource_id : str | None
            The resource ID to use for scoping the token, if provided.
        """
        if not hasattr(self, "initialized"):
            self.scope = f"{resource_id}/.default" if resource_id else None
            self.initialized = True

    def _build_scopes_tuple(self, scopes: tuple[Any, ...]) -> tuple[str, ...]:
        """
        Determines the appropriate scopes tuple to use for token retrieval.

        Parameters
        ----------
        scopes : tuple[Any, ...]
            The scopes provided to get_token.

        Returns
        -------
        tuple[str, ...]
            The scopes tuple to use, either the provided scopes or the default scope.
        """
        return tuple([self.scope] if len(scopes) == 0 and self.scope else scopes)

    def _get_cached_token(self, credential: ChainedTokenCredentialAlias, scopes_tuple: tuple[str, ...]) -> AccessToken | None:
        """
        Checks if a cached Azure CLI token should be used.

        The following code is required to optimize token retrieval when using Azure CLI credentials.
        See: https://github.com/Azure/azure-sdk-for-go/issues/23533#issuecomment-2387072175
        See: https://github.com/Azure/azure-sdk-for-python/issues/40636#issuecomment-2819608804
        Should be removed once the Azure SDK for Python supports caching of Azure CLI credentials.

        Parameters
        ----------
        credential : Any
            The chained credential instance.
        cli_credential_type : type
            The Azure CLI credential type to check against.
        scopes_tuple : tuple[str, ...]
            The scopes for which to check the cache.

        Returns
        -------
        AccessToken | None
            The cached token if available and valid, otherwise None.
        """

        cli_type = self._cli_credential_type()

        successful = getattr(credential, "_successful_credential", None)
        if cli_type and successful and isinstance(successful, cli_type):
            token = self._azure_cli_access_tokens.get(scopes_tuple)
            if token is not None and int(time.time()) < token.expires_on - self._cache_skew:
                return token
        return None

    def _store_cached_token(self, credential: ChainedTokenCredentialAlias, scopes_tuple: tuple[Any, ...], token: AccessToken) -> None:
        """
        Caches the token if the successful credential is Azure CLI.

        Parameters
        ----------
        credential : Any
            The chained credential instance.
        scopes_tuple : tuple[str, ...]
            The scopes for which to cache the token.
        token : AccessToken
            The token to cache.
        """
        cli_type = self._cli_credential_type()
        successful = getattr(credential, "_successful_credential", None)
        if cli_type and successful and isinstance(successful, cli_type):
            self._azure_cli_access_tokens[scopes_tuple] = token

    def _prepare_token_request(
        self, scopes: tuple[Any, ...]
    ) -> tuple[ChainedTokenCredentialAlias, tuple[str, ...], AccessToken | None]:
        credential = type(self).get_credential()
        scopes_tuple = self._build_scopes_tuple(scopes)
        return credential, scopes_tuple, self._get_cached_token(credential, scopes_tuple)

    def _finalize_token(
        self,
        credential: ChainedTokenCredentialAlias,
        scopes_tuple: tuple[str, ...],
        token: AccessToken,
    ) -> AccessToken:
        self._store_cached_token(credential, scopes_tuple, token)
        return token

    @classmethod
    def get_credential(cls) -> ChainedTokenCredentialAlias:
        return cls._ensure_credential()

    @classmethod
    def _ensure_credential(cls) -> ChainedTokenCredentialAlias:
        if cls._credential is None:
            cls._credential = cls._build_credential()
        return cls._credential

    @classmethod
    @abstractmethod
    def _build_credential(cls) -> ChainedTokenCredentialAlias:
        ...

    @classmethod
    @abstractmethod
    def _cli_credential_type(cls) -> AzureCliCredentialAlias:
        ...


class AsyncCredential(_BaseCredential, AsyncTokenCredential):
    """
    Azure credential class supporting async authentication. For the sync version, see Credential.

    This class provides a singleton credential instance per resource ID, using
    a chained credential that tries Azure CLI, Workload Identity, and Managed Identity
    in order. It implements the async TokenCredential protocol for use with Azure SDK clients.

    Methods
    -------
    async get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken
        Asynchronously acquires an access token for the specified scopes.
    @classmethod
    get_credential(cls) -> AsyncChainedTokenCredential
        Returns the cached AsyncChainedTokenCredential instance, creating it if necessary.
    """

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        """
        Asynchronously acquires an access token for the specified scopes.
        If the underlying credential is AzureCliCredential, applies in-memory caching.
        """
        credential, scopes_tuple, cached = self._prepare_token_request(scopes)
        if cached:
            return cached

        token = await credential.get_token(*scopes_tuple, **kwargs)
        return self._finalize_token(credential, scopes_tuple, token)

    @classmethod
    def _build_credential(cls) -> AsyncChainedTokenCredential:
        """
        Returns the cached azure.identity.aio.ChainedTokenCredential instance, creating it if necessary.

        The credential chain attempts authentication in the following order:
        1. Azure CLI
        2. Workload Identity
        3. Managed Identity

        Returns
        -------
        azure.identity.aio.ChainedTokenCredential
            The credential instance with the configured chain.

        Raises
        ------
        RuntimeError
            If no credentials could be instantiated.
        """
        # Try credentials in a specific order: Azure CLI → Workload Identity → Managed Identity
        # See: https://github.com/equinor/fiberoptics-common/issues/50
        credential_types = [
            AsyncAzureCliCredential,
            AsyncWorkloadIdentityCredential,
            AsyncManagedIdentityCredential,
        ]

        credentials = []
        for credential_type in credential_types:
            try:
                credentials.append(credential_type())
            except ValueError as e:
                logger.debug(f"Failed to instantiate {credential_type.__name__}: {e}")

        if not credentials:
            raise RuntimeError("No Azure credentials could be instantiated")

        return AsyncChainedTokenCredential(*credentials)

    @classmethod
    def _cli_credential_type(cls) -> AzureCliCredential:
        return AsyncAzureCliCredential


class Credential(_BaseCredential, TokenCredential):
    """
    Azure credential class supporting sync authentication. For the async version, see AsyncCredential.

    This class provides a singleton credential instance per resource ID, using
    a chained credential that tries Azure CLI, Workload Identity, and Managed Identity
    in order. It implements the sync TokenCredential protocol for use with Azure SDK clients.

    Methods
    -------
    get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken
        Synchronously acquires an access token for the specified scopes.
    @classmethod
    get_credential(cls) -> DefaultAzureCredential
        Returns the cached DefaultAzureCredential instance, creating it if necessary.
    """

    def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        """
        Synchronously acquires an access token for the specified scopes.
        If the underlying credential is AzureCliCredential, applies in-memory caching.
        """
        credential, scopes_tuple, cached = self._prepare_token_request(scopes)
        if cached:
            return cached

        token = credential.get_token(*scopes_tuple, **kwargs)
        return self._finalize_token(credential, scopes_tuple, token)

    @classmethod
    def _build_credential(cls) -> DefaultAzureCredential:
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
        options = {
            "exclude_developer_cli_credential": True,
            "exclude_environment_credential": True,
            "exclude_powershell_credential": True,
            "exclude_visual_studio_code_credential": True,
            "exclude_interactive_browser_credential": True,
        }
        return DefaultAzureCredential(**options)

    @classmethod
    def _cli_credential_type(cls) -> AzureCliCredential:
        return AzureCliCredential
