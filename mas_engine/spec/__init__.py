"""Spec layer: templates, compilation, and validation."""

from .compiler import (
    compile_spec,
    compile_spec_obj,
    compile_spec_text,
    dump_spec_yaml,
    export_ir_json,
    load_spec_text,
)
from .templates import SUPPORTED_PATTERNS, build_spec_template
from .validators import validate_spec

__all__ = [
    "compile_spec",
    "compile_spec_obj",
    "compile_spec_text",
    "load_spec_text",
    "dump_spec_yaml",
    "export_ir_json",
    "validate_spec",
    "SUPPORTED_PATTERNS",
    "build_spec_template",
]
