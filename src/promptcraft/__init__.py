"""PromptCraft CLI Tool - A command-line tool for managing prompt templates."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("promptcraft")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development installations
    __version__ = "0.1.0"

__author__ = "PromptCraft Team"
