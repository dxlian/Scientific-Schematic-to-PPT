"""Place existing vector PDF panels on one page at the requested physical dimensions."""
import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import tempfile

import fitz


def compose(spec_path, output):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    width, height = map(float, spec["size_mm"])
    if not all(math.isfinite(d) and d > 0 for d in [width, height]) or not spec["panels"]:
        raise ValueError("Supply a positive finite canvas size and at least one panel")
    pt = 72/25.4
    with ExitStack() as stack:
        result = stack.enter_context(fitz.open())
        page = result.new_page(width=width*pt, height=height*pt)
        for panel in spec["panels"]:
            x, y, w, h = map(float, panel["box_mm"])
            if not (x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= width and y+h <= height):
                raise ValueError(f"Panel outside the canvas: {panel['file']}")
            src = stack.enter_context(fitz.open(spec_path.parent / panel["file"]))
            number = panel.get("page", 1)
            if not src.is_pdf or type(number) is not int or not 1 <= number <= len(src):
                raise ValueError("A PDF and a valid one-based page number are required")
            target = fitz.Rect(x*pt, y*pt, (x+w)*pt, (y+h)*pt)
            page.show_pdf_page(target, src, number-1, keep_proportion=True)
        output = Path(output)
        if output.exists():
            raise ValueError(f"Choose a new output directory: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent) as temp:
            stage = Path(temp) / "output"
            stage.mkdir()
            result.save(stage / "figure.pdf", garbage=3, deflate=True)
            with fitz.open(stage / "figure.pdf") as saved:
                saved[0].get_pixmap(dpi=600, alpha=False).save(stage / "figure.png")
            stage.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        compose(args.spec, args.out)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")
