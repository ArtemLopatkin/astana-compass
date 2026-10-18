# Verified infrastructure pins

The following versions and commit or manifest digests were resolved from official APIs/registries on 2026-10-18. Update versions, immutable pins and relevant lockfiles together, then rerun checks. Tags are explanatory; immutable digests/commits control execution.

| Component | Version/tag | Immutable reference | Primary source |
|---|---|---|---|
| checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | [Official release](https://github.com/actions/checkout/releases/tag/v7.0.1) |
| setup-uv | v10.3.0 | `1c37ad07a6a961277cf70c0d37d6f313000f5884` | [Official release](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0) |
| setup-node | v7.1.0 | `949feb2413d6458794dcd2491c4babbbce0c15c1` | [Official release](https://github.com/actions/setup-node/releases/tag/v7.1.0) |
| uv executable/image | 0.13.1 | image `sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336` | [Official release](https://github.com/astral-sh/uv/releases/tag/0.13.1), [official container package](https://github.com/astral-sh/uv/pkgs/container/uv) |
| Python image | 3.12-slim-bookworm | `sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258` | [Docker Official Image](https://hub.docker.com/_/python) |
| pgvector image | 0.8.1-pg17 | `sha256:3e8b3adfd27b5707128f60956f62a793c3c9326ea8cfaf0eab7adccb5d700b21` | [Upstream project](https://github.com/pgvector/pgvector), [upstream image](https://hub.docker.com/r/pgvector/pgvector) |
| Node.js | 24.19.0 | setup-node verifies the official distribution | [Official checksum list](https://nodejs.org/dist/v24.19.0/SHASUMS256.txt) |
| TypeScript | 7.0.2 | integrity hashes in `.github/typescript/package-lock.json` | [Official npm registry metadata](https://registry.npmjs.org/typescript/7.0.2) |

GitHub action references were resolved via `api.github.com/repos/{owner}/{repo}/git/ref/tags/{tag}` and annotated tags were dereferenced to commits. Docker digests were read from `Docker-Content-Digest` on official registry manifests. No registry token or provider key is stored in this repository.
