"""Tests for the extension protocol and auto-discovery."""

from pyramid_introspector.extensions import (
    IntrospectionExtension,
    auto_discover_extensions,
)
from pyramid_introspector.extensions.cornice import CorniceExtension
from pyramid_introspector.extensions.pycornmarsh import PycornmarshExtension


def test_cornice_extension_satisfies_protocol():
    ext = CorniceExtension()
    assert isinstance(ext, IntrospectionExtension)


def test_pycornmarsh_extension_satisfies_protocol():
    ext = PycornmarshExtension()
    assert isinstance(ext, IntrospectionExtension)


def test_auto_discover_finds_builtin_extensions():
    extensions = auto_discover_extensions()

    names = [ext.name for ext in extensions]
    assert "cornice" in names
    assert "pycornmarsh" in names


def test_auto_discover_cornice_before_pycornmarsh():
    extensions = auto_discover_extensions()

    names = [ext.name for ext in extensions]
    cornice_idx = names.index("cornice")
    pcm_idx = names.index("pycornmarsh")
    assert cornice_idx < pcm_idx


def test_custom_extension_satisfies_protocol():

    class MyExtension:
        name = "custom"

        def is_available(self):
            return True

        def enrich(self, registry, routes):
            return routes

    ext = MyExtension()
    assert isinstance(ext, IntrospectionExtension)
