"""Async credential implementation."""

from __future__ import annotations

import logging
from typing import Any

from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import (
    AzureCliCredential as AsyncAzureCliCredential,
    ChainedTokenCredential as AsyncChainedTokenCredential,
    ManagedIdentityCredential as AsyncManagedIdentityCredential,
    WorkloadIdentityCredential as AsyncWorkloadIdentityCredential,
)

from ._base import BaseCredential
from ._browser import AsyncInteractiveBrowserCredential, use_browser_credentials

logger = logging.getLogger("fiberoptics.common")


class AsyncCredential(BaseCredential, AsyncTokenCredential):
    def __init__(self, resource_id: str | None = None, **kwargs: Any):
        super().__init__(resource_id, **kwargs)

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        scopes_tuple = self.build_scopes_tuple(scopes)
        cached = self.get_cached_token(scopes_tuple)
        if cached:
            return cached

        token = await self.credential.get_token(*scopes_tuple, **kwargs)
        self.store_cached_token(scopes_tuple, token)
        return token

    def build_credential(self) -> AsyncChainedTokenCredential:
        credentials: list[AsyncTokenCredential] = []

        if use_browser_credentials():
            try:
                browser_kwargs = self.get_browser_kwargs()
                credentials.append(
                    AsyncInteractiveBrowserCredential(
                        resource_id=self.resource_id,
                        scope=self.scope,
                        persist_auth_record=True,
                        **browser_kwargs,
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
