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


ChainedTokenCredentialAlias: TypeAlias = ChainedTokenCredential | AsyncChainedTokenCredential


logger = logging.getLogger("fiberoptics.common")


def _get_token_cache_persistence_options() -> TokenCachePersistenceOptions:
    """
    Returns token cache persistence options.

    Returns
    -------
    TokenCachePersistenceOptions
        Configuration for token cache persistence.
    """
    allow_unencrypted = os.environ.get("ALLOW_UNENCRYPTED_STORAGE", "false").lower() == "true"

    options = TokenCachePersistenceOptions(
        name="fiberoptics-common",
        allow_unencrypted_storage=allow_unencrypted,
    )

    if allow_unencrypted:
        logger.warning(
            "Unencrypted storage of token cache has been enabled. "
            "It is your responsibility to safeguard the cache and decommission it when no longer needed."
        )

    return options


def _get_authentication_record_path(resource_id: str | None = None) -> Path:
    """
    Returns the path to the authentication record file.

    Parameters
    ----------
    resource_id : str | None
        Optional resource ID to create a unique authentication record per resource.

    Returns
    -------
    Path
        Path to the authentication record file.
    """
    home = Path.home()
    cache_dir = home / ".azure" / "fiberoptics-common"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a safe filename from resource_id
    if resource_id:
        # Replace non-filesystem-safe characters with underscores
        safe_resource_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in resource_id)
        filename = f"authentication-record-{safe_resource_id}.json"
    else:
        filename = "authentication-record-default.json"
    
    return cache_dir / filename


def _load_authentication_record(resource_id: str | None = None) -> AuthenticationRecord | None:
    """
    Loads the authentication record from disk if it exists.

    Parameters
    ----------
    resource_id : str | None
        Optional resource ID to load the corresponding authentication record.

    Returns
    -------
    AuthenticationRecord | None
        The loaded authentication record, or None if not found.
    """
    path = _get_authentication_record_path(resource_id)
    if not path.exists():
        return None

    try:
        with open(path, "r") as f:
            return AuthenticationRecord.deserialize(f.read())
    except Exception as e:
        logger.debug(f"Failed to load authentication record: {e}")
        return None


def _save_authentication_record(record: AuthenticationRecord, resource_id: str | None = None) -> None:
    """
    Saves the authentication record to disk.

    Parameters
    ----------
    record : AuthenticationRecord
        The authentication record to save.
    resource_id : str | None
        Optional resource ID to save the authentication record for a specific resource.
    """
    path = _get_authentication_record_path(resource_id)
    try:
        with open(path, "w") as f:
            f.write(record.serialize())
    except Exception as e:
        logger.warning(f"Failed to save authentication record: {e}")


def _use_browser_credentials() -> bool:
    """
    Checks if browser credentials should be used.

    Returns
    -------
    bool
        True if USE_BROWSER_CREDENTIALS environment variable is set to true.
    """
    return os.environ.get("USE_BROWSER_CREDENTIALS", "false").lower() == "true"


def _get_browser_credential_config() -> dict[str, Any]:
    """
    Returns configuration for browser credential.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary with client_id, tenant_id, and redirect_uri.
    """
    return {
        "client_id": os.environ.get("AZURE_CLIENT_ID", os.environ.get("sp_client_id")),
        "tenant_id": os.environ.get("AZURE_TENANT_ID", os.environ.get("azure_tenant_id")),
        "redirect_uri": os.environ.get("REDIRECT_URI", "http://localhost:4000"),
    }


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
    _resource_id : ClassVar[str | None]
        The resource ID used for building credentials (specific to each subclass).
    """

    _credential: ClassVar[ChainedTokenCredential | AsyncChainedTokenCredential | None] = None
    _instances: ClassVar[dict[str | None, Self]] = {}
    _azure_cli_access_tokens: ClassVar[dict[tuple[str, ...], AccessToken]] = {}
    _cache_skew: ClassVar[int] = 300
    _resource_id: ClassVar[str | None] = None

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
            # Store resource_id at class level for this singleton instance
            cls._resource_id = resource_id
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

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Initializes subclass-specific class variables to ensure cache isolation.

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments passed to the superclass.
        """
        super().__init_subclass__(**kwargs)
        cls._credential = None
        cls._instances = {}
        cls._azure_cli_access_tokens = {}
        cls._resource_id = None

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
        credential : ChainedTokenCredential | AsyncChainedTokenCredential
            The chained credential instance.
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

    def _store_cached_token(
        self, credential: ChainedTokenCredentialAlias, scopes_tuple: tuple[Any, ...], token: AccessToken
    ) -> None:
        """
        Caches the token if the successful credential is Azure CLI.

        Parameters
        ----------
        credential : ChainedTokenCredential | AsyncChainedTokenCredential
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
    def _cli_credential_type(cls) -> type[AzureCliCredential] | type[AsyncAzureCliCredential]:
        ...

    @classmethod
    def _build_browser_credential(cls) -> InteractiveBrowserCredential:
        """
        Builds a browser credential with authentication record if available.

        Returns
        -------
        InteractiveBrowserCredential
            The browser credential instance.
        """
        config = _get_browser_credential_config()

        if not config["client_id"] or not config["tenant_id"]:
            raise RuntimeError(
                "Browser credentials require AZURE_CLIENT_ID and AZURE_TENANT_ID environment variables"
            )

        auth_record = _load_authentication_record(cls._resource_id)
        cache_options = _get_token_cache_persistence_options()

        kwargs = {
            "client_id": config["client_id"],
            "tenant_id": config["tenant_id"],
            "redirect_uri": config["redirect_uri"],
            "cache_persistence_options": cache_options,
        }

        if auth_record:
            kwargs["authentication_record"] = auth_record

        credential = InteractiveBrowserCredential(**kwargs)

        # If no auth record exists, authenticate now and save it
        if not auth_record and hasattr(credential, "authenticate"):
            try:
                # Use resource_id scope if available, otherwise default scope
                scopes = [f"{cls._resource_id}/.default"] if cls._resource_id else []
                new_record = credential.authenticate(scopes=scopes)
                _save_authentication_record(new_record, cls._resource_id)
            except Exception as e:
                logger.warning(f"Failed to authenticate and save record: {e}")

        return credential


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
        1. Interactive Browser (if USE_BROWSER_CREDENTIALS=true)
        2. Azure CLI
        3. Workload Identity
        4. Managed Identity

        Returns
        -------
        azure.identity.aio.ChainedTokenCredential
            The credential instance with the configured chain.

        Raises
        ------
        RuntimeError
            If no credentials could be instantiated.
        """
        credentials = []

        # Add browser credential if enabled
        if _use_browser_credentials():
            try:
                credentials.append(cls._build_browser_credential())
            except Exception as e:
                logger.debug(f"Failed to instantiate browser credential: {e}")

        # Try credentials in a specific order: Azure CLI → Workload Identity → Managed Identity
        credential_types = [
            AsyncAzureCliCredential,
            AsyncWorkloadIdentityCredential,
            AsyncManagedIdentityCredential,
        ]

        for credential_type in credential_types:
            try:
                credentials.append(credential_type())
            except Exception as e:
                logger.debug(f"Failed to instantiate {credential_type.__name__}: {e}")

        if not credentials:
            raise RuntimeError("No Azure credentials could be instantiated")

        return AsyncChainedTokenCredential(*credentials)

    @classmethod
    def _cli_credential_type(cls) -> type[AsyncAzureCliCredential]:
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
    def _build_credential(cls) -> ChainedTokenCredential:
        """
        Returns the cached credential chain instance, creating it if necessary.

        The credential chain attempts authentication in the following order:
        1. Interactive Browser (if USE_BROWSER_CREDENTIALS=true)
        2. Azure CLI
        3. Workload Identity
        4. Managed Identity

        Returns
        -------
        ChainedTokenCredential
            The credential instance with the configured chain.

        Raises
        ------
        RuntimeError
            If no credentials could be instantiated.
        """
        credentials = []

        # Add browser credential if enabled
        if _use_browser_credentials():
            try:
                credentials.append(cls._build_browser_credential())
            except Exception as e:
                logger.debug(f"Failed to instantiate browser credential: {e}")

        # # Add DefaultAzureCredential with selected flows excluded
        # try:
        #     options = {
        #         "exclude_developer_cli_credential": True,
        #         "exclude_environment_credential": True,
        #         "exclude_powershell_credential": True,
        #         "exclude_visual_studio_code_credential": True,
        #         "exclude_interactive_browser_credential": True,
        #     }
        #     credentials.append(DefaultAzureCredential(**options))
        # except Exception as e:
        #     logger.debug(f"Failed to instantiate DefaultAzureCredential: {e}")

        if not credentials:
            raise RuntimeError("No Azure credentials could be instantiated")

        return ChainedTokenCredential(*credentials)

    @classmethod
    def _cli_credential_type(cls) -> type[AzureCliCredential]:
        return AzureCliCredential
