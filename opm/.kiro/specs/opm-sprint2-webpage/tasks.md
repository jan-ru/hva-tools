# Implementation Plan: OPM Sprint 2 Webpage

## Overview

Build a Quarto static website for Sprint 2 of the OPM project. The implementation creates the project configuration, rubric files, submissions directory structure, and the main `sprint2.qmd` page organized as a tabset with one tab per student group. Python is used for any validation/testing scripts.

## Tasks

- [x] 1. Set up Quarto project configuration
  - Create `_quarto.yml` with `project.type: website`, navbar entries for Home and Sprint 2, HTML theme `cosmo`, and reference to `styles.css`
  - Create `index.qmd` with a minimal home page (YAML front matter + brief description)
  - Create `styles.css` with base styles for group tabs and assignment sections
  - _Requirements: 1.1, 1.2, 1.3, 8.4, 10.1_

  - [ ]* 1.1 Write property test for site config navbar (Property 9)
    - **Property 9: Site config navbar includes Sprint 2**
    - **Validates: Requirements 1.2, 10.1, 10.2**
    - Parse `_quarto.yml` with PyYAML and assert that at least one navbar entry has `href: sprint2.qmd`

- [x] 2. Create rubric directory structure and placeholder rubric files
  - Create `sprint-2/opm-sprint-2-dma/rubric.md` with placeholder assessment criteria for the DMA assignment
  - Create `sprint-2/opm-sprint-2-meetplan-tbv-datacollectie/rubric.md` with placeholder assessment criteria for the Meetplan assignment
  - Each rubric should include at least two named criteria sections (used later for feedback alignment)
  - _Requirements: 5.3, 5.4, 8.2_

  - [ ]* 2.1 Write property test for rubric file existence and path correctness (Property 5)
    - **Property 5: Rubric link correctness per assignment**
    - **Validates: Requirements 5.1, 5.2, 5.6**
    - Assert both rubric files exist at their exact expected paths using `os.path.exists`

- [x] 3. Create submissions directory structure for student groups
  - Create `submissions/sprint2/FC2E-01/` with placeholder input files: `FC2E-01_dma_report.pdf` and `FC2E-01_meetplan.pdf` (empty placeholder files)
  - Create `submissions/sprint2/FC2E-03/` with placeholder input files: `FC2E-03_dma_report.pdf` and `FC2E-03_meetplan.pdf`
  - Create `submissions/sprint2/FC2F-01/` with placeholder input files: `FC2F-01_dma_report.pdf`, `FC2F-01_dma_supplementary.pdf`, and `FC2F-01_meetplan.pdf`
  - _Requirements: 4.1, 4.2, 4.3, 8.3_

  - [ ]* 3.1 Write property test for input file uniqueness across groups (Property 4)
    - **Property 4: Input file uniqueness across groups**
    - **Validates: Requirements 4.3**
    - Parse `sprint2.qmd` (once created) and assert that no input file path appears in more than one group's section

- [x] 4. Create `sprint2.qmd` with tabset structure and group content
  - Write YAML front matter with `title: "Sprint 2 — OPM Sprint 2 DMA & Meetplan tbv Datacollectie"`
  - Write Overview section with sprint description and category name "Sprint 2"
  - Open a `{.panel-tabset}` div with one `## {group-id}` tab per group (FC2E-01, FC2E-03, FC2F-01)
  - Within each tab, add `### OPM Sprint 2 DMA` and `### OPM Sprint 2 - Meetplan tbv Datacollectie` sections separated by `---`
  - Within each assignment section add: `#### Input Files` (group-specific links), `#### Rubric` (link to correct `rubric.md`), `#### Prompts` (at least one prompt with identifier and full text — no placeholder `[...]` text)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 5.1, 5.2, 5.6, 6.1, 6.2, 6.4, 8.1_

  - [ ]* 4.1 Write property test for tab count matching group count (Property 1)
    - **Property 1: Tab count matches group count**
    - **Validates: Requirements 2.1, 2.3**
    - Parse `sprint2.qmd` source and assert the number of `## FC*` headings inside the tabset equals the number of defined groups

  - [ ]* 4.2 Write property test for both assignments present in every group tab (Property 2)
    - **Property 2: Both assignments present in every group tab**
    - **Validates: Requirements 3.1, 3.3**
    - Parse `sprint2.qmd` and assert each group tab contains headings for both assignment names

  - [ ]* 4.3 Write property test for input files present per group per assignment (Property 3)
    - **Property 3: Input files present per group per assignment**
    - **Validates: Requirements 4.1, 4.2**
    - Parse `sprint2.qmd` and assert each group+assignment section contains at least one link under `submissions/sprint2/{group-id}/`

  - [ ]* 4.4 Write property test for no placeholder prompt text (Property 6)
    - **Property 6: Prompt completeness and no placeholder text**
    - **Validates: Requirements 6.1, 6.2, 6.4**
    - Read `sprint2.qmd` source and assert no text matching the pattern `\[.*?\]` appears inside a Prompts section

- [ ] 5. Add feedback sections for FC2E-01 (both assignments)
  - Under FC2E-01's DMA section, add `#### Feedback` with per-criterion subsections matching `sprint-2/opm-sprint-2-dma/rubric.md` criteria, plus an `##### Overall` subsection with date, evaluated files, and feedback text
  - Under FC2E-01's Meetplan section, add `#### Feedback` with per-criterion subsections matching `sprint-2/opm-sprint-2-meetplan-tbv-datacollectie/rubric.md` criteria, plus an `##### Overall` subsection
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 5.1 Write property test for feedback completeness and rubric alignment (Property 8)
    - **Property 8: Feedback completeness and rubric alignment**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
    - Parse `sprint2.qmd` and for each group+assignment that has a Feedback section, assert the set of criterion subsection names matches the rubric criteria; assert Overall subsection contains date, evaluated files, and feedback text

- [ ] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Validate shared prompt text consistency
  - Verify that prompts with the same identifier (e.g., `P-DMA-01`) have identical text across all group tabs for the same assignment in `sprint2.qmd`
  - If any shared prompt text differs, normalize it to a single canonical version
  - _Requirements: 6.3_

  - [ ]* 7.1 Write property test for shared prompt text consistency (Property 7)
    - **Property 7: Shared prompt text consistency**
    - **Validates: Requirements 6.3**
    - Parse `sprint2.qmd`, collect all prompt texts keyed by prompt ID per assignment, and assert identical text for each ID that appears in multiple groups

- [ ] 8. Validate rendered HTML output
  - Run `quarto render` and assert `_site/sprint2.html` is produced without errors
  - Parse the generated HTML with `BeautifulSoup` and assert: one `<div role="tabpanel">` (or equivalent Bootstrap tab structure) per group, both assignment headings present in each tab, all `<a href>` links for rubrics point to the correct paths, no broken internal links
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 8.1 Write property test for valid HTML output (Property 10)
    - **Property 10: Valid HTML output**
    - **Validates: Requirements 9.1, 9.3**
    - Parse `_site/sprint2.html` with `html.parser` and assert the document has a `<html>` root, a `<body>`, and no unclosed tags reported by the parser

- [ ] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties defined in the design document
- Placeholder input files (empty PDFs or `.txt` stubs) are sufficient for structure validation; real student files are placed by the content author
- Python test scripts should use `pytest` and `PyYAML`/`BeautifulSoup4` for parsing
