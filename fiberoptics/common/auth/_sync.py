"""Sync credential implementation."""

from __future__ import annotations

from typing import Any

from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import (
    AzureCliCredential,
    ChainedTokenCredential,
    ManagedIdentityCredential,
    WorkloadIdentityCredential,
)

from ._base import BaseCredential
from ._browser import SyncInteractiveBrowserCredential


class Credential(BaseCredential, TokenCredential):
    def __init__(self, resource_id: str | None = None, **kwargs: Any):
        super().__init__(resource_id, **kwargs)

    def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        scopes_tuple = self.build_scopes_tuple(scopes)
        cached = self.get_cached_token(scopes_tuple, kwargs)
        if cached:
            return cached

        token = self.credential.get_token(*scopes_tuple, **kwargs)
        self.store_cached_token(scopes_tuple, kwargs, token)
        return token

    def build_credential(self) -> ChainedTokenCredential:
        return self._build_credential_chain(
            chain_type=ChainedTokenCredential,
            browser_cls=SyncInteractiveBrowserCredential,
            credential_types=(WorkloadIdentityCredential, ManagedIdentityCredential, AzureCliCredential),
        )
