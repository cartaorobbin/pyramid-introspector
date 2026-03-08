"""Extension system for library-specific Pyramid introspection.

Extensions enrich the base route/view metadata discovered from Pyramid's
introspection system with library-specific information (e.g. Cornice
service metadata, Marshmallow schemas from pycornmarsh predicates).

Third-party extensions can be registered via the
``pyramid_introspector.extensions`` entry point group.
"""

import logging
from typing import Any, Protocol, runtime_checkable

from pyramid_introspector.models import RouteInfo

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "pyramid_introspector.extensions"


@runtime_checkable
class IntrospectionExtension(Protocol):
    """Protocol that all introspection extensions must satisfy."""

    name: str

    def is_available(self) -> bool:
        """Return True if the library this extension handles is installed."""
        ...

    def enrich(self, registry: Any, routes: list[RouteInfo]) -> list[RouteInfo]:
        """Enrich route info with library-specific metadata.

        Extensions should mutate or replace the ViewInfo objects in the
        provided routes, adding parameters, schemas, and extra metadata.

        Args:
            registry: The Pyramid registry.
            routes: Routes discovered so far (may already be enriched
                by earlier extensions).

        Returns:
            The enriched list of routes.
        """
        ...


def auto_discover_extensions() -> list[IntrospectionExtension]:
    """Discover and instantiate extensions from entry points and built-ins.

    Built-in extensions (cornice, pycornmarsh) are always included when
    their dependencies are available.  Additional extensions can be
    registered via the ``pyramid_introspector.extensions`` entry point
    group.
    """
    extensions: list[IntrospectionExtension] = []

    extensions.extend(_load_builtin_extensions())
    extensions.extend(_load_entrypoint_extensions())

    return extensions


def _load_builtin_extensions() -> list[IntrospectionExtension]:
    """Load the built-in extensions shipped with this package."""
    builtins: list[IntrospectionExtension] = []

    try:
        from pyramid_introspector.extensions.cornice import CorniceExtension

        builtins.append(CorniceExtension())
    except Exception:
        logger.debug("Could not load CorniceExtension", exc_info=True)

    try:
        from pyramid_introspector.extensions.pycornmarsh import (
            PycornmarshExtension,
        )

        builtins.append(PycornmarshExtension())
    except Exception:
        logger.debug("Could not load PycornmarshExtension", exc_info=True)

    return builtins


def _load_entrypoint_extensions() -> list[IntrospectionExtension]:
    """Load extensions registered via entry points."""
    loaded: list[IntrospectionExtension] = []

    from importlib.metadata import entry_points

    eps = entry_points(group=ENTRY_POINT_GROUP)

    for ep in eps:
        try:
            ext_class = ep.load()
            ext = ext_class()
            if isinstance(ext, IntrospectionExtension):
                loaded.append(ext)
            else:
                logger.warning(
                    "Entry point %s does not satisfy IntrospectionExtension",
                    ep.name,
                )
        except Exception:
            logger.warning(
                "Failed to load extension from entry point %s",
                ep.name,
                exc_info=True,
            )

    return loaded
