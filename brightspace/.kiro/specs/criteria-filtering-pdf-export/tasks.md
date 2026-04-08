# Implementation Plan: Criteria Filtering & PDF Export

## Overview

Add criteria filtering by subject category and PDF export to the Brightspace Feedback Extractor. The implementation follows the pipeline order: exceptions → filtering module → serialization extensions → PDF export module → CLI wiring → integration tests.

## Tasks

- [x] 1. Add new exception classes to `exceptions.py`
  - Add `ConfigError(ExtractorError)` for category config validation errors
  - Add `PdfExportError(ExtractorError)` for pandoc invocation failures
  - _Requirements: 1.3, 4.6, 4.7_

- [x] 2. Implement the filtering module (`brightspace_extractor/filtering.py`)
  - [x] 2.1 Create `CategoryConfig` model and `load_category_config()` function
    - Define `CategoryConfig(BaseModel, frozen=True)` with `categories: dict[str, tuple[str, ...]]`
    - Implement TOML loading with validation: each category must have at least one non-empty pattern
    - Raise `ConfigError` on malformed/missing files or empty patterns
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Implement `get_patterns()` and `matches_any_pattern()`
    - `get_patterns()`: case-insensitive category lookup, raises `ConfigError` listing available categories if not found
    - `matches_any_pattern()`: case-insensitive substring matching of criterion name against patterns
    - _Requirements: 1.4, 3.4_

  - [x] 2.3 Implement `filter_rubric()` and `filter_assignment_feedback()`
    - `filter_rubric()`: pure function returning new `RubricFeedback` with only matching criteria, preserving order
    - `filter_assignment_feedback()`: maps `filter_rubric` over all submissions in an `AssignmentFeedback`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.4 Write property test: Config validation rejects invalid patterns
    - **Property 1: Config validation rejects invalid patterns**
    - **Validates: Requirements 1.2**
    - Test in `tests/test_filtering.py` using Hypothesis to generate dicts with empty lists/strings

  - [x] 2.5 Write property test: Substring matching is case-insensitive
    - **Property 2: Substring matching is case-insensitive**
    - **Validates: Requirements 1.4**
    - Test in `tests/test_filtering.py` using Hypothesis to generate random names + patterns with mixed case

  - [x] 2.6 Write property test: Filter keeps only matching criteria
    - **Property 3: Filter keeps only matching criteria**
    - **Validates: Requirements 2.1, 2.2, 1.5**
    - Test in `tests/test_filtering.py` using Hypothesis with random `RubricFeedback` + random patterns

  - [x] 2.7 Write property test: Filter preserves criterion order
    - **Property 4: Filter preserves criterion order**
    - **Validates: Requirements 2.4**
    - Test in `tests/test_filtering.py` using Hypothesis with random `RubricFeedback` + random patterns

  - [x] 2.8 Write unit tests for filtering module
    - Test `load_category_config()` happy path with a real TOML file (Req 1.1, 1.3)
    - Test `get_patterns()` with known category and unknown category
    - Test `filter_rubric()` with empty criteria result (Req 2.2)
    - Test `matches_any_pattern()` with multi-category matching (Req 1.5)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2_

- [x] 3. Checkpoint — Ensure all filtering tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Extend serialization for pandoc-compatible output (`brightspace_extractor/serialization.py`)
  - [x] 4.1 Implement `_escape_cell()` and `_build_separator_row()`
    - `_escape_cell()`: strip HTML tags, escape pipe characters with `\|`
    - `_build_separator_row()`: produce pandoc pipe table separator with alignment markers and dash counts proportional to column widths
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 4.2 Implement `render_group_markdown_pandoc()`
    - Render `GroupFeedback` as pandoc-compatible markdown with pipe tables, alignment markers, category label in title
    - Accept `col_widths` tuple and `category_label` parameter
    - _Requirements: 5.1, 5.3, 6.1, 6.2, 6.3_

  - [x] 4.3 Add `suffix` parameter to `group_to_filename()`
    - Extend existing function with optional `suffix: str | None = None` parameter
    - When suffix provided, append `-{suffix.lower()}` before `.md` extension
    - _Requirements: 3.5, 7.2_

  - [x] 4.4 Write property test: Filename includes category suffix
    - **Property 5: Filename includes category suffix**
    - **Validates: Requirements 3.5**
    - Test in `tests/test_serialization_pandoc.py` with random group names + category strings

  - [x] 4.5 Write property test: PDF filename mirrors markdown filename
    - **Property 6: PDF filename mirrors markdown filename**
    - **Validates: Requirements 4.5**
    - Test in `tests/test_serialization_pandoc.py` with random `.md` filenames

  - [x] 4.6 Write property test: Separator row dash counts are proportional to column widths
    - **Property 7: Separator row dash counts are proportional to column widths**
    - **Validates: Requirements 5.1**
    - Test in `tests/test_serialization_pandoc.py` with random `(a, b, c)` positive int tuples

  - [x] 4.7 Write property test: Pandoc output contains alignment markers
    - **Property 8: Pandoc output contains alignment markers**
    - **Validates: Requirements 6.1**
    - Test in `tests/test_serialization_pandoc.py` with random `GroupFeedback`

  - [x] 4.8 Write property test: Cell escaping removes HTML and escapes pipes
    - **Property 9: Cell escaping removes HTML and escapes pipes**
    - **Validates: Requirements 6.2, 6.3**
    - Test in `tests/test_serialization_pandoc.py` with random strings containing HTML + pipes

  - [x] 4.9 Write unit tests for pandoc serialization
    - Test `render_group_markdown_pandoc()` known output against expected string
    - Test default `col_widths` of `(3, 1, 6)` (Req 5.3)
    - Test `_escape_cell()` with known HTML and pipe inputs
    - Test `_build_separator_row()` with known width ratios
    - _Requirements: 5.1, 5.3, 6.1, 6.2, 6.3_

- [x] 5. Checkpoint — Ensure all serialization tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement PDF export module (`brightspace_extractor/pdf_export.py`)
  - [x] 6.1 Implement `check_pandoc_available()`
    - Use `shutil.which("pandoc")` to verify pandoc is on PATH
    - Raise `PdfExportError` with descriptive message if not found
    - _Requirements: 4.6_

  - [x] 6.2 Implement `convert_md_to_pdf()`
    - Shell out to pandoc with `--pdf-engine=typst` and margin variables
    - Raise `PdfExportError` on subprocess failure
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 6.3 Implement `export_all_pdfs()`
    - Convert all `.md` files in directory to PDF
    - Log warnings for individual failures, continue processing remaining
    - Return `(success_count, failure_count)` tuple
    - _Requirements: 4.2, 4.4, 4.7_

  - [x] 6.4 Write unit tests for PDF export module
    - Test `check_pandoc_available()` raises `PdfExportError` when pandoc not found (mock `shutil.which`)
    - Test `convert_md_to_pdf()` constructs correct subprocess command (mock `subprocess.run`)
    - Test `export_all_pdfs()` continues on individual failure and returns correct counts
    - Test PDF files placed in same directory as markdown files (Req 4.4)
    - _Requirements: 4.2, 4.4, 4.5, 4.6, 4.7_

- [x] 7. Checkpoint — Ensure all PDF export tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Wire everything into the CLI (`brightspace_extractor/cli.py`)
  - [x] 8.1 Add new CLI parameters to `extract` command
    - Add `--category` (optional str), `--category-config` (optional str), `--pdf` (bool flag), `--col-widths` (optional str)
    - _Requirements: 3.1, 3.2, 4.1, 5.2_

  - [x] 8.2 Implement CLI validation logic
    - Validate `--category` requires `--category-config` (Req 3.3)
    - Validate `--category` exists in loaded config (Req 3.4)
    - Parse and validate `--col-widths` as three positive numbers (Req 5.5)
    - _Requirements: 3.3, 3.4, 5.5_

  - [x] 8.3 Wire filtering into the pipeline
    - After parsing, before aggregation: load config, get patterns, filter all feedbacks
    - When no `--category`, skip filtering entirely (Req 2.5)
    - _Requirements: 2.5, 7.1_

  - [x] 8.4 Wire serialization mode and PDF export into the pipeline
    - Choose `render_group_markdown_pandoc` when `--pdf` is enabled
    - Pass `col_widths` and `category_label` to pandoc renderer
    - Pass `suffix` to `group_to_filename` when category is set
    - After writing markdown, call `check_pandoc_available()` and `export_all_pdfs()`
    - _Requirements: 4.1, 4.2, 5.1, 7.1, 7.2, 7.3_

  - [x] 8.5 Write unit tests for new CLI parameters and validation
    - Test `--category` without `--category-config` exits with code 1 (Req 3.3)
    - Test unknown category exits with code 1 listing available categories (Req 3.4)
    - Test invalid `--col-widths` format exits with code 1 (Req 5.5)
    - Test `--pdf` flag is accepted without error
    - Test combined `--category --pdf --col-widths` accepted (Req 7.3)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 5.2, 5.5, 7.3_

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- PDF export tests mock `subprocess.run` and `shutil.which` to avoid requiring pandoc in CI
