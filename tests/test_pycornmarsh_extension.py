"""Tests for the pycornmarsh extension.

Uses real Cornice services with pycornmarsh-style predicates
(pcm_request, pcm_responses, etc.) stored in the service definition
args to test the full enrichment pipeline.
"""

import marshmallow as ma
from cornice import Service
from cornice.validators import marshmallow_body_validator
from pyramid.config import Configurator

from pyramid_introspector.discovery import discover_routes
from pyramid_introspector.extensions.cornice import CorniceExtension
from pyramid_introspector.extensions.pycornmarsh import PycornmarshExtension


class CreateItemSchema(ma.Schema):
    name = ma.fields.String(required=True)
    price = ma.fields.Float(required=True)


class ItemFilterSchema(ma.Schema):
    q = ma.fields.String()
    category = ma.fields.String()


class ItemResponseSchema(ma.Schema):
    """Successful item response."""

    id = ma.fields.Integer()
    name = ma.fields.String()
    price = ma.fields.Float()


class ErrorResponseSchema(ma.Schema):
    """Error response."""

    error = ma.fields.String()
    detail = ma.fields.String()


class _PCMPredicate:
    """Minimal pycornmarsh-style view predicate for testing.

    Pycornmarsh registers these so Pyramid accepts pcm_* kwargs on
    view configs.  We replicate them here to avoid depending on
    pycornmarsh at test time.
    """

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
    "pcm_summary": type("PCMSummary", (_PCMPredicate,), {}),
    "pcm_description": type("PCMDescription", (_PCMPredicate,), {}),
    "pcm_security": type("PCMSecurity", (_PCMPredicate,), {}),
    "pcm_show": type("PCMShow", (_PCMPredicate,), {}),
}


def _make_app_with_pcm(services):
    """Create a registry with Cornice services and pcm predicates registered."""
    config = Configurator()
    config.include("cornice")
    for name, cls in _PCM_PREDICATES.items():
        config.add_view_predicate(name, cls)
    for svc in services:
        config.add_cornice_service(svc)
    config.commit()
    return config.registry


def _run_pipeline(registry):
    """Run the full discovery + cornice + pycornmarsh pipeline."""
    routes = discover_routes(registry)
    cornice_ext = CorniceExtension()
    routes = cornice_ext.enrich(registry, routes)
    pcm_ext = PycornmarshExtension()
    routes = pcm_ext.enrich(registry, routes)
    return routes


def test_pycornmarsh_extension_is_available():
    ext = PycornmarshExtension()
    assert ext.is_available() is True
    assert ext.name == "pycornmarsh"


def test_pcm_request_body_schema():
    svc = Service(name="items", path="/items")

    @svc.post(
        validators=(marshmallow_body_validator,),
        pcm_request=dict(body=CreateItemSchema),
    )
    def create_item(request):
        return {}

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    post_view = next(v for v in routes[0].views if v.method == "POST")

    assert post_view.request_schema is not None
    assert post_view.request_schema.name == "CreateItemSchema"

    body_params = post_view.body_parameters
    param_names = {p.name for p in body_params}
    assert "name" in param_names
    assert "price" in param_names


def test_pcm_request_querystring_schema():
    svc = Service(name="items", path="/items")

    @svc.get(
        pcm_request=dict(querystring=ItemFilterSchema),
    )
    def list_items(request):
        return []

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    get_view = next(v for v in routes[0].views if v.method == "GET")

    assert get_view.querystring_schema is not None
    assert get_view.querystring_schema.name == "ItemFilterSchema"

    qs_params = get_view.querystring_parameters
    param_names = {p.name for p in qs_params}
    assert "q" in param_names
    assert "category" in param_names


def test_pcm_request_body_and_querystring():
    svc = Service(name="items", path="/items")

    @svc.post(
        pcm_request=dict(body=CreateItemSchema, querystring=ItemFilterSchema),
    )
    def create_item(request):
        return {}

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    post_view = next(v for v in routes[0].views if v.method == "POST")

    assert post_view.request_schema is not None
    assert post_view.request_schema.name == "CreateItemSchema"
    assert post_view.querystring_schema is not None
    assert post_view.querystring_schema.name == "ItemFilterSchema"


def test_pcm_responses():
    svc = Service(name="items", path="/items")

    @svc.post(
        pcm_request=dict(body=CreateItemSchema),
        pcm_responses={200: ItemResponseSchema, 400: ErrorResponseSchema},
    )
    def create_item(request):
        return {}

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    post_view = next(v for v in routes[0].views if v.method == "POST")

    assert post_view.response_schema is not None
    assert post_view.response_schema.name == "ItemResponseSchema"

    assert 200 in post_view.response_schemas
    assert 400 in post_view.response_schemas
    assert post_view.response_schemas[200].name == "ItemResponseSchema"
    assert post_view.response_schemas[400].name == "ErrorResponseSchema"


def test_pcm_responses_string_description():
    svc = Service(name="items", path="/items")

    @svc.delete(
        pcm_responses={204: "No content", 404: ErrorResponseSchema},
    )
    def delete_item(request):
        return {}

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    view = next(v for v in routes[0].views if v.method == "DELETE")

    assert 204 in view.response_schemas
    assert view.response_schemas[204].name == "No content"
    assert view.response_schemas[204].fields == []

    assert 404 in view.response_schemas
    assert view.response_schemas[404].name == "ErrorResponseSchema"


def test_pcm_metadata_stored_in_extra():
    svc = Service(name="items", path="/items")

    @svc.get(
        pcm_tags=["items", "catalog"],
        pcm_summary="List all items",
        pcm_description="Returns a list of all items in the catalog",
        pcm_security="Bearer",
        pcm_show="v1",
    )
    def list_items(request):
        return []

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    view = routes[0].views[0]

    assert view.security == "Bearer"
    assert view.extra.get("pcm_tags") == ["items", "catalog"]
    assert view.extra.get("pcm_summary") == "List all items"
    assert view.extra.get("pcm_security") == "Bearer"
    assert view.extra.get("pcm_show") == "v1"


def test_pcm_description_used_when_view_has_no_description():
    svc = Service(name="items", path="/items")

    @svc.get(
        pcm_description="Returns all items",
    )
    def list_items(request):
        return []

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    view = routes[0].views[0]
    assert view.description == "Returns all items"


def test_pcm_description_does_not_override_existing():
    svc = Service(name="items", path="/items")

    @svc.get(
        pcm_description="PCM description",
    )
    def list_items(request):
        """View docstring."""
        return []

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    view = routes[0].views[0]
    assert view.description == "View docstring."


def test_pcm_responses_first_2xx_becomes_response_schema():
    svc = Service(name="items", path="/items")

    @svc.get(
        pcm_responses={
            200: ItemResponseSchema,
            201: CreateItemSchema,
            400: ErrorResponseSchema,
        },
    )
    def list_items(request):
        return []

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    view = routes[0].views[0]
    assert view.response_schema.name == "ItemResponseSchema"


def test_no_pcm_metadata_leaves_view_unchanged():
    svc = Service(name="items", path="/items")

    @svc.get()
    def list_items(request):
        """List items."""
        return []

    registry = _make_app_with_pcm([svc])
    routes = _run_pipeline(registry)

    view = routes[0].views[0]
    assert view.description == "List items."
    assert view.request_schema is None
    assert view.response_schema is None
    assert "pcm_tags" not in view.extra
