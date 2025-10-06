"""Compatibility layer that forwards helpers to the new services module."""

from legopy.services.media import *  # noqa: F401,F403
from legopy.services.media import __all__ as _MEDIA_ALL

__all__ = _MEDIA_ALL
