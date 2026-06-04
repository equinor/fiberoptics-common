"""Async credential implementation."""

from __future__ import annotations

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
from ._browser import AsyncInteractiveBrowserCredential


class AsyncCredential(BaseCredential, AsyncTokenCredential):
    def __init__(self, resource_id: str | None = None, **kwargs: Any):
        super().__init__(resource_id, **kwargs)

    async def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        scopes_tuple = self.build_scopes_tuple(scopes)
        cached = self.get_cached_token(scopes_tuple, kwargs)
        if cached:
            return cached

        token = await self.credential.get_token(*scopes_tuple, **kwargs)
        self.store_cached_token(scopes_tuple, kwargs, token)
        return token

    def build_credential(self) -> AsyncChainedTokenCredential:
        return self._build_credential_chain(
            chain_type=AsyncChainedTokenCredential,
            browser_cls=AsyncInteractiveBrowserCredential,
            credential_types=(AsyncWorkloadIdentityCredential, AsyncManagedIdentityCredential, AsyncAzureCliCredential),
        )
