"""Tests for PyramidIntrospector -- the main orchestrator."""

import marshmallow as ma
from cornice import Service
from cornice.validators import marshmallow_body_validator
from pyramid.config import Configurator

from pyramid_introspector.extensions.cornice import CorniceExtension
from pyramid_introspector.extensions.pycornmarsh import PycornmarshExtension
from pyramid_introspector.introspector import PyramidIntrospector


class ItemSchema(ma.Schema):
    name = ma.fields.String(required=True)


class ItemResponseSchema(ma.Schema):
    id = ma.fields.Integer()
    name = ma.fields.String()


class ErrorSchema(ma.Schema):
    error = ma.fields.String()


class _PCMPredicate:
    def __init__(self, val, _):
        self.val = val

    def text(self):
        return str(self.val)

    phash = text

    def __call__(self, context, request):
        return True


_PCM_PREDICATES = {
    "pcm_request": type("PCMRequest", (_PCMPredicate,), {}),
    "pcm_responses": type("PCMResponses", (_PCMPredicate,), {}),
    "pcm_tags": type("PCMTags", (_PCMPredicate,), {}),
}


def test_introspector_with_no_extensions():
    config = Configurator()
    config.add_route("home", "/")
    config.add_view(lambda r: {}, route_name="home", renderer="json")
    config.commit()

    introspector = PyramidIntrospector(config.registry, extensions=[])
    routes = introspector.introspect()

    assert len(routes) == 1
    assert routes[0].name == "home"


def test_introspector_with_cornice_extension():
    svc = Service(name="items", path="/items")

    @svc.post(
        schema=ItemSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_item(request):
        """Create item."""
        return {}

    config = Configurator()
    config.include("cornice")
    config.add_cornice_service(svc)
    config.commit()

    introspector = PyramidIntrospector(
        config.registry,
        extensions=[CorniceExtension()],
    )
    routes = introspector.introspect()

    assert len(routes) == 1
    post_view = next(v for v in routes[0].views if v.method == "POST")
    assert post_view.request_schema is not None
    assert post_view.request_schema.name == "ItemSchema"


def test_introspector_with_full_pipeline():
    svc = Service(name="items", path="/items")

    @svc.post(
        pcm_request=dict(body=ItemSchema),
        pcm_responses={200: ItemResponseSchema, 400: ErrorSchema},
        pcm_tags=["items"],
    )
    def create_item(request):
        return {}

    config = Configurator()
    config.include("cornice")
    for name, cls in _PCM_PREDICATES.items():
        config.add_view_predicate(name, cls)
    config.add_cornice_service(svc)
    config.commit()

    introspector = PyramidIntrospector(
        config.registry,
        extensions=[CorniceExtension(), PycornmarshExtension()],
    )
    routes = introspector.introspect()

    assert len(routes) == 1
    post_view = next(v for v in routes[0].views if v.method == "POST")

    assert post_view.request_schema is not None
    assert post_view.request_schema.name == "ItemSchema"

    assert post_view.response_schema is not None
    assert post_view.response_schema.name == "ItemResponseSchema"

    assert 200 in post_view.response_schemas
    assert 400 in post_view.response_schemas

    assert post_view.extra.get("pcm_tags") == ["items"]


def test_introspector_extension_ordering_matters():
    """Pycornmarsh extension depends on Cornice having run first."""
    svc = Service(name="items", path="/items")

    @svc.post(
        pcm_request=dict(body=ItemSchema),
    )
    def create_item(request):
        return {}

    config = Configurator()
    config.include("cornice")
    for name, cls in _PCM_PREDICATES.items():
        config.add_view_predicate(name, cls)
    config.add_cornice_service(svc)
    config.commit()

    introspector = PyramidIntrospector(
        config.registry,
        extensions=[CorniceExtension(), PycornmarshExtension()],
    )
    routes = introspector.introspect()
    post_view = next(v for v in routes[0].views if v.method == "POST")
    assert post_view.request_schema is not None

    introspector_reversed = PyramidIntrospector(
        config.registry,
        extensions=[PycornmarshExtension(), CorniceExtension()],
    )
    routes_reversed = introspector_reversed.introspect()
    post_view_reversed = next(v for v in routes_reversed[0].views if v.method == "POST")
    assert post_view_reversed.request_schema is None


def test_introspector_skips_unavailable_extension():
    class UnavailableExtension:
        name = "unavailable"

        def is_available(self):
            return False

        def enrich(self, registry, routes):
            raise RuntimeError("Should not be called")

    config = Configurator()
    config.add_route("home", "/")
    config.add_view(lambda r: {}, route_name="home", renderer="json")
    config.commit()

    introspector = PyramidIntrospector(
        config.registry,
        extensions=[UnavailableExtension()],
    )
    routes = introspector.introspect()
    assert len(routes) == 1


def test_introspector_handles_extension_error_gracefully():
    class BrokenExtension:
        name = "broken"

        def is_available(self):
            return True

        def enrich(self, registry, routes):
            raise RuntimeError("Extension crashed")

    config = Configurator()
    config.add_route("home", "/")
    config.add_view(lambda r: {}, route_name="home", renderer="json")
    config.commit()

    introspector = PyramidIntrospector(
        config.registry,
        extensions=[BrokenExtension()],
    )
    routes = introspector.introspect()
    assert len(routes) == 1


def test_introspector_mixed_cornice_and_plain_routes():
    svc = Service(name="items", path="/items")

    @svc.get()
    def list_items(request):
        """List items."""
        return []

    def home_view(request):
        """Home page."""
        return {}

    config = Configurator()
    config.include("cornice")
    config.add_cornice_service(svc)
    config.add_route("home", "/")
    config.add_view(home_view, route_name="home", renderer="json")
    config.commit()

    introspector = PyramidIntrospector(
        config.registry,
        extensions=[CorniceExtension(), PycornmarshExtension()],
    )
    routes = introspector.introspect()

    route_names = {r.name for r in routes}
    assert "items" in route_names
    assert "home" in route_names

    home = next(r for r in routes if r.name == "home")
    assert home.views[0].description == "Home page."
    assert home.views[0].extra.get("cornice_args") is None

    items = next(r for r in routes if r.name == "items")
    assert items.views[0].extra.get("cornice_service_name") == "items"
