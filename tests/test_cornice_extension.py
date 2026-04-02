"""Tests for the Cornice extension.

Uses real Cornice services and Marshmallow schemas to test the
full introspection pipeline.
"""

import marshmallow as ma
from cornice import Service
from cornice.validators import (
    marshmallow_body_validator,
    marshmallow_querystring_validator,
)
from pyramid.config import Configurator

from pyramid_introspector.discovery import discover_routes
from pyramid_introspector.extensions.cornice import (
    CorniceExtension,
    _schema_to_schema_info,
)


class ItemSchema(ma.Schema):
    name = ma.fields.String(required=True, metadata={"description": "Item name"})
    price = ma.fields.Float(required=True)
    description = ma.fields.String()


class ItemQuerySchema(ma.Schema):
    q = ma.fields.String(metadata={"description": "Search query"})
    limit = ma.fields.Integer()


class CompositeSchema(ma.Schema):
    body = ma.fields.Nested(ItemSchema)
    querystring = ma.fields.Nested(ItemQuerySchema)


class PhoneSchema(ma.Schema):
    number = ma.fields.String(required=True)
    label = ma.fields.String()


class AddressSchema(ma.Schema):
    street = ma.fields.String(required=True)
    city = ma.fields.String(required=True)


class PersonSchema(ma.Schema):
    name = ma.fields.String(required=True)
    birthdate = ma.fields.Date(allow_none=True)
    phones = ma.fields.Nested(PhoneSchema, many=True)
    address = ma.fields.Nested(AddressSchema)
    tags = ma.fields.List(ma.fields.Nested(PhoneSchema))


class TreeNodeSchema(ma.Schema):
    """Self-referencing schema for circular recursion testing."""

    value = ma.fields.String(required=True)
    children = ma.fields.Nested(lambda: TreeNodeSchema, many=True)


def _make_cornice_app(services):
    """Create a committed Pyramid registry with Cornice services."""
    config = Configurator()
    config.include("cornice")
    for svc in services:
        config.add_cornice_service(svc)
    config.commit()
    return config.registry


def test_cornice_extension_is_available():
    ext = CorniceExtension()
    assert ext.is_available() is True
    assert ext.name == "cornice"


def test_cornice_enriches_with_flat_body_schema():
    svc = Service(name="items", path="/items", description="Manage items")

    @svc.post(
        schema=ItemSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_item(request):
        """Create a new item."""
        return {}

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    assert len(routes) == 1
    post_view = next(v for v in routes[0].views if v.method == "POST")

    body_params = post_view.body_parameters
    assert len(body_params) >= 2
    param_names = {p.name for p in body_params}
    assert "name" in param_names
    assert "price" in param_names

    assert post_view.request_schema is not None
    assert post_view.request_schema.name == "ItemSchema"
    field_names = {f.name for f in post_view.request_schema.fields}
    assert "name" in field_names
    assert "price" in field_names


def test_cornice_enriches_with_querystring_schema():
    svc = Service(name="items", path="/items")

    @svc.get(
        schema=ItemQuerySchema(),
        validators=(marshmallow_querystring_validator,),
    )
    def list_items(request):
        """List items."""
        return []

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    get_view = next(v for v in routes[0].views if v.method == "GET")

    qs_params = get_view.querystring_parameters
    param_names = {p.name for p in qs_params}
    assert "q" in param_names
    assert "limit" in param_names

    assert get_view.querystring_schema is not None
    assert get_view.querystring_schema.name == "ItemQuerySchema"


def test_cornice_enriches_with_composite_schema():
    svc = Service(name="items_composite", path="/items-composite")

    @svc.post(
        schema=CompositeSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_item(request):
        """Create item with composite schema."""
        return {}

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    post_view = next(v for v in routes[0].views if v.method == "POST")

    assert post_view.request_schema is not None
    assert post_view.request_schema.name == "ItemSchema"

    assert post_view.querystring_schema is not None
    assert post_view.querystring_schema.name == "ItemQuerySchema"


def test_cornice_preserves_path_parameters():
    svc = Service(name="item_detail", path="/items/{item_id}")

    @svc.get()
    def get_item(request):
        """Get an item."""
        return {}

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    view = routes[0].views[0]
    path_params = view.path_parameters
    assert len(path_params) == 1
    assert path_params[0].name == "item_id"


def test_cornice_stores_service_name_in_extra():
    svc = Service(name="items", path="/items")

    @svc.get()
    def list_items(request):
        return []

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    view = routes[0].views[0]
    assert view.extra.get("cornice_service_name") == "items"


def test_cornice_uses_service_description_when_view_has_none():
    svc = Service(name="items", path="/items", description="Item management")

    @svc.get()
    def list_items(request):
        return []

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    view = routes[0].views[0]
    assert view.description == "Item management"


def test_cornice_does_not_override_existing_description():
    svc = Service(name="items", path="/items", description="Service description")

    @svc.get()
    def list_items(request):
        """View description."""
        return []

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    view = routes[0].views[0]
    assert view.description == "View description."


def test_cornice_multiple_methods_on_same_service():
    svc = Service(name="items", path="/items")

    @svc.get()
    def list_items(request):
        """List items."""
        return []

    @svc.post(
        schema=ItemSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_item(request):
        """Create item."""
        return {}

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    route = routes[0]
    methods = {v.method for v in route.views}
    assert "GET" in methods
    assert "POST" in methods

    post_view = next(v for v in route.views if v.method == "POST")
    assert post_view.request_schema is not None

    get_view = next(v for v in route.views if v.method == "GET")
    assert get_view.request_schema is None


def test_cornice_schema_field_metadata():
    svc = Service(name="items", path="/items")

    @svc.post(
        schema=ItemSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_item(request):
        return {}

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    post_view = next(v for v in routes[0].views if v.method == "POST")
    name_field = next(f for f in post_view.request_schema.fields if f.name == "name")
    assert name_field.required is True
    assert name_field.field_type == "String"
    assert name_field.metadata.get("description") == "Item name"


def test_cornice_no_enrichment_for_non_cornice_route():
    svc = Service(name="items", path="/items")

    @svc.get()
    def list_items(request):
        """List items."""
        return []

    config = Configurator()
    config.include("cornice")
    config.add_cornice_service(svc)
    config.add_route("other", "/other")
    config.add_view(lambda r: {}, route_name="other", renderer="json")
    config.commit()

    routes = discover_routes(config.registry)
    ext = CorniceExtension()
    routes = ext.enrich(config.registry, routes)

    other_route = next(r for r in routes if r.name == "other")
    assert other_route.views[0].extra.get("cornice_args") is None

    items_route = next(r for r in routes if r.name == "items")
    assert items_route.views[0].extra.get("cornice_service_name") == "items"


def test_schema_field_allow_none():
    info = _schema_to_schema_info(PersonSchema)
    assert info is not None

    birthdate = next(f for f in info.fields if f.name == "birthdate")
    assert birthdate.allow_none is True
    assert birthdate.field_type == "Date"

    name_field = next(f for f in info.fields if f.name == "name")
    assert name_field.allow_none is False


def test_schema_field_nested_many():
    info = _schema_to_schema_info(PersonSchema)
    assert info is not None

    phones = next(f for f in info.fields if f.name == "phones")
    assert phones.field_type == "Nested"
    assert phones.many is True
    assert phones.nested_schema == "PhoneSchema"


def test_schema_field_nested_single():
    info = _schema_to_schema_info(PersonSchema)
    assert info is not None

    address = next(f for f in info.fields if f.name == "address")
    assert address.field_type == "Nested"
    assert address.many is False
    assert address.nested_schema == "AddressSchema"


def test_schema_field_list_of_nested():
    info = _schema_to_schema_info(PersonSchema)
    assert info is not None

    tags = next(f for f in info.fields if f.name == "tags")
    assert tags.field_type == "List"
    assert tags.nested_schema == "PhoneSchema"


def test_nested_schema_recursive_discovery():
    info = _schema_to_schema_info(PersonSchema)
    assert info is not None

    nested_names = {s.name for s in info.nested_schemas}
    assert "PhoneSchema" in nested_names
    assert "AddressSchema" in nested_names

    phone_info = next(s for s in info.nested_schemas if s.name == "PhoneSchema")
    phone_field_names = {f.name for f in phone_info.fields}
    assert "number" in phone_field_names
    assert "label" in phone_field_names

    address_info = next(s for s in info.nested_schemas if s.name == "AddressSchema")
    address_field_names = {f.name for f in address_info.fields}
    assert "street" in address_field_names
    assert "city" in address_field_names


def test_nested_schema_no_circular_recursion():
    info = _schema_to_schema_info(TreeNodeSchema)
    assert info is not None
    assert info.name == "TreeNodeSchema"

    children_field = next(f for f in info.fields if f.name == "children")
    assert children_field.field_type == "Nested"
    assert children_field.many is True
    assert children_field.nested_schema == "TreeNodeSchema"

    assert info.nested_schemas == []


def test_nested_schemas_via_cornice_pipeline():
    """Nested schemas are discovered through the full Cornice enrichment."""
    svc = Service(name="people", path="/people")

    @svc.post(
        schema=PersonSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_person(request):
        return {}

    registry = _make_cornice_app([svc])
    routes = discover_routes(registry)

    ext = CorniceExtension()
    routes = ext.enrich(registry, routes)

    post_view = next(v for v in routes[0].views if v.method == "POST")
    assert post_view.request_schema is not None

    nested_names = {s.name for s in post_view.request_schema.nested_schemas}
    assert "PhoneSchema" in nested_names
    assert "AddressSchema" in nested_names
