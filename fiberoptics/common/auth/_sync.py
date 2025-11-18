"""Sync credential implementation."""

from __future__ import annotations

import logging
from typing import Any

from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import ChainedTokenCredential, DefaultAzureCredential

from ._base import BaseCredential
from ._browser import SyncInteractiveBrowserCredential, use_browser_credentials

logger = logging.getLogger("fiberoptics.common")


class Credential(BaseCredential, TokenCredential):
    def __init__(self, resource_id: str | None = None, **kwargs: Any):
        super().__init__(resource_id, **kwargs)

    def get_token(self, *scopes: Any, **kwargs: Any) -> AccessToken:
        scopes_tuple = self.build_scopes_tuple(scopes)
        cached = self.get_cached_token(scopes_tuple)
        if cached:
            return cached

        token = self.credential.get_token(*scopes_tuple, **kwargs)
        self.store_cached_token(scopes_tuple, token)
        return token

    def build_credential(self) -> ChainedTokenCredential:
        credentials: list[TokenCredential] = []

        if use_browser_credentials():
            try:
                browser_kwargs = self.get_browser_kwargs()
                credentials.append(
                    SyncInteractiveBrowserCredential(
                        resource_id=self.resource_id,
                        scope=self.scope,
                        persist_auth_record=True,
                        **browser_kwargs,
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
