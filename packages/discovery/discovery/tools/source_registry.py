"""Instagram source registry — factory for switching between HikerAPI, Apify, etc."""

import os
import structlog
from typing import Any

from discovery.tools.apify_instagram_source import ApifyInstagramSource
from discovery.tools.hikerapi_client import HikerAPIClient
from discovery.tools.instagram_source import InstagramSource

logger = structlog.get_logger(__name__)


class SourceRegistry:
    """Factory for Instagram data sources."""

    _instances: dict[str, InstagramSource] = {}

    def get(self, name: str | None = None) -> InstagramSource:
        """Get or create a source instance by name.

        Default is controlled by INSTAGRAM_SOURCE env var (default: hikerapi).
        Instances are cached per name for reuse.
        """
        source_name = name or os.getenv("INSTAGRAM_SOURCE", "hikerapi")

        if source_name not in self._instances:
            self._instances[source_name] = self._create(source_name)

        logger.info("instagram_source_selected", source=source_name)
        return self._instances[source_name]

    def _create(self, name: str) -> InstagramSource:
        if name == "hikerapi":
            return HikerAPIClient()
        elif name == "apify":
            return ApifyInstagramSource()
        else:
            raise ValueError(f"Unknown Instagram source: {name}. Valid: hikerapi, apify")

    def close_all(self) -> None:
        """Close all cached source instances."""
        for source in self._instances.values():
            try:
                source.close()
            except Exception as e:
                logger.warning("source_close_error", source=type(source).__name__, error=str(e))
        self._instances.clear()


registry = SourceRegistry()


def get_instagram_source(name: str | None = None) -> InstagramSource:
    """Convenience factory function."""
    return registry.get(name)
