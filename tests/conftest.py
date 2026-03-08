"""Shared test fixtures for pyramid-introspector."""

import pytest
from pyramid import testing
from pyramid.config import Configurator


@pytest.fixture
def pyramid_config():
    """Create a Pyramid Configurator for testing."""
    config = Configurator()
    yield config
    testing.tearDown()


@pytest.fixture
def make_registry():
    """Factory fixture that creates a committed Pyramid registry.

    Usage::

        def test_something(make_registry):
            def configure(config):
                config.add_route("home", "/")
                config.add_view(my_view, route_name="home")
            registry = make_registry(configure)
    """

    def _make(configure_fn):
        config = Configurator()
        configure_fn(config)
        config.commit()
        return config.registry

    yield _make
    testing.tearDown()
