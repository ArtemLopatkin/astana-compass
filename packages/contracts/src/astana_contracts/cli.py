"""Verify all bundled fixtures or a named JSON payload."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
from .errors import ContractValidationError
from .validation import load_examples, load_schema, validate_payload


def validate_contract(definition: str, instance: Any) -> tuple[str | None, str | None]:
    try:
        validate_payload(definition, instance)
    except ContractValidationError as error:
        return error.stage, error.message
    return None, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definition", help="A $defs name, e.g. RecommendationResponse")
    parser.add_argument("--instance", type=Path, help="JSON payload to verify")
    args = parser.parse_args()
    load_schema()
    if bool(args.definition) != bool(args.instance):
        parser.error("--definition and --instance must be supplied together")
    if args.instance:
        stage, error = validate_contract(args.definition, json.loads(args.instance.read_text()))
        if error:
            raise SystemExit(f"FAIL [{stage}]: {error}")
        print(f"PASS {args.definition}")
        return
    cases = load_examples()["cases"]
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
