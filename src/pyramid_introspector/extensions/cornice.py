"""Cornice extension for Pyramid introspection.

Discovers Cornice services, matches them to routes, and enriches views
with Marshmallow schema metadata extracted from service definitions.

Handles two Cornice schema patterns:
  - Composite schemas: top-level Nested fields named ``body``,
    ``querystring``, or ``path``
  - Flat schemas: a single schema with location inferred from the
    validator function
"""

import logging
from typing import Any

from pyramid_introspector.models import (
    ParameterInfo,
    RouteInfo,
    SchemaFieldInfo,
    SchemaInfo,
    ViewInfo,
)

logger = logging.getLogger(__name__)

MARSHMALLOW_TYPE_MAP = {
    "String": "str",
    "Int": "int",
    "Integer": "int",
    "Float": "float",
    "Decimal": "str",
    "Bool": "bool",
    "Boolean": "bool",
    "UUID": "str",
    "DateTime": "str",
    "Date": "str",
    "List": "list",
    "Nested": "dict",
    "Dict": "dict",
    "Raw": "Any",
}

_LOCATION_FIELDS = {"body", "querystring", "path"}


class CorniceExtension:
    """Extension that enriches routes with Cornice service metadata."""

    name = "cornice"

    def is_available(self) -> bool:
        try:
            import cornice.service  # noqa: F401

            return True
        except ImportError:
            return False

    def enrich(self, registry: Any, routes: list[RouteInfo]) -> list[RouteInfo]:
        services = _get_cornice_services()
        if not services:
            return routes

        service_by_path = _index_services_by_path(services)

        for route in routes:
            service = service_by_path.get(route.pattern)
            if not service:
                continue

            for view in route.views:
                _enrich_view(view, service)

        return routes


def _get_cornice_services() -> list[Any]:
    """Get all registered Cornice services."""
    try:
        from cornice.service import get_services

        return list(get_services())
    except ImportError:
        logger.debug("Cornice not installed")
        return []
    except Exception:
        logger.debug("Failed to get Cornice services", exc_info=True)
        return []


def _index_services_by_path(services: list[Any]) -> dict[str, Any]:
    """Build a lookup from path pattern to Cornice service."""
    index: dict[str, Any] = {}
    for service in services:
        path = getattr(service, "path", "")
        if path:
            index[path] = service
    return index


def _enrich_view(view: ViewInfo, service: Any) -> None:
    """Enrich a single ViewInfo from the matching Cornice service definition."""
    definitions = getattr(service, "definitions", [])

    for method, view_callable, args in definitions:
        if method.upper() != view.method:
            continue

        if not view.description:
            view.description = getattr(service, "description", "") or ""

        view.extra["cornice_service_name"] = getattr(service, "name", "")
        view.extra["cornice_args"] = args

        schema_cls = args.get("schema")
        if schema_cls is not None:
            schema_instance = _instantiate(schema_cls)
            if schema_instance is not None:
                if _is_composite_schema(schema_instance):
                    _enrich_from_composite(view, schema_instance)
                else:
                    _enrich_from_flat(view, schema_cls, args)

        if view.response_schema is None:
            response_schema_cls = _extract_response_schema(view_callable)
            if response_schema_cls is not None:
                view.response_schema = _schema_to_schema_info(response_schema_cls)

        break


def _is_composite_schema(schema_instance: Any) -> bool:
    """Detect Cornice composite schemas with location-named Nested fields.

    Composite schemas group fields by location::

        class MyRequestSchema(ma.Schema):
            body = ma.fields.Nested(BodySchema)
            querystring = ma.fields.Nested(QuerySchema)
    """
    for name, field_obj in schema_instance.fields.items():
        if name in _LOCATION_FIELDS and type(field_obj).__name__ == "Nested":
            return True
    return False


def _enrich_from_composite(view: ViewInfo, schema_instance: Any) -> None:
    """Extract parameters and schemas from a composite schema."""
    existing_names = {p.name for p in view.parameters}

    for location_name, field_obj in schema_instance.fields.items():
        if location_name not in _LOCATION_FIELDS:
            continue
        if type(field_obj).__name__ != "Nested":
            continue
        if location_name == "path":
            continue

        inner_schema = _get_nested_schema(field_obj)
        if inner_schema is None:
            continue

        params = _fields_to_parameters(inner_schema.fields, location_name)
        for p in params:
            if p.name not in existing_names:
                view.parameters.append(p)
                existing_names.add(p.name)

        inner_info = _schema_to_schema_info(inner_schema)
        if inner_info:
            if location_name == "body":
                view.request_schema = inner_info
            elif location_name == "querystring":
                view.querystring_schema = inner_info


def _enrich_from_flat(view: ViewInfo, schema_cls: Any, args: dict) -> None:
    """Extract parameters and schemas from a flat (single-location) schema."""
    location = _detect_location(args)
    params = _extract_from_schema(schema_cls, location)

    existing_names = {p.name for p in view.parameters}
    for p in params:
        if p.name not in existing_names:
            view.parameters.append(p)
            existing_names.add(p.name)

    schema_info = _schema_to_schema_info(schema_cls)
    if schema_info:
        if location == "body":
            view.request_schema = schema_info
        elif location == "querystring":
            view.querystring_schema = schema_info


def _detect_location(args: dict) -> str:
    """Detect parameter location from Cornice validator functions.

    Cornice marshmallow validators are closures generated by
    ``_generate_marshmallow_validator``.  The first closure variable
    holds the location string (``"body"``, ``"querystring"``, or
    ``"path"``).
    """
    validators = args.get("validators", [])
    for v in validators:
        location = _location_from_closure(v)
        if location:
            return location

    return "body"


def _location_from_closure(validator: Any) -> str | None:
    """Extract the location string from a Cornice validator's closure."""
    closure = getattr(validator, "__closure__", None)
    if not closure:
        return None

    for cell in closure:
        try:
            value = cell.cell_contents
        except ValueError:
            continue
        if isinstance(value, str) and value in (
            "body",
            "querystring",
            "path",
        ):
            return value

    return None


def _instantiate(schema_cls: Any) -> Any | None:
    """Instantiate a schema class, handling both classes and instances."""
    try:
        instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        return instance if hasattr(instance, "fields") else None
    except Exception:
        logger.debug("Failed to instantiate schema", exc_info=True)
        return None


def _get_nested_schema(field_obj: Any) -> Any | None:
    """Get the inner schema instance from a Nested field."""
    nested = getattr(field_obj, "nested", None)
    if nested is None:
        return None
    try:
        if isinstance(nested, type):
            return nested()
        if callable(nested):
            return nested()
        return nested
    except Exception:
        logger.debug("Failed to get nested schema", exc_info=True)
        return None


def _extract_response_schema(view_callable: Any) -> Any | None:
    """Extract a response schema from a ``response_schema`` attribute."""
    return getattr(view_callable, "response_schema", None)


def _schema_to_schema_info(schema_cls: Any) -> SchemaInfo | None:
    """Build a SchemaInfo from a Marshmallow schema class or instance."""
    try:
        schema_instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        if not hasattr(schema_instance, "fields"):
            return None

        schema_name = (
            schema_cls.__name__
            if isinstance(schema_cls, type)
            else type(schema_cls).__name__
        )
        fields_info = _fields_to_schema_fields(schema_instance.fields)
        return SchemaInfo(name=schema_name, fields=fields_info)
    except Exception:
        logger.debug("Failed to build SchemaInfo", exc_info=True)
        return None


def _fields_to_schema_fields(fields: dict) -> list[SchemaFieldInfo]:
    """Convert Marshmallow field instances to SchemaFieldInfo objects."""
    result = []
    for field_name, field_obj in fields.items():
        field_type = type(field_obj).__name__
        required = getattr(field_obj, "required", False)
        metadata = dict(getattr(field_obj, "metadata", {}))

        result.append(
            SchemaFieldInfo(
                name=field_name,
                field_type=field_type,
                required=required,
                metadata=metadata,
            )
        )
    return result


def _extract_from_schema(schema_cls: Any, location: str) -> list[ParameterInfo]:
    """Extract ParameterInfo list from a Marshmallow schema class."""
    if schema_cls is None:
        return []

    try:
        schema_instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        if not hasattr(schema_instance, "fields"):
            return []

        return _fields_to_parameters(schema_instance.fields, location)
    except Exception:
        logger.debug(
            "Failed to extract schema for location=%s",
            location,
            exc_info=True,
        )
        return []


def _fields_to_parameters(fields: dict, location: str) -> list[ParameterInfo]:
    """Convert Marshmallow fields to ParameterInfo objects."""
    params = []
    for field_name, field_obj in fields.items():
        type_hint = _marshmallow_field_to_type(field_obj)
        required = getattr(field_obj, "required", False)

        metadata = getattr(field_obj, "metadata", {})
        description = metadata.get("description", "") if metadata else ""

        params.append(
            ParameterInfo(
                name=field_name,
                location=location,
                required=required,
                type_hint=type_hint,
                description=description,
            )
        )
    return params


def _marshmallow_field_to_type(field_obj: Any) -> str:
    """Map a Marshmallow field to a Python type hint string."""
    class_name = type(field_obj).__name__
    return MARSHMALLOW_TYPE_MAP.get(class_name, "Any")
