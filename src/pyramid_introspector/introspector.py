"""Main introspector that orchestrates discovery and extension enrichment."""

import logging
from typing import Any

from pyramid_introspector.discovery import discover_routes
from pyramid_introspector.extensions import (
    IntrospectionExtension,
    auto_discover_extensions,
)
from pyramid_introspector.models import RouteInfo

logger = logging.getLogger(__name__)


class PyramidIntrospector:
    """Introspect a Pyramid application's routes and views.

    Discovers routes from Pyramid's introspectable registry and enriches
    them through a chain of extensions that handle library-specific
    metadata (Cornice services, pycornmarsh predicates, etc.).

    Args:
        registry: A committed Pyramid registry.
        extensions: Optional list of extensions. When None, extensions
            are auto-discovered from built-ins and entry points.
    """

    def __init__(
        self,
        registry: Any,
        extensions: list[IntrospectionExtension] | None = None,
    ):
        self.registry = registry
        self.extensions = (
            extensions if extensions is not None else auto_discover_extensions()
        )

    def introspect(self) -> list[RouteInfo]:
        """Discover routes and enrich them through all available extensions.

        Returns:
            List of RouteInfo objects, each containing ViewInfo objects
            enriched with library-specific metadata.
        """
        routes = discover_routes(self.registry)

        for ext in self.extensions:
            if not ext.is_available():
                logger.debug("Skipping extension %s (not available)", ext.name)
                continue
            try:
                routes = ext.enrich(self.registry, routes)
            except Exception:
                logger.warning(
                    "Extension %s failed during enrichment",
                    ext.name,
                    exc_info=True,
                )

        return routes
