# HTTP integration foundation

The API composes shared validated contracts and `DefaultRecommendationService` with independently owned data, retrieval and context adapters. All `/v1` endpoints in `CONTRACTS.md` are implemented. `/docs` provides OpenAPI from the same canonical schema.

## Run

From repository root, `uv sync --locked`, then `uv run uvicorn astana_api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log`. `ASTANA_MODE=fixture` is the default. It serves **three synthetic places only**, distance-based candidate selection (query intent is ignored), and an explicitly approximate route with no geometry. These adapters are integration tooling, not a second implementation of team modules.

`ASTANA_MODE=live` loads the team factories below. Missing imports/configuration result in liveness 200 and readiness/API 503. It never substitutes fixture data. All returned place payloads reject synthetic markers in live mode. In live mode readiness requires a populated source with a successful import (ready or explicitly stale), a positive total count, and a valid non-synthetic sample place. It does not probe the retrieval index. Essential readiness probes repository data status; it does not guarantee every external provider is up. Optional generation failures produce a clearly reported deterministic fallback. This is not a deployed public service.

## Factory contract for teams

Factories may return their resource directly or an awaitable. Define keyword arguments exactly:

```python
# Team 01
create_repository(*, config: dict) -> PlaceRepository
create_retriever(*, repository: PlaceRepository, config: dict) -> Retriever
# Team 02
create_context(*, config: dict) -> ContextProvider
```

Default imports are `astana_city_data`, `astana_retrieval`, `astana_city_context`. `config` currently contains `mode='live'` and `timezone='Asia/Almaty'`. Adapters read their own documented server-side env. Implement `aclose()` for async resource cleanup (or synchronous `close()`). Factories must release partial resources if initialization fails before returning. The API closes successfully created resources at shutdown. Ports are defined in `astana_contracts`; root schemas remain canonical. Teams propose their workspace member/dependency changes for coordinator integration.

## AI configuration

Set `LLM_PROVIDER=openai` and `LLM_MODEL` plus `OPENAI_API_KEY`, or `LLM_PROVIDER=nvidia` and `LLM_MODEL` plus `NVIDIA_API_KEY`. `LLM_API_KEY` is an alternate server-only key. `none` disables external generation. Values are loaded from environment; copying `.env.example` does not automatically load secrets. Model names have no guessed default. The optional provider gets a reduced grounding payload; it does not get the user's coordinate object. See `packages/ai_providers/README.md` and `docs/ai/TRAINING.md` for its precise privacy and generation boundaries. No live model call or training is implied by passing mocked tests.

## Operational boundaries

- 32 KiB request body cap including chunked requests; 10-second receive deadline.
- 2,000-character query limit and 20 constraints, up to 100 list results, fixed CORS origins.
- Bounded concurrency and request timeout, safe error envelopes, generated request IDs, no input/provider text in error responses.
- `X-Astana-Data-Mode`, `X-Request-ID`, `Cache-Control: no-store`; disable HTTP access logs because list URL queries can carry private text.
- Anonymous feedback is an explicitly submitted, bounded **in-memory** queue. It is lost on restart. No durable analytics/export or automatic training from feedback is implemented.
- The app has no per-user rate limit or public edge protection; shared concurrency limits are local per worker. Configure ingress quotas/body/time limits before a public deployment.
- Actual route availability, real POI ingestion, weather, embeddings, natural-language constraint extraction, frontend and persistent feedback belong to subsequent integrations. No endpoint silently infers hard constraints from prose.

Run `uv run pytest tests/integration` for API tests; full workspace checks are in `scripts/check.sh`.
