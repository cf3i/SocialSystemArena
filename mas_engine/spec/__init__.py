"""Spec layer: templates, compilation, and validation."""

from .compiler import compile_spec, export_ir_json
from .templates import SUPPORTED_PATTERNS, build_spec_template
from .validators import validate_spec

__all__ = [
    "compile_spec",
    "export_ir_json",
    "validate_spec",
    "SUPPORTED_PATTERNS",
    "build_spec_template",
]
