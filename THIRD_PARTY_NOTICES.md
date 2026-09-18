# Dependency/license review

No third-party source was copied or vendored. Runtime packages are installed by
uv from the pinned lock; their distributions retain their own notices. This is a
bounded dependency/license review, not a legal opinion or vulnerability audit.

Direct dependencies inspected from installed distribution metadata:

- Pydantic 2.13.5 and pydantic-core 2.46.5: MIT.
- Playwright 1.63.0: Apache-2.0. Chromium is downloaded separately and includes
  Chromium and bundled third-party notices; no browser binary is redistributed.
- Optional OpenAI SDK 2.54.0: Apache-2.0.
- Development: pytest 9.1.1 (MIT), pytest-asyncio 1.4.0 (Apache-2.0), Ruff 0.16.8 (MIT).

Transitives in this environment: annotated-types, anyio, h11, jiter, pluggy,
iniconfig, pyee, typing-inspection (MIT); greenlet (MIT AND PSF-2.0);
typing-extensions (PSF-2.0); httpcore/httpx/idna (BSD-3-Clause); Pygments
(BSD-2-Clause); packaging (Apache-2.0 OR BSD-2-Clause); sniffio (MIT OR
Apache-2.0); distro (Apache-2.0); certifi (MPL-2.0); tqdm (MPL-2.0 AND MIT).
No modifications are made to these packages. Review the installed notices and
redistribution requirements if shipping binaries or modified dependencies.

OpenAdapt was inspected only as a reference; its root package license is MIT.
The source checkout includes isolated AGPL benchmark deployment material, which
is not used. See [ADR 001](docs/adr-001-surface.md) for the pinned inspected commit.
