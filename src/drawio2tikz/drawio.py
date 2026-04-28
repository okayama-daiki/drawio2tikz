from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
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
    text: str
    font_size: float | None


@dataclass(frozen=True)
class Label:
    lines: list[LabelLine]
    font_size: float | None


@dataclass
class TextStyle:
    bold: bool = False
    color: str | None = None
    font_size: float | None = None


@dataclass
class TextRun:
    text: str
    bold: bool = False
    color: str | None = None
    font_size: float | None = None


class DrawioLabelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[list[TextRun]] = [[]]
        self.stack: list[TextStyle] = [TextStyle()]
        self.pushed_tags: list[str] = []

    @property
    def current_style(self) -> TextStyle:
        return self.stack[-1]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
        tag = tag.lower()
        if tag in {"div", "p", "b", "strong", "font", "span", "i", "em", "u"}:
            self._pop_style(tag)

    def handle_data(self, data: str) -> None:
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
            )
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
    root = ET.parse(path).getroot()
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
    root = ET.parse(path).getroot()
    return len(root.findall("diagram"))


def drawio_stem(path: Path) -> str:
    name = path.name
    if name.endswith(".drawio.png"):
        return name[: -len(".drawio.png")]
    if name.endswith(".drawio"):
        return name[: -len(".drawio")]
    return path.stem


def parse_label(value: str) -> Label:
    parser = DrawioLabelParser()
    parser.feed(value)

    lines: list[LabelLine] = []
    font_sizes: list[float] = []

    for runs in parser.lines:
        line_font_sizes = [run.font_size for run in runs if run.font_size]
        font_sizes.extend(line_font_sizes)
        text = _runs_to_tex(runs)
        if not text:
            continue
        line_font_size = max(line_font_sizes) if line_font_sizes else None
        if line_font_size:
            text = f"{_tex_font_size(line_font_size)} {text}"
        lines.append(LabelLine(text=text, font_size=line_font_size))

    raw_font_sizes = [float(size) for size in FONT_SIZE_RE.findall(value)]
    font_sizes.extend(raw_font_sizes)
    return Label(lines=lines, font_size=max(font_sizes) if font_sizes else None)


def _style_from_attrs(attrs: list[tuple[str, str | None]]) -> TextStyle:
    attrs_dict = {name.lower(): value or "" for name, value in attrs}
    style = TextStyle()

    style.color = _css_color_to_html(attrs_dict.get("color"))
    css = attrs_dict.get("style", "")

    if color_match := CSS_COLOR_RE.search(css):
        style.color = _css_color_to_html(color_match.group(1)) or style.color
    if font_size_match := FONT_SIZE_RE.search(css):
        style.font_size = float(font_size_match.group(1))
    if font_weight_match := FONT_WEIGHT_RE.search(css):
        style.bold = font_weight_match.group(1).strip().lower() in {
            "bold",
            "bolder",
            "600",
            "700",
            "800",
            "900",
        }

    return style


def _css_color_to_html(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()

    if rgb := RGB_COLOR_RE.search(value):
        return "".join(f"{int(channel):02X}" for channel in rgb.groups()[:3])
    if hex_color := HEX_COLOR_RE.search(value):
        return hex_color.group(1).upper()
    return None


def _runs_to_tex(runs: list[TextRun]) -> str:
    runs = _trim_runs(runs)
    if not runs:
        return ""

    all_bold = all(run.bold for run in runs)
    text = "".join(_run_to_tex(run, omit_bold=all_bold) for run in runs)
    if all_bold:
        text = rf"\textbf{{{text}}}"
    return text


def _trim_runs(runs: list[TextRun]) -> list[TextRun]:
    trimmed = [TextRun(**run.__dict__) for run in runs]
    while trimmed and not trimmed[0].text.strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1].text.strip():
        trimmed.pop()
    if trimmed:
        trimmed[0].text = trimmed[0].text.lstrip()
        trimmed[-1].text = trimmed[-1].text.rstrip()
    return trimmed


def _run_to_tex(run: TextRun, *, omit_bold: bool = False) -> str:
    text = _tex_escape(run.text)
    if run.color:
        text = rf"\textcolor[HTML]{{{run.color}}}{{{text}}}"
    if run.bold and not omit_bold:
        text = rf"\textbf{{{text}}}"
    return text


def _tex_escape(text: str) -> str:
    text = unescape(text)
    if "\\" in text or "$" in text:
        return text
    return "".join(TEX_SPECIALS.get(char, char) for char in text)


def _tex_font_size(font_size_px: float) -> str:
    size_pt = font_size_px * DRAWIO_PX_TO_TEX_PT
    leading_pt = size_pt * 1.2
    return rf"\fontsize{{{size_pt:.1f}pt}}{{{leading_pt:.1f}pt}}\selectfont"
