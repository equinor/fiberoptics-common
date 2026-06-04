"""Private browser credential helpers."""

from __future__ import annotations

import asyncio
import logging
import os
from functools import partial
from pathlib import Path
from typing import Any

from azure.core.credentials import AccessToken, TokenCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity import (
    AuthenticationRecord,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
)

logger = logging.getLogger("fiberoptics.common")


def get_token_cache_persistence_options() -> TokenCachePersistenceOptions:
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


def get_authentication_record_path(resource_id: str | None = None) -> Path:
    home = Path.home()
    cache_dir = home / ".azure" / "fiberoptics-common"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if resource_id:
        safe_resource_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in resource_id)
        filename = f"authentication-record-{safe_resource_id}.json"
    else:
        filename = "authentication-record-default.json"

    return cache_dir / filename


def load_authentication_record(resource_id: str | None = None) -> AuthenticationRecord | None:
    path = get_authentication_record_path(resource_id)
    if not path.exists():
        return None

    try:
        with open(path, "r") as fh:
            return AuthenticationRecord.deserialize(fh.read())
    except Exception as exc:
        logger.debug(f"Failed to load authentication record: {exc}")
        return None


def save_authentication_record(record: AuthenticationRecord, resource_id: str | None = None) -> None:
    path = get_authentication_record_path(resource_id)
    try:
        with open(path, "w") as fh:
            fh.write(record.serialize())
    except Exception as exc:
        logger.warning(f"Failed to save authentication record: {exc}")


def use_browser_credentials() -> bool:
    return os.environ.get("USE_BROWSER_CREDENTIALS", "false").lower() == "true"


def _build_credential(
    resource_id: str | None,
    scope: str | None,
    persist_auth_record: bool,
    client_id: str | None = None,
    tenant_id: str | None = None,
    redirect_uri: str | None = None,
) -> InteractiveBrowserCredential:
    """Build an InteractiveBrowserCredential, optionally persisting the auth record.

    Reads client_id, tenant_id, redirect_uri from env vars when not provided.
    """
    resolved_client_id = client_id or os.environ.get("AZURE_CLIENT_ID") or os.environ.get("sp_client_id")
    resolved_tenant_id = tenant_id or os.environ.get("AZURE_TENANT_ID") or os.environ.get("azure_tenant_id")
    resolved_redirect_uri = redirect_uri or os.environ.get("REDIRECT_URI", "http://localhost:4000")

    if not resolved_client_id or not resolved_tenant_id:
        raise RuntimeError(
            "Browser credentials require both client_id and tenant_id, which can be provided either "
            "via environment variables (AZURE_CLIENT_ID or sp_client_id and AZURE_TENANT_ID or "
            "azure_tenant_id) or as constructor parameters."
        )

    auth_record = load_authentication_record(resource_id)

    kwargs: dict[str, Any] = {
        "client_id": resolved_client_id,
        "tenant_id": resolved_tenant_id,
        "redirect_uri": resolved_redirect_uri,
        "cache_persistence_options": get_token_cache_persistence_options(),
    }
    if auth_record:
        kwargs["authentication_record"] = auth_record

    credential = InteractiveBrowserCredential(**kwargs)

    if persist_auth_record and not auth_record:
        try:
            new_record = credential.authenticate(scopes=[scope] if scope else None)
            save_authentication_record(new_record, resource_id)
        except Exception as exc:
            logger.warning(f"Failed to authenticate and save record: {exc}")

    return credential


class SyncInteractiveBrowserCredential(TokenCredential):
    def __init__(
        self,
        *,
        resource_id: str | None,
        scope: str | None,
        persist_auth_record: bool,
        client_id: str | None = None,
        tenant_id: str | None = None,
        redirect_uri: str | None = None,
    ):
        self._credential = _build_credential(
            resource_id, scope, persist_auth_record, client_id, tenant_id, redirect_uri
        )

    def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        return self._credential.get_token(*scopes, **kwargs)


class AsyncInteractiveBrowserCredential(AsyncTokenCredential):
    def __init__(
        self,
        *,
        resource_id: str | None,
        scope: str | None,
        persist_auth_record: bool,
        client_id: str | None = None,
        tenant_id: str | None = None,
        redirect_uri: str | None = None,
    ):
        self._credential = _build_credential(
            resource_id, scope, persist_auth_record, client_id, tenant_id, redirect_uri
        )

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._credential.get_token, *scopes, **kwargs))
