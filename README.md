# drawio2tikz

`drawio2tikz` is a thin wrapper around [`svg2tikz`](https://github.com/xyz2tex/svg2tikz) that converts draw.io diagrams to TikZ.

## Features

- Converts either a single draw.io page or all pages.
- Preserves label colors, bold text, font sizes, and simple line breaks.
- **Ignores draw.io font family names**, so the output uses the host LaTeX document font.
- Removes draw.io SVG CSS that `svg2tikz` cannot parse, including `light-dark(...)` from draw.io's dark mode color scheme.
- Restores draw.io labels emitted as SVG `foreignObject` elements, which draw.io exports as HTML fragments.

## Requirements

- Python 3.10 or newer.
- `drawio` CLI available on `PATH`.

## Install

### Using Homebrew (macOS)

```sh
brew install drawio2tikz
```

### Using uv

```sh
uv tool install drawio2tikz
```

### Development

```sh
uv sync
uv run drawio2tikz --help
```

## Usage

Convert one page:

```sh
drawio2tikz path/to/figure.drawio -o out
```

Keep the sanitized intermediate SVG:

```sh
drawio2tikz path/to/figure.drawio -o out --keep-svg --svg-dir out/svg
```

Convert all pages in a `.drawio` file:

```sh
drawio2tikz path/to/multipage.drawio --all-pages -o out
```

---

- LaTeX document using generated TikZ should load:

```tex
\usepackage{xcolor}
\usepackage{tikz}
```

For arbitrary large font sizes, use a scalable font such as:

```tex
\usepackage{mlmodern}
```

## How It Works

`svg2tikz` cannot consume draw.io HTML text directly because draw.io exports it as SVG `foreignObject`. This tool reads the original `.drawio` XML, reconstructs text labels, injects them into the exported SVG as normal SVG text, sanitizes unsupported CSS, and then calls `svg2tikz.convert_svg()`.

Font family names from draw.io are intentionally ignored. The generated TikZ uses LaTeX commands for color, boldness, and size, while letting the host document choose the actual font.

## License

MIT
