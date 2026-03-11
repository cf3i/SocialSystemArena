"""Custom exceptions for the MAS governance engine."""


class SpecError(Exception):
    """Raised when spec loading or validation fails."""


class RuntimeErrorEngine(Exception):
    """Raised when runtime execution fails."""


class AdapterError(Exception):
    """Raised when an agent adapter invocation fails."""
