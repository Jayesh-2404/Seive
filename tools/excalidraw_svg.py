"""Render an .excalidraw scene to a plain SVG.

Only what the Sieve diagram uses: rectangles with centred text, and arrows.
The .excalidraw file stays the source, so edit it in excalidraw.com and re-run:

    python tools/excalidraw_svg.py docs/architecture.excalidraw docs/architecture.svg
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

PAD = 24
CHAR_EM = 0.55


def wrap(text: str, width: float, size: float) -> list[str]:
    limit = max(8, int(width / (size * CHAR_EM)))
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            candidate = f"{line} {word}".strip()
            if len(candidate) <= limit:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def render(scene: dict) -> str:
    elements = [item for item in scene["elements"] if not item.get("isDeleted")]
    texts = {item["containerId"]: item for item in elements
             if item.get("type") == "text" and item.get("containerId")}
    shapes = [item for item in elements if item.get("type") != "text"]

    xs = [item["x"] for item in shapes] + [item["x"] + item["width"] for item in shapes]
    ys = [item["y"] for item in shapes] + [item["y"] + item["height"] for item in shapes]
    x0, y0 = min(xs) - PAD, min(ys) - PAD
    width, height = max(xs) - x0 + PAD, max(ys) - y0 + PAD

    body: list[str] = []
    for item in shapes:
        if item["type"] == "rectangle":
            fill = item.get("backgroundColor", "transparent")
            stroke = item.get("strokeColor", "#1e1e1e")
            body.append(
                f'<rect x="{item["x"]}" y="{item["y"]}" width="{item["width"]}" '
                f'height="{item["height"]}" rx="10" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="{item.get("strokeWidth", 2)}"/>'
            )
            label = texts.get(item["id"])
            if not label:
                continue
            size = label.get("fontSize", 16)
            lines = wrap(label["text"], item["width"] - 16, size)
            cx = item["x"] + item["width"] / 2
            top = item["y"] + item["height"] / 2 - (len(lines) - 1) * size * 0.62
            spans = "".join(
                f'<tspan x="{cx:.1f}" y="{top + i * size * 1.24:.1f}">{escape(line)}</tspan>'
                for i, line in enumerate(lines))
            body.append(
                f'<text font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="{size}" '
                f'fill="{label.get("strokeColor", "#1e1e1e")}" text-anchor="middle">{spans}</text>')
        elif item["type"] == "arrow":
            points = [(item["x"] + px, item["y"] + py) for px, py in item["points"]]
            (x1, y1), (x2, y2) = points[0], points[-1]
            body.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{item.get("strokeColor", "#1e1e1e")}" '
                f'stroke-width="{item.get("strokeWidth", 2)}"/>')
            dx, dy = x2 - x1, y2 - y1
            length = (dx * dx + dy * dy) ** 0.5 or 1
            ux, uy = dx / length, dy / length
            head = 11
            left = (x2 - ux * head - uy * 5, y2 - uy * head + ux * 5)
            right = (x2 - ux * head + uy * 5, y2 - uy * head - ux * 5)
            body.append(
                f'<polygon points="{x2:.1f},{y2:.1f} {left[0]:.1f},{left[1]:.1f} '
                f'{right[0]:.1f},{right[1]:.1f}" fill="{item.get("strokeColor", "#1e1e1e")}"/>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {width} {height}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" '
        f'aria-label="Sieve architecture">\n'
        f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" fill="#ffffff"/>\n'
        + "\n".join(body) + "\n</svg>\n"
    )


def main(source: str, target: str) -> None:
    scene = json.loads(Path(source).read_text(encoding="utf-8"))
    svg = render(scene)
    Path(target).write_text(svg, encoding="utf-8")
    print(f"wrote {target}: {len(scene['elements'])} elements, {len(svg)} bytes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
