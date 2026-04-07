"""Category configuration loading and criteria filtering."""

import tomllib
from pathlib import Path

from pydantic import BaseModel

from brightspace_extractor.exceptions import ConfigError
from brightspace_extractor.models import (
    AssignmentFeedback,
    GroupSubmission,
    RubricFeedback,
)


class CategoryConfig(BaseModel, frozen=True):
    """Parsed TOML config: maps category names to pattern lists."""

    categories: dict[str, tuple[str, ...]]


def load_category_config(path: str) -> CategoryConfig:
    """Load and validate a TOML category config file.

    Raises ConfigError if file is missing, malformed, or has empty patterns.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Category config file not found: {path}")

    try:
        raw = config_path.read_bytes()
        data = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Malformed TOML in {path}: {exc}") from exc

    if "categories" not in data:
        raise ConfigError(f"Missing [categories] table in {path}")

    raw_categories = data["categories"]

    if not isinstance(raw_categories, dict):
        raise ConfigError(f"[categories] must be a table in {path}")

    categories: dict[str, tuple[str, ...]] = {}

    for name, patterns in raw_categories.items():
        if not isinstance(patterns, list):
            raise ConfigError(
                f"Category '{name}' must map to a list of patterns in {path}"
            )

        if len(patterns) == 0:
            raise ConfigError(
                f"Category '{name}' must have at least one pattern in {path}"
            )

        for i, pattern in enumerate(patterns):
            if not isinstance(pattern, str) or pattern.strip() == "":
                raise ConfigError(
                    f"Category '{name}', pattern {i}: must be a non-empty string in {path}"
                )

        categories[name] = tuple(patterns)

    return CategoryConfig(categories=categories)


def get_patterns(config: CategoryConfig, category: str) -> tuple[str, ...]:
    """Look up patterns for a category name (case-insensitive).

    Raises ConfigError if category not found, listing available categories.
    """
    lookup = {k.lower(): v for k, v in config.categories.items()}
    patterns = lookup.get(category.lower())
    if patterns is None:
        available = ", ".join(sorted(config.categories.keys()))
        raise ConfigError(
            f"Category '{category}' not found. Available categories: {available}"
        )
    return patterns


def matches_any_pattern(criterion_name: str, patterns: tuple[str, ...]) -> bool:
    """Return True if criterion_name contains any pattern as a substring (case-insensitive)."""
    name_lower = criterion_name.lower()
    return any(p.lower() in name_lower for p in patterns)


def filter_rubric(rubric: RubricFeedback, patterns: tuple[str, ...]) -> RubricFeedback:
    """Return a new RubricFeedback containing only criteria matching any pattern.

    Pure function. Preserves original criterion order.
    """
    filtered = tuple(
        c for c in rubric.criteria if matches_any_pattern(c.name, patterns)
    )
    return RubricFeedback(criteria=filtered)


def filter_assignment_feedback(
    feedback: AssignmentFeedback, patterns: tuple[str, ...]
) -> AssignmentFeedback:
    """Filter all submissions within an AssignmentFeedback.

    Pure function. Returns new AssignmentFeedback with filtered rubrics.
    """
    filtered_submissions = tuple(
        GroupSubmission(
            group_name=sub.group_name,
            students=sub.students,
            rubric=filter_rubric(sub.rubric, patterns),
            submission_date=sub.submission_date,
        )
        for sub in feedback.submissions
    )
    return AssignmentFeedback(
        assignment_name=feedback.assignment_name,
        assignment_id=feedback.assignment_id,
        submissions=filtered_submissions,
    )
