"""Utility functions for authentication and credential caching."""

import logging
import os
from pathlib import Path
import time

from abc import ABC, abstractmethod

from typing import Any, ClassVar, TypeAlias

from azure.identity import (
    AuthenticationRecord,
    AzureCliCredential,
    DefaultAzureCredential,
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


def _create_browser_credential(
    *,
    resource_id: str | None,
    scope: str | None,
    persist_auth_record: bool,
) -> Any:
    config = _get_browser_credential_config()
    if not config["client_id"] or not config["tenant_id"]:
        raise RuntimeError("Browser credentials require AZURE_CLIENT_ID and AZURE_TENANT_ID environment variables")

    auth_record = _load_authentication_record(resource_id)
    cache_options = _get_token_cache_persistence_options()

    kwargs: dict[str, Any] = {
        "client_id": config["client_id"],
        "tenant_id": config["tenant_id"],
        "redirect_uri": config["redirect_uri"],
        "cache_persistence_options": cache_options,
    }
    if auth_record:
        kwargs["authentication_record"] = auth_record

    credential = InteractiveBrowserCredential(**kwargs)

    if persist_auth_record and not auth_record and hasattr(credential, "authenticate"):
        try:
            preferred_scope = [scope] if scope else None
            new_record = credential.authenticate(scopes=preferred_scope)
            _save_authentication_record(new_record, resource_id)
        except BaseException as exc:
            logger.warning(f"Failed to authenticate and save record: {exc}")

    return credential


class _BaseCredential(ABC):
    """
    Base class for Azure credential implementations providing shared caching logic.
    """

    _cache_skew: ClassVar[int] = 300

    def __init__(self, resource_id: str | None = None):
        """
        Initializes the credential instance.

        Parameters
        ----------
        resource_id : str | None
            The resource ID to use for scoping the token, if provided.
        """
        self.resource_id = resource_id
        self.scope = f"{resource_id}/.default" if resource_id else None
        self._azure_cli_access_tokens: dict[tuple[str, ...], AccessToken] = {}
        self._credential = self._build_credential()

    @property
    def credential(self) -> ChainedTokenCredentialAlias:
        return self._credential

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

    def _get_cached_token(self, scopes_tuple: tuple[str, ...]) -> AccessToken | None:
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
        successful = getattr(self.credential, "_successful_credential", None)
        if successful and isinstance(successful, (AzureCliCredential, AsyncAzureCliCredential)):
            token = self._azure_cli_access_tokens.get(scopes_tuple)
            if token is not None and int(time.time()) < token.expires_on - self._cache_skew:
                return token
        return None

    def _store_cached_token(self, scopes_tuple: tuple[Any, ...], token: AccessToken) -> None:
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
        successful = getattr(self.credential, "_successful_credential", None)
        if successful and isinstance(successful, (AzureCliCredential, AsyncAzureCliCredential)):
            self._azure_cli_access_tokens[scopes_tuple] = token

    @abstractmethod
    def _build_credential(self) -> ChainedTokenCredentialAlias:
        ...


class AsyncCredential(_BaseCredential, AsyncTokenCredential):
    """
    Azure credential class supporting async authentication. For the sync version, see Credential.

    This class provides a credential instance, using a chained credential that tries 
    Azure CLI, Workload Identity, Managed Identity and optionally Interactive Browser flow.
    It implements the async TokenCredential protocol for use with Azure SDK clients.
    """

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        scopes_tuple = self._build_scopes_tuple(scopes)
        cached = self._get_cached_token(scopes_tuple)
        if cached:
            return cached

        token = await self.credential.get_token(*scopes_tuple, **kwargs)
        self._store_cached_token(scopes_tuple, token)
        return token

    def _build_credential(self) -> AsyncChainedTokenCredential:
        credentials: list[AsyncTokenCredential] = []

        if _use_browser_credentials():
            try:
                credentials.append(
                    _create_browser_credential(
                        resource_id=self.resource_id,
                        scope=self.scope,
                        persist_auth_record=False,
                    )
                )
            except BaseException as exc:
                logger.debug(f"Failed to instantiate browser credential: {exc}")

        for credential_type in (
            AsyncAzureCliCredential,
            AsyncWorkloadIdentityCredential,
            AsyncManagedIdentityCredential,
        ):
            try:
                credentials.append(credential_type())
            except BaseException as exc:
                logger.debug(f"Failed to instantiate {credential_type.__name__}: {exc}")

        if not credentials:
            raise RuntimeError("No Azure credentials could be instantiated")

        return AsyncChainedTokenCredential(*credentials)


class Credential(_BaseCredential, TokenCredential):
    """
    Azure credential class supporting sync authentication. For the async version, see AsyncCredential.

    This class provides a credential instance, using a chained credential that tries 
    Azure CLI, Workload Identity, Managed Identity and optionally Interactive Browser flow.
    It implements the sync TokenCredential protocol for use with Azure SDK clients.
    """

    def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        scopes_tuple = self._build_scopes_tuple(scopes)
        cached = self._get_cached_token(scopes_tuple)
        if cached:
            return cached

        token = self.credential.get_token(*scopes_tuple, **kwargs)
        self._store_cached_token(scopes_tuple, token)
        return token

    def _build_credential(self) -> ChainedTokenCredential:
        credentials: list[TokenCredential] = []

        if _use_browser_credentials():
            try:
                credentials.append(
                    _create_browser_credential(
                        resource_id=self.resource_id,
                        scope=self.scope,
                        persist_auth_record=True,
                    )
                )
            except BaseException as exc:
                logger.debug(f"Failed to instantiate browser credential: {exc}")

        try:
            options = {
                "exclude_developer_cli_credential": True,
                "exclude_environment_credential": True,
                "exclude_powershell_credential": True,
                "exclude_visual_studio_code_credential": True,
                "exclude_interactive_browser_credential": True,
            }
            credentials.append(DefaultAzureCredential(**options))
        except BaseException as exc:
            logger.debug(f"Failed to instantiate DefaultAzureCredential: {exc}")

        if not credentials:
            raise RuntimeError("No Azure credentials could be instantiated")

        return ChainedTokenCredential(*credentials)
