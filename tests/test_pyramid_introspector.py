"""Smoke tests for the pyramid-introspector public API."""

import pyramid_introspector
from pyramid_introspector import (
    ParameterInfo,
    PyramidIntrospector,
    RouteInfo,
    SchemaFieldInfo,
    SchemaInfo,
    ViewInfo,
)


def test_import():
    """Verify package is importable."""
    assert pyramid_introspector is not None


def test_public_api_exports():
    """Verify all public symbols are importable."""
    assert PyramidIntrospector is not None
    assert RouteInfo is not None
    assert ViewInfo is not None
    assert ParameterInfo is not None
    assert SchemaInfo is not None
    assert SchemaFieldInfo is not None
