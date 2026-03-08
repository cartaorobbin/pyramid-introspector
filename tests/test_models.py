"""Tests for pyramid_introspector.models."""

from pyramid_introspector.models import (
    ParameterInfo,
    RouteInfo,
    SchemaFieldInfo,
    SchemaInfo,
    ViewInfo,
)


def test_parameter_info_defaults():
    param = ParameterInfo(name="id", location="path")
    assert param.name == "id"
    assert param.location == "path"
    assert param.required is True
    assert param.type_hint == "str"
    assert param.description == ""


def test_schema_field_info_defaults():
    field = SchemaFieldInfo(name="email", field_type="String")
    assert field.name == "email"
    assert field.field_type == "String"
    assert field.required is False
    assert field.metadata == {}


def test_schema_info_with_fields():
    fields = [
        SchemaFieldInfo(name="name", field_type="String", required=True),
        SchemaFieldInfo(name="age", field_type="Integer"),
    ]
    schema = SchemaInfo(name="UserSchema", fields=fields)
    assert schema.name == "UserSchema"
    assert len(schema.fields) == 2
    assert schema.fields[0].required is True


def test_view_info_parameter_filtering():
    params = [
        ParameterInfo(name="id", location="path"),
        ParameterInfo(name="q", location="querystring", required=False),
        ParameterInfo(name="name", location="body"),
    ]
    view = ViewInfo(method="POST", parameters=params)

    assert [p.name for p in view.path_parameters] == ["id"]
    assert [p.name for p in view.querystring_parameters] == ["q"]
    assert [p.name for p in view.body_parameters] == ["name"]
    assert view.has_body is True


def test_view_info_has_body_false_when_no_body_params():
    view = ViewInfo(
        method="GET",
        parameters=[ParameterInfo(name="id", location="path")],
    )
    assert view.has_body is False


def test_view_info_defaults():
    view = ViewInfo(method="GET")
    assert view.callable is None
    assert view.permission is None
    assert view.security is None
    assert view.description == ""
    assert view.parameters == []
    assert view.request_schema is None
    assert view.querystring_schema is None
    assert view.response_schema is None
    assert view.response_schemas == {}
    assert view.extra == {}


def test_route_info_defaults():
    route = RouteInfo(name="home", pattern="/")
    assert route.name == "home"
    assert route.pattern == "/"
    assert route.views == []
    assert route.factory is None
    assert route.extra == {}


def test_route_info_with_views():
    views = [
        ViewInfo(method="GET"),
        ViewInfo(method="POST"),
    ]
    route = RouteInfo(name="items", pattern="/items", views=views)
    assert len(route.views) == 2
    assert route.views[0].method == "GET"
    assert route.views[1].method == "POST"
