# Getting Started

## Prerequisites

- Python 3.12 or later
- A Pyramid application with a committed registry

## Installation

=== "Base"

    ```bash
    pip install pyramid-introspector
    ```

=== "With Cornice support"

    ```bash
    pip install pyramid-introspector[cornice]
    ```

    This pulls in `cornice` and `marshmallow`, enabling the built-in Cornice and pycornmarsh extensions.

## Quick start

The entry point is `PyramidIntrospector`. Pass it a committed Pyramid registry and call `introspect()`:

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

!!! tip "Using paster/plaster"

    If your application is configured via an INI file, you can bootstrap the registry like this:

    ```python
    from pyramid.paster import bootstrap

    env = bootstrap("production.ini")
    registry = env["registry"]

    introspector = PyramidIntrospector(registry)
    routes = introspector.introspect()

    env["closer"]()
    ```

## What comes back

`introspect()` returns a `list[RouteInfo]`. Each `RouteInfo` holds the route name, URL pattern, and a list of `ViewInfo` objects -- one per HTTP method handler. See the [Usage Guide](usage.md) for a detailed walkthrough of the data model.
