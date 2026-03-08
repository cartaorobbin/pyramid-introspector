# Domain Concepts

Key domain concepts, terminology, and mental models for this project.

## Glossary

| Term | Definition |
|---|---|
| Introspectable | A Pyramid object that stores metadata about a configuration action (route, view, permission, etc.). Accessed via `registry.introspector`. |
| RouteInfo | A discovered route with its name, URL pattern, and list of associated views. |
| ViewInfo | A single view handler for a route+method combination, with parameters, schemas, permissions, and security type. |
| Extension | A plugin that enriches base route/view metadata with library-specific information. Implements the `IntrospectionExtension` protocol. |
| Cornice Service | A REST service defined with the Cornice library, grouping views by URL path with method-specific definitions. |
| Service Definition | A tuple `(method, view_callable, args)` from a Cornice service, containing the HTTP method, the view function, and keyword arguments (schema, validators, etc.). |
| Composite Schema | A Marshmallow schema with top-level Nested fields named `body`, `querystring`, or `path` -- Cornice's way of grouping fields by location. |
| Flat Schema | A single Marshmallow schema where all fields belong to one location, determined by the Cornice validator used. |
| Security Type | A string describing the authentication scheme for a view (e.g. `"bearer"`, `"BearerAuth"`, `"basic"`). Stored as `ViewInfo.security`. Originates from view predicates like `pcm_security` or `mcp_security`. |
| pcm_request | A pycornmarsh predicate mapping locations (`body`, `querystring`) to Marshmallow schema classes. |
| pcm_responses | A pycornmarsh predicate mapping HTTP status codes to Marshmallow schema classes or description strings. |

## Mental Models

### Extension Pipeline

The introspector runs as a pipeline: core discovery produces base RouteInfo objects, then each extension enriches them in order. Extensions communicate via the `view.extra` dict -- the Cornice extension stores `cornice_args` for the pycornmarsh extension to read.

### Library Detection

Extensions use `is_available()` to check if their library is installed. This means the introspector works with any combination of installed libraries -- plain Pyramid only, Pyramid+Cornice, Pyramid+Cornice+pycornmarsh.

### Permission Storage in Pyramid

Pyramid does not store permissions directly in view introspectables. Instead, permissions live in separate `permissions` category introspectables that are linked to views via the `related` field in the introspection item.

## Invariants

- Extensions must not modify the order of routes -- only enrich existing RouteInfo/ViewInfo objects.
- The Cornice extension must run before the pycornmarsh extension (pycornmarsh reads data that Cornice stores).
- Path parameters extracted from the URL pattern are always present, even before any extension runs.
- `view.extra` is the designated namespace for extension-specific metadata that doesn't fit the core model.
