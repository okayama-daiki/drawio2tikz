from dataclasses import dataclass
from pathlib import Path

DRAWIO_PX_TO_TEX_PT: float

@dataclass(frozen=True)
class LabelLine:
    text: str
    font_size: float | None

@dataclass(frozen=True)
class Label:
    lines: list[LabelLine]
    font_size: float | None

def parse_labels(path: Path) -> dict[str, Label]: ...
def count_pages(path: Path) -> int: ...
def drawio_stem(path: Path) -> str: ...
def parse_label(value: str) -> Label: ...
