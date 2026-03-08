# pyramid-introspector

Extract route and view metadata from Pyramid applications, with an extension system that handles library-specific introspection for [Cornice](https://cornice.readthedocs.io/) and [pycornmarsh](https://github.com/debonzi/pycornmarsh).

## Why this library?

Pyramid's introspectable registry holds rich metadata about routes and views, but extracting it -- especially when libraries like Cornice and pycornmarsh layer their own conventions on top -- requires non-trivial, repetitive code. This library provides a single, tested entry point for that work.

## Key features

- **Typed dataclass output** -- `RouteInfo` and `ViewInfo` objects with clear, documented fields
- **Extension pipeline** -- built-in support for Cornice and pycornmarsh, plus a protocol for custom extensions
- **Schema extraction** -- Marshmallow request/response schemas are captured as `SchemaInfo` objects with field-level detail
- **Permission and security metadata** -- extracted from Pyramid ACL and pycornmarsh predicates
- **Auto-discovery** -- extensions are loaded automatically when their dependencies are installed, or registered via entry points
- **Zero configuration** -- pass a Pyramid registry, call `.introspect()`, done

## Quick look

```python
from pyramid_introspector import PyramidIntrospector

introspector = PyramidIntrospector(config.registry)
routes = introspector.introspect()

for route in routes:
    for view in route.views:
        print(f"{view.method:6} {route.pattern}")
```

## Next steps

- [Getting Started](getting-started.md) -- install the library and run your first introspection
- [Usage Guide](usage.md) -- explore the data model, work with schemas, and filter routes
- [Extensions](extensions.md) -- understand built-in extensions and write your own
- [API Reference](api-reference.md) -- complete reference for all public classes and functions
