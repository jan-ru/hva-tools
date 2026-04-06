# Output Format

Each group gets one markdown file named after the group (lowercase, spaces replaced with hyphens).

## Example: `team-alpha.md`

```markdown
# Team Alpha

**Students:** Alice Johnson, Bob Smith

## Assignment 1 — Project Proposal

**Date:** 2025-09-15

| Criterion | Score | Feedback |
|---|---|---|
| Problem Statement | 8.0 | Clear and well-scoped |
| Literature Review | 7.5 | Could include more recent sources |
| Methodology | 9.0 | Solid approach |

## Assignment 2 — Midterm Report

**Date:** 2025-10-20

| Criterion | Score | Feedback |
|---|---|---|
| Progress | 8.5 | On track |
| Writing Quality | 7.0 | Some sections need proofreading |
| Technical Depth | 8.0 | Good analysis of results |
```

## Structure

1. Top-level heading: group name
2. Student names listed after the heading
3. One section per assignment, ordered chronologically by submission date
4. Each assignment section contains:
   - Assignment name as a second-level heading
   - Submission date
   - Rubric criteria table with columns: Criterion, Score, Feedback

## Filename Derivation

| Group Name | Filename |
|---|---|
| Team Alpha | `team-alpha.md` |
| Group 3 | `group-3.md` |
| My Cool Team | `my-cool-team.md` |

The rule: lowercase the name, replace spaces with hyphens, append `.md`.
