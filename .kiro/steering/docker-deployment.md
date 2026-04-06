---
inclusion: manual
---

# Docker Deployment

## Container Runtime
- Use `docker` for all containerization (not podman unless explicitly requested).

## Development Containers
- Always provide a `Dockerfile.dev` for development builds and testing.
- Mount source code as a volume; do not copy source into dev containers.
- Run all builds and tests inside the dev container, never locally.

## Production Images
- Use multi-stage builds to keep production images small.
- Base Python images on `python:3.12-slim`.
- Base Node/TypeScript images on `node:22-slim`.
- Never include dev dependencies, test files, or `.env` files in production images.

## Conventions
- Name images as `<project-name>-dev` and `<project-name>-prod`.
- Always include a `.dockerignore` excluding `.venv`, `node_modules`, `.git`, `__pycache__`.
- Pin base image versions; avoid `latest` tags.
