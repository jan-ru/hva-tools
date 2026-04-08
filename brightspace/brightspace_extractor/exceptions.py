"""Custom exceptions for the Brightspace Feedback Extractor."""


class ExtractorError(Exception):
    """Base exception for the extractor."""


class ConnectionError(ExtractorError):
    """Failed to connect to browser via CDP."""


class AuthenticationError(ExtractorError):
    """Browser session is not authenticated."""


class NavigationError(ExtractorError):
    """Failed to navigate to a Brightspace page."""


class ExtractionError(ExtractorError):
    """Failed to extract expected data from a page."""


class ConfigError(ExtractorError):
    """Invalid or missing category configuration."""


class PdfExportError(ExtractorError):
    """PDF conversion failed."""
