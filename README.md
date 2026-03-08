# pyramid-introspector

Extract route and view metadata from Pyramid applications, with an extension system that handles library-specific introspection for [Cornice](https://cornice.readthedocs.io/) and [pycornmarsh](https://github.com/debonzi/pycornmarsh).

## Why

Pyramid's introspectable registry holds rich metadata about routes and views, but extracting it -- especially when libraries like Cornice and pycornmarsh layer their own conventions on top -- requires non-trivial, repetitive code. This library provides a single, tested entry point for that work.

## Installation

```bash
pip install pyramid-introspector
```

With Cornice/Marshmallow support:

```bash
pip install pyramid-introspector[cornice]
```

## Quick start

```python
from pyramid.config import Configurator
from pyramid_introspector import PyramidIntrospector

config = Configurator()
# ... add routes, views, include cornice, etc.
config.commit()

introspector = PyramidIntrospector(config.registry)
routes = introspector.introspect()

for route in routes:
    for view in route.views:
        print(f"{view.method:6} {route.pattern}")
        if view.request_schema:
            print(f"       body: {view.request_schema.name}")
        if view.response_schema:
            print(f"       resp: {view.response_schema.name}")
```

## What you get

Each `RouteInfo` contains:

| Field     | Type             | Description                          |
|-----------|------------------|--------------------------------------|
| `name`    | `str`            | Pyramid route name                   |
| `pattern` | `str`            | URL pattern (e.g. `/items/{id}`)     |
| `views`   | `list[ViewInfo]` | One per HTTP method                  |
| `factory` | `Any`            | Route factory for ACL contexts       |
| `extra`   | `dict`           | Extension-specific route metadata    |

Each `ViewInfo` contains:

| Field                | Type                   | Description                                          |
|----------------------|------------------------|------------------------------------------------------|
| `method`             | `str`                  | HTTP method (`GET`, `POST`, ...)                     |
| `callable`           | `Any`                  | The Python view function                             |
| `permission`         | `str \| None`          | Pyramid permission (from ACL)                        |
| `security`           | `str \| None`          | Auth scheme type (e.g. `"bearer"`, `"BearerAuth"`)   |
| `description`        | `str`                  | First line of view docstring                         |
| `parameters`         | `list[ParameterInfo]`  | Path, querystring, and body parameters               |
| `request_schema`     | `SchemaInfo \| None`   | Marshmallow schema for request body                  |
| `querystring_schema` | `SchemaInfo \| None`   | Marshmallow schema for querystring                   |
| `response_schema`    | `SchemaInfo \| None`   | Primary 2xx response schema                          |
| `response_schemas`   | `dict[int, SchemaInfo]`| All response schemas keyed by status code            |
| `extra`              | `dict`                 | Extension-specific view metadata                     |

## Extensions

Extensions enrich the base route/view data with library-specific metadata. Built-in extensions are loaded automatically when their dependencies are installed.

### Cornice

Activated when `cornice` is installed. Discovers Cornice services, matches them to routes by path, and extracts Marshmallow schemas from service definitions -- both composite schemas (body/querystring/path as nested fields) and flat schemas with location detection from validators.

### pycornmarsh

Activated when `cornice` is installed. Reads pycornmarsh predicates (`pcm_request`, `pcm_responses`, `pcm_tags`, `pcm_summary`, `pcm_description`, `pcm_security`, `pcm_show`) from Cornice service definition args and populates the corresponding ViewInfo fields.

### Writing custom extensions

Any class that satisfies the `IntrospectionExtension` protocol can be used:

```python
from pyramid_introspector.extensions import IntrospectionExtension
from pyramid_introspector.models import RouteInfo

class MyExtension:
    name = "my_library"

    def is_available(self) -> bool:
        try:
            import my_library
            return True
        except ImportError:
            return False

    def enrich(self, registry, routes: list[RouteInfo]) -> list[RouteInfo]:
        # Mutate views with library-specific metadata
        return routes
```

Pass it directly:

```python
introspector = PyramidIntrospector(registry, extensions=[MyExtension()])
```

Or register it via entry points for automatic discovery:

```toml
[project.entry-points."pyramid_introspector.extensions"]
my_library = "my_package:MyExtension"
```

## Development

```bash
git clone https://github.com/your-org/pyramid-introspector.git
cd pyramid-introspector
uv sync --group dev
```

Run tests:

```bash
uv run pytest
```

Lint and format:

```bash
uv run ruff check src/ tests/
uv run black src/ tests/
```

## License

MIT
