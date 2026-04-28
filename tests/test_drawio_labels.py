"""Tests for draw.io label parsing."""

from drawio2tikz.drawio import parse_label


def test_parse_mixed_formatting() -> None:
    """Test parsing labels with mixed formatting."""
    label = parse_label(
        '<div><font style="font-size: 40px;"><b>Assign searchers evenly&nbsp;</b></font></div>'
        '<div><font style="font-size: 40px;"><b>to '
        '<font style="color: rgb(255, 128, 0);">unfinished</font> subtrees.</b></font></div>',
    )

    expected_first = r"\fontsize{30.0pt}{36.0pt}\selectfont \textbf{Assign searchers evenly}"
    assert label.lines[0].text == expected_first

    expected_second = (
        r"\fontsize{30.0pt}{36.0pt}\selectfont \textbf{to "
        r"\textcolor[HTML]{FF8000}{unfinished} subtrees.}"
    )
    assert label.lines[1].text == expected_second


def test_parse_math_label_raw() -> None:
    """Test parsing math labels in raw mode."""
    label = parse_label('<font style="font-size: 28px;">\\(\\times 10\\)</font>')

    expected = r"\fontsize{21.0pt}{25.2pt}\selectfont \(\times 10\)"
    assert label.lines[0].text == expected
