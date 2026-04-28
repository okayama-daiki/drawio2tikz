from drawio2tikz.drawio import parse_label


def test_parse_mixed_formatting() -> None:
    label = parse_label(
        '<div><font style="font-size: 40px;"><b>Assign searchers evenly&nbsp;</b></font></div>'
        '<div><font style="font-size: 40px;"><b>to '
        '<font style="color: rgb(255, 128, 0);">unfinished</font> subtrees.</b></font></div>'
    )

    assert label.lines[0].text == (
        r"\fontsize{30.0pt}{36.0pt}\selectfont \textbf{Assign searchers evenly}"
    )
    assert (
        label.lines[1].text
        == r"\fontsize{30.0pt}{36.0pt}\selectfont \textbf{to "
        r"\textcolor[HTML]{FF8000}{unfinished} subtrees.}"
    )


def test_parse_math_label_raw() -> None:
    label = parse_label('<font style="font-size: 28px;">\\(\\times 10\\)</font>')

    assert label.lines[0].text == r"\fontsize{21.0pt}{25.2pt}\selectfont \(\times 10\)"
