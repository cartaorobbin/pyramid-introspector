"""Tests for pyramid_introspector.discovery -- core Pyramid route/view discovery."""

from pyramid.config import Configurator

from pyramid_introspector.discovery import discover_routes


def _home_view(request):
    """Home page."""
    return {}


def _list_items(request):
    """List all items."""
    return []


def _create_item(request):
    """Create a new item."""
    return {}


def _get_item(request):
    """Get a single item."""
    return {}


def _update_item(request):
    """Update a single item."""
    return {}


def test_discover_single_route_default_get():
    config = Configurator()
    config.add_route("home", "/")
    config.add_view(_home_view, route_name="home", renderer="json")
    config.commit()

    routes = discover_routes(config.registry)

    assert len(routes) == 1
    assert routes[0].name == "home"
    assert routes[0].pattern == "/"
    assert len(routes[0].views) == 1
    assert routes[0].views[0].method == "GET"
    assert routes[0].views[0].description == "Home page."


def test_discover_route_with_explicit_methods():
    config = Configurator()
    config.add_route("items", "/items")
    config.add_view(
        _list_items,
        route_name="items",
        request_method="GET",
        renderer="json",
    )
    config.add_view(
        _create_item,
        route_name="items",
        request_method="POST",
        renderer="json",
    )
    config.commit()

    routes = discover_routes(config.registry)

    assert len(routes) == 1
    route = routes[0]
    assert route.name == "items"
    assert route.pattern == "/items"

    methods = {v.method for v in route.views}
    assert methods == {"GET", "POST"}

    get_view = next(v for v in route.views if v.method == "GET")
    assert get_view.description == "List all items."

    post_view = next(v for v in route.views if v.method == "POST")
    assert post_view.description == "Create a new item."


def test_discover_route_with_path_parameters():
    config = Configurator()
    config.add_route("item_detail", "/items/{item_id}")
    config.add_view(
        _get_item,
        route_name="item_detail",
        request_method="GET",
        renderer="json",
    )
    config.commit()

    routes = discover_routes(config.registry)

    assert len(routes) == 1
    route = routes[0]
    assert route.pattern == "/items/{item_id}"

    view = route.views[0]
    assert len(view.parameters) == 1
    assert view.parameters[0].name == "item_id"
    assert view.parameters[0].location == "path"
    assert view.parameters[0].required is True
    assert view.parameters[0].type_hint == "str"


def test_discover_route_with_typed_path_parameter():
    config = Configurator()
    config.add_route("item_detail", "/items/{item_id:\\d+}")
    config.add_view(
        _get_item,
        route_name="item_detail",
        request_method="GET",
        renderer="json",
    )
    config.commit()

    routes = discover_routes(config.registry)

    route = routes[0]
    view = route.views[0]
    assert len(view.parameters) == 1
    assert view.parameters[0].name == "item_id"


def test_discover_multiple_routes():
    config = Configurator()
    config.add_route("home", "/")
    config.add_view(_home_view, route_name="home", renderer="json")

    config.add_route("items", "/items")
    config.add_view(
        _list_items,
        route_name="items",
        request_method="GET",
        renderer="json",
    )
    config.commit()

    routes = discover_routes(config.registry)

    assert len(routes) == 2
    route_names = {r.name for r in routes}
    assert route_names == {"home", "items"}


def test_discover_skips_routes_without_views():
    config = Configurator()
    config.add_route("orphan", "/orphan")
    config.add_route("home", "/")
    config.add_view(_home_view, route_name="home", renderer="json")
    config.commit()

    routes = discover_routes(config.registry)

    route_names = {r.name for r in routes}
    assert "orphan" not in route_names
    assert "home" in route_names


def test_discover_extracts_permission():
    config = Configurator()
    config.add_route("admin", "/admin")
    config.add_view(
        _home_view,
        route_name="admin",
        renderer="json",
        permission="admin",
    )
    config.commit()

    routes = discover_routes(config.registry)

    assert len(routes) == 1
    view = routes[0].views[0]
    assert view.permission == "admin"


def test_discover_view_without_docstring():
    def bare_view(request):
        return {}

    config = Configurator()
    config.add_route("bare", "/bare")
    config.add_view(bare_view, route_name="bare", renderer="json")
    config.commit()

    routes = discover_routes(config.registry)

    assert routes[0].views[0].description == ""


def test_discover_skip_view_without_method_when_others_have_methods():
    """When some views have explicit methods and one doesn't, skip the one without."""

    def catch_all(request):
        return {}

    config = Configurator()
    config.add_route("items", "/items")
    config.add_view(
        _list_items,
        route_name="items",
        request_method="GET",
        renderer="json",
    )
    config.add_view(
        catch_all,
        route_name="items",
        renderer="json",
    )
    config.commit()

    routes = discover_routes(config.registry)

    assert len(routes) == 1
    methods = [v.method for v in routes[0].views]
    assert methods == ["GET"]


def test_discover_multiple_path_parameters():
    config = Configurator()
    config.add_route("nested", "/orgs/{org_id}/projects/{project_id}")
    config.add_view(
        _get_item,
        route_name="nested",
        request_method="GET",
        renderer="json",
    )
    config.commit()

    routes = discover_routes(config.registry)

    view = routes[0].views[0]
    param_names = [p.name for p in view.parameters]
    assert param_names == ["org_id", "project_id"]
