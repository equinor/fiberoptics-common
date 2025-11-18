"""Private credential base classes."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from azure.core.credentials import AccessToken
from azure.identity import AzureCliCredential, ChainedTokenCredential
from azure.identity.aio import (
    AzureCliCredential as AsyncAzureCliCredential,
    ChainedTokenCredential as AsyncChainedTokenCredential,
)

logger = logging.getLogger("fiberoptics.common")


class BaseCredential(ABC):
    _cache_skew: ClassVar[int] = 300

    def __init__(self, resource_id: str | None = None):
        self.resource_id = resource_id
        self.scope = f"{resource_id}/.default" if resource_id else None
        self._azure_cli_access_tokens: dict[tuple[str, ...], AccessToken] = {}
        self._credential = self.build_credential()

    @property
    def credential(self) -> ChainedTokenCredential | AsyncChainedTokenCredential:
        return self._credential

    def build_scopes_tuple(self, scopes: tuple[Any, ...]) -> tuple[str, ...]:
        return tuple([self.scope] if len(scopes) == 0 and self.scope else scopes)

    def get_cached_token(self, scopes_tuple: tuple[str, ...]) -> AccessToken | None:
        successful = getattr(self.credential, "_successful_credential", None)
        if successful and isinstance(successful, (AzureCliCredential, AsyncAzureCliCredential)):
            token = self._azure_cli_access_tokens.get(scopes_tuple)
            if token is not None and int(time.time()) < token.expires_on - self._cache_skew:
                return token
        return None

    def store_cached_token(self, scopes_tuple: tuple[Any, ...], token: AccessToken) -> None:
        successful = getattr(self.credential, "_successful_credential", None)
        if successful and isinstance(successful, (AzureCliCredential, AsyncAzureCliCredential)):
            self._azure_cli_access_tokens[scopes_tuple] = token

    @abstractmethod
    def build_credential(self) -> ChainedTokenCredential | AsyncChainedTokenCredential:
        ...
