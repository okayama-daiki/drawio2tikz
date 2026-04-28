from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from .drawio import DRAWIO_PX_TO_TEX_PT, Label, LabelLine

STYLE_ELEMENT_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL)
STYLE_ATTR_RE = re.compile(r'\sstyle="[^"]*"')
SWITCH_FOREIGN_OBJECT_RE = re.compile(
    r"<switch>\s*<foreignObject\b.*?</foreignObject>\s*<image\s+([^>]*)/>\s*</switch>",
    re.DOTALL,
)
ATTR_RE = re.compile(r'([:\w-]+)="([^"]*)"')


@dataclass(frozen=True)
class SVGStats:
    remaining_foreign_objects: int
    text_nodes: int


def sanitize_svg(raw_svg: Path, sanitized_svg: Path, labels: dict[str, Label]) -> SVGStats:
    text = raw_svg.read_text(encoding="utf-8")
    text = _restore_foreign_object_text(text, labels)
    text = STYLE_ELEMENT_RE.sub("", text)
    text = STYLE_ATTR_RE.sub("", text)
    sanitized_svg.write_text(text, encoding="utf-8")
    return SVGStats(
        remaining_foreign_objects=text.count("foreignObject"),
        text_nodes=text.count("<text"),
    )


def _restore_foreign_object_text(svg_text: str, labels: dict[str, Label]) -> str:
    def replace(match: re.Match[str]) -> str:
        cell_id = _nearest_cell_id(svg_text, match.start())
        if not cell_id or cell_id not in labels:
            return match.group(0)
        replacement = _text_svg_for_label(labels[cell_id], _parse_attrs(match.group(1)))
        return replacement or match.group(0)

    return SWITCH_FOREIGN_OBJECT_RE.sub(replace, svg_text)


def _nearest_cell_id(svg_text: str, offset: int) -> str | None:
    marker = 'data-cell-id="'
    start = svg_text.rfind(marker, 0, offset)
    if start == -1:
        return None
    start += len(marker)
    end = svg_text.find('"', start)
    if end == -1:
        return None
    return svg_text[start:end]


def _parse_attrs(raw_attrs: str) -> dict[str, str]:
    return {name: html.unescape(value) for name, value in ATTR_RE.findall(raw_attrs)}


def _text_svg_for_label(label: Label, image_attrs: dict[str, str]) -> str:
    try:
        x = float(image_attrs["x"])
        y = float(image_attrs["y"])
        width = float(image_attrs["width"])
        height = float(image_attrs["height"])
    except (KeyError, ValueError):
        return ""

    if not label.lines:
        return ""

    font_size = label.font_size or height / len(label.lines) * 0.8
    font_size = max(8.0, min(font_size, height * 0.95))
    line_height = font_size * 1.2
    first_baseline = y + height / 2 - (len(label.lines) - 1) * line_height / 2 + font_size * 0.35
    cx = x + width / 2

    text_nodes = []
    for index, line in enumerate(label.lines):
        line_text = _line_text_with_fallback_size(line, font_size)
        text_nodes.append(
            f'<text x="{cx:.3f}" y="{first_baseline + index * line_height:.3f}" '
            f'text-anchor="middle" font-size="{font_size:.3f}px">'
            f"{html.escape(line_text, quote=False)}</text>"
        )
    return "".join(text_nodes)


def _line_text_with_fallback_size(line: LabelLine, font_size_px: float) -> str:
    if line.font_size:
        return line.text
    size_pt = font_size_px * DRAWIO_PX_TO_TEX_PT
    leading_pt = size_pt * 1.2
    return rf"\fontsize{{{size_pt:.1f}pt}}{{{leading_pt:.1f}pt}}\selectfont {line.text}"
