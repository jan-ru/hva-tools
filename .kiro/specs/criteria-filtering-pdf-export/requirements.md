# Requirements Document

## Introduction

The Brightspace Feedback Extractor currently extracts all rubric criteria for all assignments and outputs one markdown file per group. Two capabilities are missing:

1. **Criteria filtering by category** — Brightspace rubrics contain criteria from multiple subjects (e.g., MIS, MAC, KMT, CAT) in a single assignment. The user needs to select only criteria belonging to a specific subject category and exclude the rest. Since Brightspace does not natively tag criteria by subject, a configuration file maps criterion name patterns to categories.

2. **PDF export** — The user needs to distribute feedback as PDF files (one per group). PDF generation uses pandoc with typst as the PDF engine. PDFs are A4 format with configurable table column widths.

Both capabilities integrate into the existing functional data pipeline: the filtering step operates on the parsed Pydantic models before aggregation, and the PDF export step operates on the serialized markdown output.

## Glossary

- **Extractor**: The Brightspace Feedback Extractor CLI tool (`brightspace-extractor`)
- **Category_Config**: A TOML configuration file that maps criterion name patterns to subject categories
- **Category**: A subject label (e.g., `MIS`, `MAC`, `KMT`, `CAT`) assigned to rubric criteria via pattern matching
- **Criterion**: A single rubric criterion with a name, score, and feedback text
- **Filter**: The pure function that removes criteria not matching a selected category from a RubricFeedback model
- **Serializer**: The module responsible for rendering GroupFeedback models into markdown strings
- **PDF_Exporter**: The component that converts markdown files to PDF using pandoc with typst
- **Group**: A student group whose feedback is aggregated across assignments into a single output file

## Requirements

### Requirement 1: Category Configuration File

**User Story:** As a teacher, I want to define which rubric criteria belong to which subject category, so that I can filter feedback by subject.

#### Acceptance Criteria

1. THE Category_Config SHALL be a TOML file containing a mapping of category names to lists of criterion name patterns
2. WHEN a Category_Config file is loaded, THE Extractor SHALL validate that each category contains at least one pattern and that all patterns are non-empty strings
3. IF a Category_Config file is malformed or missing required fields, THEN THE Extractor SHALL exit with a descriptive error message and exit code 1
4. THE Category_Config SHALL support substring matching: a criterion matches a category when the criterion name contains any of that category's patterns as a substring (case-insensitive)
5. WHEN a criterion name matches patterns from multiple categories, THE Filter SHALL include that criterion in each matching category

### Requirement 2: Criteria Filtering

**User Story:** As a teacher, I want to filter rubric criteria by subject category, so that each group's feedback contains only the criteria relevant to a specific subject.

#### Acceptance Criteria

1. WHEN a category is specified, THE Filter SHALL remove all criteria from each RubricFeedback whose names do not match any pattern in that category
2. WHEN filtering removes all criteria from a RubricFeedback, THE Filter SHALL produce a RubricFeedback with an empty criteria tuple
3. THE Filter SHALL be a pure function that takes a RubricFeedback and a list of patterns and returns a new RubricFeedback containing only matching criteria
4. THE Filter SHALL preserve the original order of criteria within the filtered RubricFeedback
5. WHEN no category is specified, THE Extractor SHALL include all criteria (no filtering applied)

### Requirement 3: CLI Integration for Filtering

**User Story:** As a teacher, I want to specify a category filter and config file path on the command line, so that I can control which criteria appear in the output.

#### Acceptance Criteria

1. THE Extractor SHALL accept an optional `--category` CLI parameter specifying the category name to filter by
2. THE Extractor SHALL accept an optional `--category-config` CLI parameter specifying the path to the Category_Config TOML file
3. IF `--category` is provided without `--category-config`, THEN THE Extractor SHALL exit with an error message stating that a config file is required
4. IF `--category` specifies a category name not present in the Category_Config, THEN THE Extractor SHALL exit with an error message listing the available categories
5. WHEN `--category` is provided, THE Extractor SHALL append the lowercase category name as a suffix to each output filename (e.g., `fc2a-1-mis.md` instead of `fc2a-1.md`)

### Requirement 4: PDF Export

**User Story:** As a teacher, I want to export feedback as PDF files, so that I can distribute printed or emailed feedback to student groups.

#### Acceptance Criteria

1. THE Extractor SHALL accept an optional `--pdf` CLI flag that enables PDF generation
2. WHEN `--pdf` is enabled, THE PDF_Exporter SHALL generate one PDF file per group by converting the group's markdown file to PDF using pandoc with typst as the PDF engine
3. THE PDF_Exporter SHALL produce A4-sized PDF documents
4. THE PDF_Exporter SHALL place PDF files in the same output directory as the markdown files
5. THE PDF_Exporter SHALL name each PDF file identically to its corresponding markdown file but with a `.pdf` extension
6. IF pandoc is not installed or not found on the system PATH, THEN THE Extractor SHALL exit with a descriptive error message and exit code 1
7. IF pandoc conversion fails for a specific group, THEN THE Extractor SHALL log a warning and continue processing remaining groups

### Requirement 5: PDF Table Formatting

**User Story:** As a teacher, I want the PDF tables to have configurable column widths, so that the feedback text is readable and does not overflow the page.

#### Acceptance Criteria

1. THE PDF_Exporter SHALL render markdown tables with column widths proportional to content type: narrow for Score, medium for Criterion, wide for Feedback
2. THE Extractor SHALL accept an optional `--col-widths` CLI parameter specifying relative column width ratios as three comma-separated numbers (e.g., `3,1,6`)
3. WHEN `--col-widths` is not specified, THE PDF_Exporter SHALL use default column width ratios of `3,1,6` (Criterion: 30%, Score: 10%, Feedback: 60%)
4. THE PDF_Exporter SHALL pass column width configuration to pandoc/typst so that tables respect the specified proportions
5. IF `--col-widths` does not contain exactly three positive numbers, THEN THE Extractor SHALL exit with an error message describing the expected format

### Requirement 6: Markdown Serialization for PDF Compatibility

**User Story:** As a teacher, I want the markdown output to render correctly in pandoc, so that the PDF conversion produces well-formatted documents.

#### Acceptance Criteria

1. WHEN `--pdf` is enabled, THE Serializer SHALL produce markdown tables using pandoc pipe table syntax with column alignment markers (e.g., `:---|:---:|:---`)
2. THE Serializer SHALL ensure that table cells do not contain raw HTML tags, replacing them with plain text equivalents suitable for pandoc
3. THE Serializer SHALL ensure that pipe characters within cell content are escaped so that pandoc parses table structure correctly

### Requirement 7: Filtering and PDF Combined Workflow

**User Story:** As a teacher, I want to filter by category and export to PDF in a single command, so that I can produce subject-specific PDF feedback in one step.

#### Acceptance Criteria

1. WHEN both `--category` and `--pdf` are specified, THE Extractor SHALL first filter criteria by category, then serialize to markdown, then convert to PDF
2. WHEN both `--category` and `--pdf` are specified, THE Extractor SHALL include the category suffix in both the markdown and PDF filenames
3. THE Extractor SHALL support using `--category`, `--pdf`, and `--col-widths` together in any combination
