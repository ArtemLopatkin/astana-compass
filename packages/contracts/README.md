# astana-contracts

Installable Python 3.12–3.14 boundary contracts, deterministic policy checks, and async Protocols. Canonical definitions remain in the repository root. Bundled JSON resources are generated snapshots; run `python scripts/generate_contracts.py --check` from any working directory using the script path to detect drift.

```python
from astana_contracts import validate_payload, ContractValidationError, PlaceRepository

validated = validate_payload("RecommendationRequest", payload)
assert validated is payload  # validation never mutates input
```

`validate` is an alias for `validate_payload`. `load_schema()` returns a defensive copy. Runtime resource loading uses `importlib.resources`; an installed wheel works outside the repository. Validation errors expose `code`, `definition`, `message`, `path`, `stage`, and `as_dict()` without raw payload values. The library never makes network calls.

`astana-verify-contracts` or `python verify_contracts.py` runs the 25 canonical fixtures. These checks verify contracts and deterministic invariants, not external factual accuracy or provider uptime.
