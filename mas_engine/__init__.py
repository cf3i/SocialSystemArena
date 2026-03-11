"""General MAS governance engine."""

from .core.runtime import GovernanceRuntime
from .spec.compiler import compile_spec

__all__ = ["compile_spec", "GovernanceRuntime"]
