# Python Project Defaults

## Package Management
- Always use `uv` for installing Python packages (e.g. `uv pip install`, `uv add`).
- Never use `pip` or `pip install` directly.

## DataFrames
- Default to `pandas` whenever a dataframe library is needed.
- Do not use polars, dask, or other alternatives unless explicitly requested.

## SQL Databases
- Default to `duckdb` whenever a SQL database is needed.
- Do not use sqlite, postgres, or other databases unless explicitly requested.

## Testing
- Use `pytest` for all testing.
- Do not use unittest or other test frameworks unless explicitly requested.
