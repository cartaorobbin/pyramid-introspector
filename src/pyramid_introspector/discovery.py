"""Core Pyramid route and view discovery from the introspection system.

This module reads Pyramid's introspectable registry to discover routes
and their associated views, producing a list of RouteInfo objects with
basic metadata (path parameters, HTTP methods, permissions, descriptions).
"""

import logging
import re
from typing import Any

from pyramid_introspector.models import ParameterInfo, RouteInfo, ViewInfo

logger = logging.getLogger(__name__)

PATH_PARAM_RE = re.compile(r"\{(\w+)(?::.*?)?\}")


def discover_routes(registry: Any) -> list[RouteInfo]:
    """Discover routes and views from a Pyramid registry.

    Args:
        registry: A committed Pyramid registry (from Configurator.registry
            after make_wsgi_app, or from pyramid.paster.bootstrap).

    Returns:
        List of RouteInfo with one ViewInfo per route+method combination.
    """
    introspector = registry.introspector

    route_category = introspector.get_category("routes") or []
    view_category = introspector.get_category("views") or []

    views_by_route = _group_views_by_route(view_category)

    routes: list[RouteInfo] = []

    for item in route_category:
        route_intr = item["introspectable"]
        route_name = route_intr.get("name")
        if not route_name:
            continue

        pattern = route_intr.get("pattern", "")
        view_items = views_by_route.get(route_name, [])

        if not view_items:
            continue

        path_params = _extract_path_params(pattern)
        has_explicit_methods = any(
            _extract_methods(vi["introspectable"]) for vi in view_items
        )

        views: list[ViewInfo] = []
        for view_item in view_items:
            view_intr = view_item["introspectable"]
            methods = _extract_methods(view_intr)
            if not methods:
                if has_explicit_methods:
                    continue
                methods = ["GET"]

            for method in methods:
                view = ViewInfo(
                    method=method.upper(),
                    callable=view_intr.get("callable"),
                    permission=_extract_permission(view_item),
                    description=_extract_description(view_intr),
                    parameters=list(path_params),
                )
                views.append(view)

        if views:
            route = RouteInfo(
                name=route_name,
                pattern=pattern,
                views=views,
                factory=route_intr.get("factory"),
            )
            routes.append(route)

    return routes


def _group_views_by_route(
    view_category: list[Any],
) -> dict[str, list[Any]]:
    """Group full view items (with related introspectables) by route_name."""
    views_by_route: dict[str, list[Any]] = {}
    for item in view_category:
        view_intr = item["introspectable"]
        route_name = view_intr.get("route_name")
        if route_name:
            views_by_route.setdefault(route_name, []).append(item)
    return views_by_route


def _extract_methods(view_intr: Any) -> list[str]:
    """Extract HTTP methods from a view introspectable."""
    methods = view_intr.get("request_methods")
    if methods is None:
        return []
    if isinstance(methods, str):
        return [methods]
    return list(methods)


def _extract_path_params(pattern: str) -> list[ParameterInfo]:
    """Extract path parameters from a route pattern like /api/{id}."""
    params = []
    for match in PATH_PARAM_RE.finditer(pattern):
        params.append(
            ParameterInfo(
                name=match.group(1),
                location="path",
                required=True,
                type_hint="str",
            )
        )
    return params


def _extract_description(view_intr: Any) -> str:
    """Get a description from the view callable's docstring."""
    view_callable = view_intr.get("callable")
    if view_callable and hasattr(view_callable, "__doc__") and view_callable.__doc__:
        return view_callable.__doc__.strip().split("\n")[0]
    return ""


def _extract_permission(view_item: Any) -> str | None:
    """Extract permission from a view item's related introspectables.

    Pyramid stores permissions in a separate 'permissions' category and
    links them to views via the 'related' field in the introspection item.
    """
    view_intr = view_item["introspectable"]
    permission = view_intr.get("permission")
    if permission:
        return str(permission)

    related = view_item.get("related", [])
    for related_intr in related:
        category = getattr(related_intr, "category_name", None)
        if category == "permissions":
            value = related_intr.get("value")
            if value:
                return str(value)
            return str(related_intr.discriminator)

    return None
