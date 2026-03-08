"""Pyramid Introspector -- extract route and view metadata from Pyramid apps.

Usage::

    from pyramid_introspector import PyramidIntrospector

    introspector = PyramidIntrospector(registry)
    routes = introspector.introspect()

    for route in routes:
        for view in route.views:
            print(f"{view.method} {route.pattern}")
"""

from pyramid_introspector.introspector import PyramidIntrospector
from pyramid_introspector.models import (
    ParameterInfo,
    RouteInfo,
    SchemaFieldInfo,
    SchemaInfo,
    ViewInfo,
)

__all__ = [
    "PyramidIntrospector",
    "RouteInfo",
    "ViewInfo",
    "ParameterInfo",
    "SchemaInfo",
    "SchemaFieldInfo",
]
