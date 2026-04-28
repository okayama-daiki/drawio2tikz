"""Convert diagrams.net/draw.io diagrams to TikZ."""

from .converter import ConversionResult, ConvertOptions, convert

__all__ = ["ConversionResult", "ConvertOptions", "convert"]
