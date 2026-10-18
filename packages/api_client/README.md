# @astana/api-client

Shared generated TypeScript boundary types. Import with `import type { RecommendationRequest, RecommendationResponse } from "@astana/api-client"` in the workspace. No network call, secret, runtime dependency or global state is introduced by this package.

Regenerate from the canonical repository root schema with `python scripts/generate_contracts.py`. CI should use `--check`; regeneration is deterministic and checks all encountered JSON Schema keywords. Never edit `src/generated.ts` by hand.

TypeScript describes the payload structure, unions, local references and fixed coordinate tuple shape. It does **not** enforce schema conditions, bounds, required-constraint satisfaction, timestamps, reference integrity or time budgets. The backend must call `astana_contracts.validate_payload` at service boundaries. Do not treat a TypeScript cast as validation of arbitrary provider or network data.
