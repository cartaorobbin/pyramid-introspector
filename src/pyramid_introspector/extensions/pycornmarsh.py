"""Pycornmarsh extension for Pyramid introspection.

Reads pycornmarsh-specific predicates (``pcm_request``, ``pcm_responses``,
``pcm_tags``, ``pcm_summary``, ``pcm_description``, ``pcm_security``,
``pcm_show``) from Cornice service definition args and enriches views
with typed request/response schemas.

This extension should run **after** the Cornice extension, which stores
the matched Cornice ``args`` dict in ``view.extra["cornice_args"]``.
"""

import logging
from typing import Any

from pyramid_introspector.extensions.cornice import (
    _extract_from_schema,
    _schema_to_schema_info,
)
from pyramid_introspector.models import RouteInfo, SchemaInfo, ViewInfo

logger = logging.getLogger(__name__)

PCM_PREDICATE_KEYS = (
    "pcm_request",
    "pcm_responses",
    "pcm_tags",
    "pcm_summary",
    "pcm_description",
    "pcm_security",
    "pcm_show",
)


class PycornmarshExtension:
    """Extension that enriches views with pycornmarsh predicate metadata."""

    name = "pycornmarsh"

    def is_available(self) -> bool:
        try:
            import cornice.service  # noqa: F401

            return True
        except ImportError:
            return False

    def enrich(self, registry: Any, routes: list[RouteInfo]) -> list[RouteInfo]:
        for route in routes:
            for view in route.views:
                args = view.extra.get("cornice_args")
                if args is None:
                    continue

                if not _has_pcm_metadata(args):
                    continue

                _enrich_view_from_pcm(view, args)

        return routes


def _has_pcm_metadata(args: dict) -> bool:
    """Check whether any pycornmarsh keys are present in the args."""
    return any(args.get(key) is not None for key in PCM_PREDICATE_KEYS)


def _enrich_view_from_pcm(view: ViewInfo, args: dict) -> None:
    """Enrich a ViewInfo with pycornmarsh predicate data."""
    pcm_request = args.get("pcm_request")
    if pcm_request is not None:
        _enrich_from_pcm_request(view, pcm_request)

    pcm_responses = args.get("pcm_responses")
    if pcm_responses is not None:
        _enrich_from_pcm_responses(view, pcm_responses)

    pcm_security = args.get("pcm_security")
    if pcm_security is not None:
        view.security = pcm_security

    for key in (
        "pcm_tags",
        "pcm_summary",
        "pcm_description",
        "pcm_security",
        "pcm_show",
    ):
        value = args.get(key)
        if value is not None:
            view.extra[key] = value

    pcm_description = args.get("pcm_description")
    if pcm_description and not view.description:
        view.description = pcm_description


def _enrich_from_pcm_request(view: ViewInfo, pcm_request: dict) -> None:
    """Extract parameters and schemas from pycornmarsh ``pcm_request``.

    ``pcm_request`` maps locations to Marshmallow schema classes::

        pcm_request=dict(body=BodySchema, querystring=QuerySchema)
    """
    existing_names = {p.name for p in view.parameters}

    for location, schema_cls in pcm_request.items():
        if location not in ("body", "querystring"):
            continue

        params = _extract_from_schema(schema_cls, location)
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


def _enrich_from_pcm_responses(view: ViewInfo, pcm_responses: dict) -> None:
    """Extract response schemas from pycornmarsh ``pcm_responses``.

    ``pcm_responses`` maps HTTP status codes to Marshmallow schema
    classes::

        pcm_responses={200: SuccessSchema, 400: ErrorSchema}

    The first 2xx schema is also set as ``view.response_schema``.
    """
    success_set = False
    for status_code in sorted(pcm_responses, key=lambda c: int(c)):
        code = int(status_code)
        schema_or_str = pcm_responses[status_code]

        if isinstance(schema_or_str, str):
            view.response_schemas[code] = SchemaInfo(name=schema_or_str, fields=[])
            continue

        schema_info = _schema_to_schema_info(schema_or_str)
        if schema_info is None:
            continue

        view.response_schemas[code] = schema_info

        if not success_set and 200 <= code < 300:
            view.response_schema = schema_info
            success_set = True
