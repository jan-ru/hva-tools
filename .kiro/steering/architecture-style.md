# Architecture Style

## Data Modeling
- Use Pydantic `BaseModel` with `frozen=True` for all domain models (immutable data classes).
- Define domain objects as typed, validated, immutable structures (e.g., Student, Group, Assignment, Criterion).

## Programming Style
- Follow a functional programming style: pure functions, no mutation, data flows through transformations.
- Each pipeline step should be a pure function that takes immutable data in and returns new immutable data out.

## Data Pipeline Pattern
- Treat the application as a data pipeline: scrape → parse into Pydantic models → aggregate → serialize to output.
- Output serialization (markdown, duckdb, etc.) should be separate pure functions that operate on the same domain models.
- Keep domain models and extraction logic decoupled from serialization logic for extensibility.
