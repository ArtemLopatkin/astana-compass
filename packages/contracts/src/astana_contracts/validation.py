"""Schema and deterministic invariant validation, independent of working directory."""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
import json
import math
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import ContractValidationError
from .invariants import validate_invariants

JSON = dict[str, Any]


@lru_cache(maxsize=1)
def _canonical_schema() -> JSON:
    schema = json.loads(files("astana_contracts").joinpath("data/contracts.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def load_schema() -> JSON:
    """Return an independent copy; callers cannot mutate runtime validators."""
    return deepcopy(_canonical_schema())


def load_examples() -> JSON:
    return json.loads(files("astana_contracts").joinpath("data/contracts.examples.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(definition: str) -> Draft202012Validator:
    schema = _canonical_schema()
    selected = {"$schema": schema["$schema"], "$defs": schema["$defs"],
                "$ref": f"#/$defs/{definition}"}
    return Draft202012Validator(selected, format_checker=FormatChecker())


def _json_value(value: Any, active: set[int] | None = None) -> bool:
    """Reject Python-only objects, nonfinite numbers and cycles before schema traversal."""
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) not in (dict, list):
        return False
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        return False
    active.add(marker)
    try:
        if type(value) is dict:
            return all(type(key) is str and _json_value(item, active) for key, item in value.items())
        return all(_json_value(item, active) for item in value)
    finally:
        active.remove(marker)


_MESSAGES = {
    "required": "A required field is missing.",
    "additionalProperties": "An unexpected field is present.",
    "type": "A field has an invalid JSON type.",
    "enum": "A field has an unsupported value.",
    "const": "A field does not match the required constant.",
    "format": "A field has an invalid format.",
    "pattern": "A field does not match its required format.",
    "minimum": "A numeric field is below the permitted minimum.",
    "maximum": "A numeric field exceeds the permitted maximum.",
    "minItems": "An array has too few items.",
    "maxItems": "An array has too many items.",
    "uniqueItems": "An array contains duplicate items.",
}


def validate_payload(definition: str, payload: Any) -> JSON:
    """Validate a named boundary and return the identical dictionary, without mutation.

    Raises ContractValidationError with safe diagnostics, never jsonschema's raw
    exception text (which can contain private user input). No network access occurs.
    """
    schema = _canonical_schema()
    if not isinstance(definition, str) or definition not in schema["$defs"]:
        raise ContractValidationError(definition="<unknown>", code="unknown_definition",
                                      message="The contract definition is unknown.")
    if type(payload) is not dict or not _json_value(payload):
        raise ContractValidationError(definition=definition, code="invalid_json",
                                      message="The payload must be a JSON object with finite numbers.")
    error = next(_validator(definition).iter_errors(payload), None)
    if error is not None:
        raise ContractValidationError(
            definition=definition, code="contract_schema_violation",
            message=_MESSAGES.get(str(error.validator), "A field violates the contract schema."),
            path=tuple(error.absolute_path),
        ) from None
    try:
        validate_invariants(definition, payload)
    except ValueError as error:
        # Invariant messages are fixed developer-authored strings, never interpolated payloads.
        raise ContractValidationError(
            definition=definition, code="contract_invariant_violation",
            message=str(error), stage="invariant",
        ) from None
    return payload


validate = validate_payload
