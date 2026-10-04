# Validation
Initial build and measured experiments: October 4, 2026, Windows, Python 3.11.9, Node 24.17.0.
Backend tests cover actual pipeline behavior; frontend checks include TypeScript and a production Vite build. GitHub Actions repeats the tests and frontend build on Ubuntu with Node 22. Full studies use explicit data download commands and remain separate from CI.
Docker launch configuration is provided; Docker was unavailable on the development machine, so an image build has not been locally verified.
The Chrome control connection failed and the built-in browser was unavailable during development. Browser visual inspection was unavailable; the UI was checked through TypeScript, production builds, and API integration. Evaluation figures are measured plots, not application screenshots.

## Verified checks

- 20 meaningful backend tests passed locally; 48 across all three projects.
- TypeScript check and production Vite build passed; npm audit reported zero known vulnerabilities at installation.
- Live Uvicorn service served the frontend and OpenAPI schema.
- Actual HTTP endpoints served the current and archived experiment manifests/reports.
