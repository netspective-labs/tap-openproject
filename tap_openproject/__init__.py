"""tap-openproject package - Singer tap for OpenProject API.

Built with the Meltano Singer SDK.
"""

from __future__ import annotations

__version__ = "0.2.0"
__author__ = "surveilr Team"

from tap_openproject.tap import TapOpenProject

__all__ = ["TapOpenProject"]
