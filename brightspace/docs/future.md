# Future Ideas

Potential improvements and features not yet implemented.

## Extension Enhancements

- Publish to Chrome Web Store / Edge Add-ons
- Add category selector dropdown in the popup UI (currently category filtering requires the `category` query param)
- Offline mode: cache last extraction results in extension storage
- Batch extraction: extract multiple assignments in one go

## API Enhancements

- Authentication/rate limiting for public deployment
- HTTPS termination via reverse proxy (Caddy/nginx) in Docker Compose
- WebSocket endpoint for progress updates on long extractions
- OpenAPI schema auto-generation is already available at `/docs` (FastAPI built-in)

## Deployment

- CI/CD pipeline for automated Docker image builds
- Multi-architecture Docker images (amd64 + arm64)
- Hetzner VPS deployment with Caddy for automatic HTTPS

## Data Export

- DuckDB export: write extracted data to a DuckDB database for SQL queries
- CSV/Excel export from the extension popup
- Webhook integration: POST results to a configurable URL
