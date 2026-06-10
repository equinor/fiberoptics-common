"""Private credential base classes."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from azure.core.credentials import AccessToken
from azure.identity import ChainedTokenCredential
from azure.identity.aio import ChainedTokenCredential as AsyncChainedTokenCredential


class BaseCredential(ABC):
    _cache_skew: ClassVar[int] = 300

    def __init__(self, resource_id: str | None = None, **kwargs: Any):
        self.resource_id = resource_id
        self.scope = f"{resource_id}/.default" if resource_id else None
        self._kwargs = kwargs
        self._cached_access_tokens: dict[tuple, AccessToken] = {}
        self._credential = self.build_credential()

    @property
    def credential(self) -> ChainedTokenCredential | AsyncChainedTokenCredential:
        return self._credential

    def build_scopes_tuple(self, scopes: tuple[Any, ...]) -> tuple[str, ...]:
        return tuple([self.scope] if len(scopes) == 0 and self.scope else scopes)

    @staticmethod
    def _cache_key(scopes_tuple: tuple[str, ...], kwargs: dict[str, Any]) -> tuple:
        tenant_id = kwargs.get("tenant_id")
        enable_cae = kwargs.get("enable_cae", False)
        return (scopes_tuple, tenant_id, enable_cae)

    def get_cached_token(self, scopes_tuple: tuple[str, ...], kwargs: dict[str, Any]) -> AccessToken | None:
        if kwargs.get("claims"):
            return None
        key = self._cache_key(scopes_tuple, kwargs)
        token = self._cached_access_tokens.get(key)
        if token is not None and int(time.time()) < token.expires_on - self._cache_skew:
            return token
        return None

    def store_cached_token(self, scopes_tuple: tuple[str, ...], kwargs: dict[str, Any], token: AccessToken) -> None:
        if kwargs.get("claims"):
            return
        key = self._cache_key(scopes_tuple, kwargs)
        self._cached_access_tokens[key] = token

    def get_browser_kwargs(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in (
                ("client_id", self._kwargs.get("client_id", None)),
                ("tenant_id", self._kwargs.get("tenant_id", None)),
                (
                    "redirect_uri",
                    self._kwargs.get("redirect_uri", None),
                ),
            )
            if value is not None
        }

    @abstractmethod
    def build_credential(self) -> ChainedTokenCredential | AsyncChainedTokenCredential:
        ...
