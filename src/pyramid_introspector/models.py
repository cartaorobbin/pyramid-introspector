"""Data models for representing introspected Pyramid routes and views."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParameterInfo:
    """A single parameter extracted from a route pattern or schema."""

    name: str
    location: str  # "path", "querystring", "body"
    required: bool = True
    type_hint: str = "str"
    description: str = ""


@dataclass
class SchemaFieldInfo:
    """A single field in a Marshmallow schema."""

    name: str
    field_type: str  # Marshmallow field class name, e.g. "Integer", "String"
    required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaInfo:
    """A Marshmallow schema captured from introspection."""

    name: str
    fields: list[SchemaFieldInfo] = field(default_factory=list)


@dataclass
class ViewInfo:
    """A single view associated with a route, representing one HTTP method handler."""

    method: str
    callable: Any = None
    permission: str | None = None
    security: str | None = None
    description: str = ""
    parameters: list[ParameterInfo] = field(default_factory=list)
    request_schema: SchemaInfo | None = None
    querystring_schema: SchemaInfo | None = None
    response_schema: SchemaInfo | None = None
    response_schemas: dict[int, SchemaInfo] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def path_parameters(self) -> list[ParameterInfo]:
        return [p for p in self.parameters if p.location == "path"]

    @property
    def querystring_parameters(self) -> list[ParameterInfo]:
        return [p for p in self.parameters if p.location == "querystring"]

    @property
    def body_parameters(self) -> list[ParameterInfo]:
        return [p for p in self.parameters if p.location == "body"]

    @property
    def has_body(self) -> bool:
        return len(self.body_parameters) > 0


@dataclass
class RouteInfo:
    """A route discovered from a Pyramid application, grouping its views."""

    name: str
    pattern: str
    views: list[ViewInfo] = field(default_factory=list)
    factory: Any = None
    extra: dict[str, Any] = field(default_factory=dict)
