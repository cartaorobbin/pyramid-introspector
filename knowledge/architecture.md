# Architecture

## Overview

A library that introspects Pyramid views and extracts their metadata and information, with an extension system that handles library-specific introspection (Cornice, pycornmarsh, etc.).

## Components

### Core Layer

- **`models.py`** -- Data classes representing introspected information: `RouteInfo`, `ViewInfo`, `ParameterInfo`, `SchemaInfo`, `SchemaFieldInfo`.
- **`discovery.py`** -- Reads Pyramid's introspectable registry to discover routes and views. Extracts path parameters, HTTP methods, permissions (from related introspectables), and descriptions (from docstrings).
- **`introspector.py`** -- `PyramidIntrospector` class that orchestrates discovery and extension enrichment.

### Extension System

- **`extensions/__init__.py`** -- Defines the `IntrospectionExtension` protocol and auto-discovery mechanism (built-ins + entry points via `pyramid_introspector.extensions` group).
- **`extensions/cornice.py`** -- `CorniceExtension`: discovers Cornice services via `get_services()`, matches them to routes by path, extracts Marshmallow schemas (composite and flat patterns), detects parameter location from validator closures. Stores `cornice_args` and `cornice_service_name` in `view.extra` for downstream extensions.
- **`extensions/pycornmarsh.py`** -- `PycornmarshExtension`: reads pycornmarsh predicates (`pcm_request`, `pcm_responses`, `pcm_tags`, `pcm_summary`, `pcm_description`, `pcm_security`, `pcm_show`) from the `cornice_args` stored by the Cornice extension. Must run after the Cornice extension.

## Data Flow

```
Pyramid Registry
    │
    ▼
discover_routes(registry)          ← discovery.py
    │  reads introspector.get_category("routes") and ("views")
    │  extracts path params, methods, permissions, descriptions
    │  produces list[RouteInfo]
    │
    ▼
CorniceExtension.enrich()          ← extensions/cornice.py
    │  gets cornice services, matches by path
    │  extracts Marshmallow schemas from service definitions
    │  stores cornice_args in view.extra
    │
    ▼
PycornmarshExtension.enrich()      ← extensions/pycornmarsh.py
    │  reads pcm_* metadata from view.extra["cornice_args"]
    │  extracts request/response schemas
    │  stores pcm_tags, pcm_summary etc. in view.extra
    │
    ▼
list[RouteInfo]  ← fully enriched, returned to consumer
```

## External Dependencies

- **pyramid** -- For the introspectable registry and route/view system.
- **cornice** (optional) -- For Cornice service discovery and Marshmallow schema extraction.
- **marshmallow** (optional) -- For schema field introspection.
- **pycornmarsh** (not a runtime dependency) -- The extension reads pycornmarsh predicates from Cornice args without importing pycornmarsh itself.
