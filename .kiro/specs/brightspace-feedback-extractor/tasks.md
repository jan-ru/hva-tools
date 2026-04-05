# Implementation Plan: Brightspace Feedback Extractor

## Overview

Implement a Python CLI tool that connects to an authenticated Playwright browser session, scrapes rubric feedback from Brightspace, aggregates it per group, and writes markdown files. The implementation follows a functional pipeline architecture with Pydantic frozen models, building from pure core modules outward to impure edges and CLI orchestration.

## Tasks

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Create the `brightspace_extractor/` package with `__init__.py` and all module files (`cli.py`, `browser.py`, `navigation.py`, `extraction.py`, `models.py`, `parsing.py`, `aggregation.py`, `serialization.py`)
    - Create empty module files with docstrings describing their purpose
    - _Requirements: 2.4_

  - [x] 1.2 Add project dependencies and configure entry point
    - Add `playwright`, `cyclopts`, `pydantic` as dependencies using `uv add`
    - Add `pytest`, `hypothesis` as dev dependencies using `uv add --dev`
    - Configure the CLI entry point in `pyproject.toml`
    - _Requirements: 2.4_

  - [x] 1.3 Create custom exception classes
    - Define `ExtractorError`, `ConnectionError`, `AuthenticationError`, `NavigationError`, `ExtractionError` in a new `exceptions.py` module
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 1.4 Create the `tests/` directory with empty test files
    - Create `tests/test_parsing.py`, `tests/test_aggregation.py`, `tests/test_serialization.py`, `tests/test_filename.py`, `tests/test_cli.py`, `tests/test_errors.py`
    - _Requirements: 2.4_

- [x] 2. Implement domain models
  - [x] 2.1 Define all Pydantic frozen models in `models.py`
    - Implement `Student`, `Criterion`, `RubricFeedback`, `GroupSubmission`, `AssignmentFeedback`, `AssignmentEntry`, `GroupFeedback`
    - All models use `frozen=True`
    - Use `tuple[...]` for collection fields to enforce immutability
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2_

- [x] 3. Implement parsing module
  - [x] 3.1 Implement `parse_group_submission` and `parse_all_submissions` in `parsing.py`
    - Parse raw dicts (from DOM extraction) into validated Pydantic models
    - Handle missing or malformed fields gracefully
    - _Requirements: 4.2, 4.3, 4.4_

  - [x] 3.2 Write unit tests for parsing
    - Test parsing valid raw dicts into correct models
    - Test rejection of malformed dicts (missing fields, bad types)
    - _Requirements: 4.2, 4.3, 4.4_

- [x] 4. Implement aggregation module
  - [x] 4.1 Implement `aggregate_by_group` in `aggregation.py`
    - Group `AssignmentFeedback` entries by group name
    - Combine feedback from multiple assignments into `GroupFeedback`
    - Order assignments chronologically by submission date within each group
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 4.2 Write property test: Aggregation round-trip preserves all feedback data
    - **Property 1: Aggregation round-trip preserves all feedback data**
    - Generate random `AssignmentFeedback` lists, aggregate by group, flatten back into (group_name, assignment_id, rubric) triples, and verify the set matches the original input exactly
    - **Validates: Requirements 5.1, 5.2**

  - [x] 4.3 Write property test: Aggregated assignments are chronologically ordered
    - **Property 2: Aggregated assignments are chronologically ordered**
    - Generate random `AssignmentFeedback` lists with random dates, aggregate, and verify each `GroupFeedback.assignments` is sorted by `submission_date`
    - **Validates: Requirements 5.3**

  - [x] 4.4 Write unit tests for aggregation edge cases
    - Test single group / single assignment
    - Test groups appearing in only some assignments
    - Test empty input
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement serialization module
  - [x] 6.1 Implement `render_group_markdown` in `serialization.py`
    - Render `GroupFeedback` into a markdown string with group name heading, student names, and per-assignment tables of rubric criteria (name, score, feedback)
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 6.2 Implement `group_to_filename` in `serialization.py`
    - Derive filename from group name: lowercase, spaces to hyphens, `.md` extension
    - _Requirements: 6.7_

  - [x] 6.3 Implement `write_feedback_files` in `serialization.py`
    - Write one markdown file per group to the output directory
    - Create the output directory if it does not exist
    - Return the count of files written
    - _Requirements: 6.5, 6.6_

  - [x] 6.4 Write property test: Markdown output contains all required feedback information
    - **Property 3: Markdown output contains all required feedback information**
    - Generate random `GroupFeedback`, render to markdown, verify the output contains the group name, every student name, every assignment name, formatted date, and every criterion's name, score, and feedback text
    - **Validates: Requirements 6.2, 6.3, 6.4**

  - [x] 6.5 Write property test: Filename derivation produces lowercase hyphenated names
    - **Property 4: Filename derivation produces lowercase hyphenated names**
    - Generate random group name strings, derive filename, verify result is lowercase, contains no spaces, and ends with `.md`
    - **Validates: Requirements 6.7**

  - [x] 6.6 Write unit tests for serialization
    - Test rendering a known `GroupFeedback` and assert exact markdown output
    - Test filename derivation for known inputs
    - Test file writing to a temp directory (correct count, filenames, content)
    - Test directory creation when output dir doesn't exist
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement browser connection and authentication
  - [x] 8.1 Implement `connect_to_browser` in `browser.py`
    - Connect to an existing browser via Playwright CDP using the sync API
    - Raise `ConnectionError` if the CDP endpoint is unreachable
    - _Requirements: 1.1_

  - [x] 8.2 Implement `verify_authentication` in `browser.py`
    - Check for a logged-in indicator on the Brightspace page
    - Return `True` if authenticated, `False` otherwise
    - _Requirements: 1.2, 1.3_

- [x] 9. Implement navigation module
  - [x] 9.1 Implement `navigate_to_class` in `navigation.py`
    - Navigate to the class page using the class identifier
    - Raise `NavigationError` if the class is not found
    - _Requirements: 3.1, 3.2_

  - [x] 9.2 Implement `navigate_to_assignment_submissions` in `navigation.py`
    - Navigate to the assignment submissions page within a class
    - Raise `NavigationError` if the assignment is not found
    - _Requirements: 3.3, 3.4_

- [x] 10. Implement extraction module
  - [x] 10.1 Implement `extract_group_submissions` in `extraction.py`
    - Extract all group submissions from the current assignment page
    - Return a list of raw dicts with group name, student names, rubric data, and date
    - Log warnings for groups with no rubric feedback and continue
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 10.2 Implement `extract_rubric_for_group` in `extraction.py`
    - Extract rubric criteria (name, score, feedback) for a single group submission
    - Handle missing DOM elements gracefully with warnings
    - _Requirements: 4.3, 8.2_

- [x] 11. Implement CLI entry point and pipeline orchestration
  - [x] 11.1 Implement the `extract` command in `cli.py`
    - Wire the full pipeline: connect → verify auth → navigate class → loop assignments → extract → parse → aggregate → serialize → write
    - Accept `class_id`, `assignment_ids`, `--output-dir`, `--cdp-url` arguments via cyclopts
    - Display progress: current assignment name, current group name
    - Display completion summary: number of groups processed and output directory path
    - Handle errors per the design: fail-fast for setup errors, graceful degradation for per-item errors
    - Exit with code 0 on success, 1 on fatal errors
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3_

  - [x] 11.2 Write unit tests for CLI argument parsing
    - Test that valid arguments are accepted
    - Test that missing required arguments produce a usage message and non-zero exit
    - Test that the subcommand structure exists for extensibility
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 12. Implement error handling tests
  - [x] 12.1 Write unit tests for error handling paths
    - Test authentication failure produces correct error message and exit code
    - Test missing assignment logs warning and continues
    - Test navigation timeout logs error and continues
    - Test missing DOM element logs warning with context and continues
    - _Requirements: 1.3, 3.4, 8.1, 8.2, 8.3_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 4 universal correctness properties from the design
- Pure modules (models, parsing, aggregation, serialization) are implemented first so they can be tested independently before wiring to impure browser code
- All dependencies should be installed with `uv add` per project conventions
