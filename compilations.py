"""Compatibility layer for legacy imports of compilation widgets."""

from legopy.ui.compilation_widgets import (
    BaseCompilationFrame,
    CompilationFrame,
    FileItem,
    ScrollableFrame,
    SequenceCompilationFrame,
    SequenceCompilationsManager,
    build_sequence_name,
    determine_sequence_base_name,
)

__all__ = [
    "BaseCompilationFrame",
    "CompilationFrame",
    "FileItem",
    "ScrollableFrame",
    "SequenceCompilationFrame",
    "SequenceCompilationsManager",
    "build_sequence_name",
    "determine_sequence_base_name",
]
