#!/usr/bin/env python3
"""Validate seed fixtures or a supplied named contract; no application required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "contracts.schema.json").read_text())


def unique(items: list[Any], label: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"duplicate {label}")


def same_value(left: Any, right: Any) -> bool:
    # Python treats True == 1; JSON booleans are not numeric constraints.
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    if isinstance(left, list) or isinstance(right, list):
        return (isinstance(left, list) and isinstance(right, list)
                and len(left) == len(right)
                and all(same_value(a, b) for a, b in zip(left, right)))
    return left == right


def validate_place(place: dict[str, Any]) -> None:
    evidence = {item["id"]: item for item in place["evidence"]}
    unique([item["id"] for item in place["evidence"]], "evidence id")
    unique([fact["key"] for fact in place["facts"]], "fact key")
    for fact in place["facts"]:
        if not set(fact["evidence_ids"]).issubset(evidence):
            raise ValueError("fact references missing place evidence")
    if place["is_synthetic"] != any(e["is_synthetic"] for e in evidence.values()):
        raise ValueError("place synthetic marker does not match its evidence")
    if not place["is_synthetic"] and place["id"].startswith("synthetic:"):
        raise ValueError("synthetic place id must be marked synthetic")


def check_route(route: dict[str, Any], request: dict[str, Any]) -> None:
    if route["transport"] != request["transport"]:
        raise ValueError("route transport does not match request")
    if route["includes_return"] != request["return_to_origin"]:
        raise ValueError("route return flag does not match request")
    unique([e["id"] for e in route["evidence"]], "route evidence id")
    if route["distance_meters"] > 0 and route["duration_seconds"] == 0:
        raise ValueError("nonzero travel distance requires nonzero travel duration")


def check_constraints(
    evaluations: list[dict[str, Any]], request: dict[str, Any], place: dict[str, Any]
) -> None:
    unique([e["key"] for e in evaluations], "constraint evaluation key")
    by_key = {e["key"]: e for e in evaluations}
    constraints = {c["key"]: c for c in request["constraints"]}
    if by_key.keys() != constraints.keys():
        raise ValueError("every requested constraint must have exactly one evaluation")
    facts = {f["key"]: f for f in place["facts"]}
    evidence = {e["id"] for e in place["evidence"]}
    for key, constraint in constraints.items():
        evaluation = by_key[key]
        if evaluation["strength"] != constraint["strength"]:
            raise ValueError("constraint strength changed")
        if not set(evaluation["evidence_ids"]).issubset(evidence):
            raise ValueError("constraint references missing place evidence")
        fact = facts.get(key)
        if fact is None or fact["status"] != "known":
            expected = "unknown"
        else:
            expected = "satisfied" if same_value(fact["value"], constraint["value"]) else "unsatisfied"
        if evaluation["outcome"] != expected:
            raise ValueError("constraint outcome does not match known place fact")
        if expected != "unknown" and not set(fact["evidence_ids"]).issubset(evaluation["evidence_ids"]):
            raise ValueError("known constraint evaluation must cite supporting fact evidence")
        if constraint["strength"] == "required" and expected != "satisfied":
            raise ValueError("required constraint is not verified satisfied")


def validate_invariants(definition: str, instance: dict[str, Any]) -> None:
    if definition in {"RecommendationRequest", "ItineraryRequest", "RetrievalRequest"}:
        unique([c["key"] for c in instance["constraints"]], "constraint key")
        if definition == "ItineraryRequest" and len(instance["place_ids"]) > instance["limit"]:
            raise ValueError("selected place count exceeds request limit")
        return
    if definition == "Place":
        validate_place(instance)
        return
    if definition not in {"RecommendationResponse", "ItineraryResponse", "RetrievalResponse", "ContextResult", "PlaceListResponse"}:
        return
    places = {p["id"]: p for p in instance["places"]}
    unique([p["id"] for p in instance["places"]], "place id")
    for place in places.values():
        validate_place(place)
    if definition in {"ContextResult", "PlaceListResponse"}:
        return
    if definition == "RetrievalResponse":
        unique([h["place_id"] for h in instance["hits"]], "retrieval hit")
        if {h["place_id"] for h in instance["hits"]} != places.keys():
            raise ValueError("retrieval hits and returned places must resolve exactly")
        for hit in instance["hits"]:
            if not set(hit["matched_fact_keys"]).issubset({f["key"] for f in places[hit["place_id"]]["facts"]}):
                raise ValueError("retrieval hit references missing fact")
        return
    request = instance["request"]
    validate_invariants("ItineraryRequest" if definition == "ItineraryResponse" else "RecommendationRequest", request)
    key = "recommendations" if definition == "RecommendationResponse" else "stops"
    items = instance[key]
    if len(items) > request["limit"]:
        raise ValueError("response exceeds requested limit")
    if request["transport"] != "walking":
        raise ValueError("initial release must return unsupported_transport ErrorResponse")
    unique([item["place_id"] for item in items], "recommended place")
    if {item["place_id"] for item in items} != places.keys():
        raise ValueError("recommended place references and returned places must resolve exactly")
    rank_key = "rank" if key == "recommendations" else "order"
    if [item[rank_key] for item in items] != list(range(1, len(items) + 1)):
        raise ValueError("recommendations/stops must have contiguous ordered ranks")
    for item in items:
        check_constraints(item["constraint_evaluations"], request, places[item["place_id"]])
        if key == "recommendations":
            check_route(item["route"], request)
            if item["total_duration_seconds"] != item["visit_duration_seconds"] + item["route"]["duration_seconds"]:
                raise ValueError("recommendation total must include visit and all travel")
            if item["total_duration_seconds"] > request["available_seconds"]:
                raise ValueError("recommendation exceeds time budget")
    if key == "stops" and items:
        if [item["place_id"] for item in items] != request["place_ids"]:
            raise ValueError("itinerary must preserve all selected place IDs in requested order")
        check_route(instance["route"], request)
        expected = instance["route"]["duration_seconds"] + sum(s["visit_duration_seconds"] for s in items)
        if instance["total_duration_seconds"] != expected:
            raise ValueError("itinerary total must include every visit and complete route")
        if expected > request["available_seconds"]:
            raise ValueError("itinerary exceeds time budget")


def validate_contract(definition: str, instance: Any) -> tuple[str | None, str | None]:
    if definition not in SCHEMA["$defs"]:
        return "schema", f"unknown definition: {definition}"
    selected = {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{definition}"}
    errors = list(Draft202012Validator(selected, format_checker=FormatChecker()).iter_errors(instance))
    if errors:
        error = errors[0]
        return "schema", f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
    try:
        validate_invariants(definition, instance)
    except ValueError as error:
        return "invariant", str(error)
    return None, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definition", help="A $defs name, e.g. RecommendationResponse")
    parser.add_argument("--instance", type=Path, help="JSON payload to verify")
    args = parser.parse_args()
    Draft202012Validator.check_schema(SCHEMA)
    if bool(args.definition) != bool(args.instance):
        parser.error("--definition and --instance must be supplied together")
    if args.instance:
        stage, error = validate_contract(args.definition, json.loads(args.instance.read_text()))
        if error:
            raise SystemExit(f"FAIL [{stage}]: {error}")
        print(f"PASS {args.definition}")
        return
    cases = json.loads((ROOT / "contracts.examples.json").read_text())["cases"]
    failures = []
    for case in cases:
        stage, error = validate_contract(case["definition"], case["instance"])
        expected_stage = case.get("failure_stage")
        correct = (stage is None) if case["valid"] else (stage == expected_stage)
        if not correct:
            failures.append(f"{case['name']}: expected {expected_stage or 'valid'}, got {stage}: {error}")
        print(f"{'PASS' if correct else 'FAIL'} {case['name']} ({stage or 'valid'})")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Verified schema and {len(cases)} contract fixtures; application behavior is not tested.")


if __name__ == "__main__":
    main()
