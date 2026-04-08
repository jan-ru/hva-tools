# TypeScript Project Defaults

## Package Management
- Always use `pnpm` for installing packages (e.g. `pnpm add`, `pnpm install`).
- Do not use `npm` or `yarn` directly unless explicitly requested.

## Runtime
- Use `tsx` for running TypeScript files directly during development.

## Typing & Data Models
- Use `zod` for runtime validation, schema definitions, and type inference.
- Do not use plain interfaces or manual validation for structured data unless explicitly requested.

## Testing
- Use `vitest` for all testing.
- Do not use jest or other test frameworks unless explicitly requested.

## Code Quality
- Use `husky` + `lint-staged` for git hooks.
- Use `eslint` for linting and `prettier` for formatting.

## SQL Databases
- Default to `duckdb` (via `duckdb-async`) whenever a SQL database is needed.
- Do not use sqlite, postgres, or other databases unless explicitly requested.
