# Shared contracts — seed v0.1.0

This is a machine-checkable integration seed, not a running application. `contracts.schema.json` is the canonical JSON Schema Draft 2020-12. Validate a named `$defs` entry, not the root union, for requests. `contracts.examples.json` contains only unmistakably synthetic places and evidence. No example proves a real venue, opening time, routing provider or completed feature.

The coordinator will move these five root files together into `packages/contracts` after browser upload. Until that coordinated move, agents must use the root paths. Update imports and CI together when moving them. Implementations may generate Python/TypeScript types from this schema; independently maintained wire models must pass the same fixtures. Propose a coordinated contract change before changing field names or meanings.

## Public endpoints

| Method/path | Request | Success | Notes |
|---|---|---|---|
| GET `/v1/health/live` | none | `HealthResponse` | Process liveness; no provider probe. |
| GET `/v1/health/ready` | none | `HealthResponse` | Essential local dependencies ready; 503 if unavailable. |
| GET `/v1/places` | bbox, query, categories, cursor | `PlaceListResponse` | `bbox=west,south,east,north`; comma-separated categories. |
| GET `/v1/places/{id}` | URL-encoded canonical ID | `Place` | Preserve source-based IDs; 404 if absent. |
| POST `/v1/recommendations` | `RecommendationRequest` | `RecommendationResponse` | Alternatives: each option fits the budget separately. |
| POST `/v1/itineraries` | `ItineraryRequest` | `ItineraryResponse` | Explicit selected `place_ids`; one ordered trip fits the budget. |
| POST `/v1/feedback` | `FeedbackRequest` | `FeedbackResponse` | Anonymous product feedback; never require location. |
| GET `/v1/data-status` | none | `DataStatusResponse` | Source freshness and ingestion status. |

Errors use `ErrorResponse`: `invalid_request` (422), `unsupported_transport` (422), `provider_unavailable` (503), `rate_limited` (429), `internal_error` (500), `not_found` (404). Do not expose stack traces or provider secrets. User location and free-text query must not be logged by default.

## Wire semantics and invariants

- Required request fields have no hidden defaults. Locale is `ru`, `kk`, or `en`; timezone is `Asia/Almaty`. `start_at` is RFC3339 with an explicit offset or Z. Convert that instant into the requested timezone for schedules. Durations are integer seconds; distances are meters.
- `walking` must work initially. Accept `cycling`/`driving` as recognized request values but return `unsupported_transport` until implemented. Never silently route as walking.
- `origin` uses named latitude/longitude. GeoJSON geometry uses `[longitude, latitude]`. A routed `LineString` is allowed only for an actual route calculation. Approximate estimates always have `geometry: null` and nonempty assumptions. Never draw a straight line as a pedestrian route.
- `return_to_origin` covers the complete return trip. A recommendation route covers origin → its place → origin when requested. An itinerary route covers origin → all ordered stops → origin when requested. Travel duration must include every leg. Visit duration is explicitly an estimate.
- `ItineraryRequest.place_ids` is a required ordered list of 1–3 selected IDs. Preserve that order and every selected stop; never silently drop or replace a selected place. If the whole trip cannot meet required constraints or fit the budget, return `no_match` with an explanation. The list length cannot exceed `limit`.
- A recommendation's total is travel + visit. An itinerary's total is complete travel + the sum of every visit. Totals cannot exceed the available budget. Recommendation alternatives are not summed into one itinerary.
- `known` facts require a nonnull value and supporting evidence. `unknown` facts have null value and no evidence claim. `conflicting` facts have null value and at least two evidence IDs. Unknown/conflicting does not mean false. Source freshness is not a truth guarantee.
- Evidence records retain actual source identity, URL, record ID and retrieval time. An LLM is not a source for a place fact. Synthetic evidence and places must be explicitly marked and use `synthetic:` IDs; do not put synthetic data into the live dataset.
- Every place fact/evaluation references evidence in that place. Every recommendation/stop/hit resolves to a returned place. Duplicate IDs, duplicate fact keys and duplicate constraint keys are invalid. Responses contain only their referenced places.
- Constraints are predicates expressed as `{key, value, strength}`. In v0.1, a key matches the same place fact key and comparison is exact JSON value equality (booleans are distinct from numbers). Do not introduce undocumented range or fuzzy semantics. Suggested predicate keys: `indoor`, `wheelchair_accessible`, `child_friendly`, `free_entry`, `open_at_requested_time`. Time-dependent predicates are computed from source schedules for the request instant before evaluation, retaining schedule evidence and an explanatory note.
- Every requested constraint gets one evaluation per candidate. A required constraint must be **known and satisfied**, with its fact evidence cited. An absent or conflicting required fact excludes the place. Preferred unknown/unsatisfied constraints may remain, but must be explained. Relaxing a required constraint requires a new user request.
- `matched` means results meet required constraints; it does not promise three results or all preferences. `partial` means some preferences/desired coverage could not be met, with warnings. `no_match` has empty places/results. `needs_clarification` also has empty results and at least one question. No hidden substitute recommendations may appear in either state.
- `suggested_activity` is an explicitly labelled AI suggestion. `why` cannot invent factual amenities. Retrieval scores are backend-specific and are not confidence probabilities; declare their `score_kind`.

## Python async service ports

The dictionary types below mean validated JSON payloads conforming to the named `$defs`; concrete adapters may use generated typed models. Keep the public signatures stable. Each package owns its implementation and tests; `services/api` owns dependency injection and HTTP status mapping. Import shared types only from the coordinator's agreed contracts package. Do not import another package's private implementation.

```python
from typing import Protocol, Any

JSON = dict[str, Any]  # boundary payload only; use generated named types internally

class PlaceRepository(Protocol):  # packages/city_data
    async def get(self, place_id: str) -> JSON | None: ...  # Place
    async def list_places(
        self, *, bbox: tuple[float, float, float, float] | None = None,
        query: str | None = None, categories: list[str] | None = None,
        cursor: str | None = None, limit: int = 50,
    ) -> JSON: ...  # PlaceListResponse
    async def nearby(
        self, *, origin: JSON, radius_meters: float, limit: int = 100,
    ) -> list[JSON]: ...  # list[Place], stable order by distance then ID
    async def data_status(self) -> JSON: ...  # DataStatusResponse

class Retriever(Protocol):  # packages/retrieval
    async def retrieve(self, request: JSON) -> JSON: ...
    # RetrievalRequest -> RetrievalResponse; exclude only known violated STATIC
    # required predicates. Do not drop unknown context-dependent predicates such
    # as open_at_requested_time; defer them for bounded context enrichment.
    # Respect candidate_limit; deterministic fallback when embeddings unavailable.

class ContextProvider(Protocol):  # packages/city_context
    async def enrich_places(self, *, places: list[JSON], request: JSON) -> JSON: ...
    # RecommendationRequest context -> ContextResult {places, warnings,
    # degraded_services}; derived place facts retain supporting source evidence.
    # Keep input immutable. Unknown provider data stays unknown; attach service
    # failures to ContextResult.degraded_services and user-facing warnings.
    async def estimate_route(
        self, *, origin: JSON, destinations: list[JSON], transport: str,
        return_to_origin: bool, start_at: str,
    ) -> JSON: ...  # Location[] -> RouteEstimate; destinations are ordered.

class RecommendationService(Protocol):  # packages/recommender
    async def recommend(self, request: JSON) -> JSON: ...
    # RecommendationRequest -> RecommendationResponse
    async def build_itinerary(self, request: JSON) -> JSON: ...
    # ItineraryRequest -> ItineraryResponse
```

A backend exception crossing ports must be normalized by the API adapter to `ErrorResponse`; callers must not consume arbitrary provider response dictionaries. The recommender rechecks required constraints and budget **after** context enrichment and routing. Retrieval is candidate selection, not the final policy decision. Source data that cannot satisfy a required dynamic predicate yet must remain unknown; context-aware orchestration can enrich a bounded pool before final exclusion.

The current context wire contract is `ContextResult {places, warnings, degraded_services}`. Weather is a planned explicit contract extension, not an opaque unvalidated payload; do not expose a weather field until its units, provider timestamps, provenance and freshness policy are jointly defined.

No network calls are required by this seed verifier. Future packages must distinguish offline unit tests, synthetic integration fixtures and live provider checks. Required constraint safety, response references and time arithmetic belong in deterministic code, not an LLM prompt.

## Verification

Requires Python >= 3.10. `jsonschema[format-nongpl]==4.26.0` was checked against the [official PyPI JSON endpoint](https://pypi.org/pypi/jsonschema/json). Install into an isolated environment:

```sh
python3 -m venv .venv-contracts
.venv-contracts/bin/pip install -r requirements-contracts.txt
.venv-contracts/bin/python verify_contracts.py
.venv-contracts/bin/python verify_contracts.py --definition RecommendationResponse --instance response.json
```

The verifier checks the schema itself, positive/negative fixtures, timezone-aware timestamps, references, evidence provenance markers, complete travel budgets, return flags, required constraints, and empty no-match results. It does not validate the truth of external facts, geometric route connectivity, operational providers, multilingual answer quality, or a deployed application.
