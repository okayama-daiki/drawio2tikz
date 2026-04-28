"""Parse and handle labels from draw.io diagrams."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DRAWIO_PX_TO_TEX_PT = 0.75
FONT_SIZE_RE = re.compile(r"font-size:\s*([0-9.]+)px", re.IGNORECASE)
CSS_COLOR_RE = re.compile(r"color:\s*([^;]+)", re.IGNORECASE)
RGB_COLOR_RE = re.compile(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[^)]+)?\)", re.IGNORECASE)
HEX_COLOR_RE = re.compile(r"#([0-9a-fA-F]{6})")
FONT_WEIGHT_RE = re.compile(r"font-weight:\s*([^;]+)", re.IGNORECASE)

TEX_SPECIALS = {
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
}


@dataclass(frozen=True)
class LabelLine:
    """A single line of text in a label."""

    text: str
    font_size: float | None


@dataclass(frozen=True)
class Label:
    """A label extracted from a draw.io cell."""

    lines: list[LabelLine]
    font_size: float | None


@dataclass
class TextStyle:
    """Text styling attributes."""

    bold: bool = False
    color: str | None = None
    font_size: float | None = None


@dataclass
class TextRun:
    """A run of text with associated styling."""

    text: str
    bold: bool = False
    color: str | None = None
    font_size: float | None = None


class DrawioLabelParser(HTMLParser):
    """Parse HTML labels from draw.io cells into TeX-compatible text."""

    def __init__(self) -> None:
        """Initialize the parser."""
        super().__init__(convert_charrefs=True)
        self.lines: list[list[TextRun]] = [[]]
        self.stack: list[TextStyle] = [TextStyle()]
        self.pushed_tags: list[str] = []

    @property
    def current_style(self) -> TextStyle:
        """Get the current text style."""
        return self.stack[-1]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle start of HTML tags."""
        tag = tag.lower()
        if tag in {"div", "p"}:
            self._newline()
            self._push_style(tag, attrs)
        elif tag == "br":
            self._newline()
        elif tag in {"b", "strong"}:
            self._push_style(tag, attrs, force_bold=True)
        elif tag in {"font", "span", "i", "em", "u"}:
            self._push_style(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        """Handle end of HTML tags."""
        tag = tag.lower()
        if tag in {"div", "p", "b", "strong", "font", "span", "i", "em", "u"}:
            self._pop_style(tag)

    def handle_data(self, data: str) -> None:
        """Handle text data."""
        text = data.replace("\xa0", " ")
        if not text:
            return
        style = self.current_style
        self.lines[-1].append(
            TextRun(
                text=text,
                bold=style.bold,
                color=style.color,
                font_size=style.font_size,
            ),
        )

    def _newline(self) -> None:
        if self.lines[-1]:
            self.lines.append([])

    def _push_style(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        *,
        force_bold: bool = False,
    ) -> None:
        style = TextStyle(**self.current_style.__dict__)
        parsed = _style_from_attrs(attrs)
        style.color = parsed.color or style.color
        style.font_size = parsed.font_size or style.font_size
        style.bold = style.bold or parsed.bold or force_bold
        self.stack.append(style)
        self.pushed_tags.append(tag)

    def _pop_style(self, tag: str) -> None:
        if tag not in self.pushed_tags:
            return
        index = len(self.pushed_tags) - 1 - self.pushed_tags[::-1].index(tag)
        del self.pushed_tags[index]
        del self.stack[index + 1]


def parse_labels(path: Path) -> dict[str, Label]:
    """Parse all labels from a draw.io file."""
    root = ET.parse(path).getroot()  # noqa: S314
    labels: dict[str, Label] = {}

    for cell in root.findall(".//mxCell"):
        cell_id = cell.get("id")
        value = cell.get("value")
        if not cell_id or not value:
            continue
        label = parse_label(value)
        if label.lines:
            labels[cell_id] = label

    return labels


def count_pages(path: Path) -> int:
    """Count the number of pages in a draw.io file."""
    root = ET.parse(path).getroot()  # noqa: S314
    return len(root.findall("diagram"))


def drawio_stem(path: Path) -> str:
    """Extract the stem of a draw.io file name."""
    name = path.name
    if name.endswith(".drawio.png"):
        return name[: -len(".drawio.png")]
    if name.endswith(".drawio"):
        return name[: -len(".drawio")]
    return path.stem


def parse_label(value: str) -> Label:
    """Parse a single label from HTML string."""
    parser = DrawioLabelParser()
    parser.feed(value)

    lines: list[LabelLine] = []
    font_sizes: list[float] = []

    for runs in parser.lines:
        line_font_sizes = [run.font_size for run in runs if run.font_size]
        font_sizes.extend(line_font_sizes)
        line_text = _text_from_runs(runs)
        if line_text:
            first_font = line_font_sizes[0] if line_font_sizes else None
            lines.append(LabelLine(text=line_text, font_size=first_font))

    if not lines:
        return Label(lines=[], font_size=None)

    label_font_size = font_sizes[0] if font_sizes else None
    return Label(lines=lines, font_size=label_font_size)


def _text_from_runs(runs: list[TextRun]) -> str:
    parts: list[str] = []
    for run in runs:
        text = run.text
        for char, replacement in TEX_SPECIALS.items():
            text = text.replace(char, replacement)
        if run.bold:
            text = rf"\textbf{{{text}}}"
        if run.color:
            text = rf"\textcolor[HTML]{{{run.color}}}{{{text}}}"
        parts.append(text)
    return "".join(parts)


def _style_from_attrs(attrs: list[tuple[str, str | None]]) -> TextStyle:
    style = TextStyle()
    attrs_dict = dict(attrs)
    if "style" in attrs_dict:
        css = attrs_dict["style"] or ""
        if match := FONT_SIZE_RE.search(css):
            style.font_size = float(match.group(1))
        if match := CSS_COLOR_RE.search(css):
            color_str = match.group(1).strip()
            if color_match := RGB_COLOR_RE.search(color_str):
                r, g, b = color_match.groups()
                style.color = f"{int(r):02X}{int(g):02X}{int(b):02X}"
            elif hex_match := HEX_COLOR_RE.search(color_str):
                style.color = hex_match.group(1).upper()
    if "color" in attrs_dict and (
        hex_match := HEX_COLOR_RE.search(attrs_dict["color"] or "")
    ):
        style.color = hex_match.group(1).upper()
    if "weight" in attrs_dict and attrs_dict["weight"] in {"bold", "700"}:
        style.bold = True
    return style
