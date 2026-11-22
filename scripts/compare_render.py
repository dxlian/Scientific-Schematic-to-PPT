"""Create full-view and region proofs, optionally measuring registered RGB renderings."""
import argparse
import json
from pathlib import Path


def pixel_metrics(reference, rendered):
    """Measure an equally sized RGB crop on its native pixel grid, before proof resizing."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ImportError("--metrics requires NumPy and OpenCV (opencv-python-headless or opencv-python)") from exc

    source = np.asarray(reference)
    actual = np.asarray(rendered)
    differences = cv2.absdiff(source, actual).mean(axis=2, dtype=np.float32)
    foreground = ~np.all(source > 242, axis=2)
    source_edges = cv2.Canny(cv2.cvtColor(source, cv2.COLOR_RGB2GRAY), 45, 105) > 0
    actual_edges = cv2.Canny(cv2.cvtColor(actual, cv2.COLOR_RGB2GRAY), 45, 105)
    close_edges = cv2.dilate(actual_edges, np.ones((3, 3), dtype=np.uint8)) > 0
    edge_count = int(source_edges.sum())
    return {"rgb_mae_0_255": round(float(differences.mean()), 3),
            "nonwhite_mae_0_255": round(float(differences[foreground].mean()), 3) if foreground.any() else None,
            "edge_recall_1px": round(float(np.count_nonzero(source_edges & close_edges)) / max(1, edge_count), 4),
            "reference_edges": edge_count, "nonwhite_pixels": int(foreground.sum())}


def compare(reference, rendered, inventory, output, reference_label="Approved preview", overlay=False, metrics=False):
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    output = Path(output)
    if output.exists():
        raise ValueError("Choose a new review directory")
    with Image.open(reference) as image:
        source = image.convert("RGBA")
    with Image.open(rendered) as image:
        actual = image.convert("RGBA")
    # Transparencies in user-supplied exports often have hidden black RGB values.
    source = Image.alpha_composite(Image.new("RGBA", source.size, "white"), source).convert("RGB")
    actual = Image.alpha_composite(Image.new("RGBA", actual.size, "white"), actual).convert("RGB")
    if metrics and source.size != actual.size:
        raise ValueError("Pixel metrics require the same registered canvas and pixel dimensions. "
                         f"Reference {source.size}, render {actual.size}. Supply matching rasters before measuring.")
    if overlay:
        # Allow the normal one-pixel rounding of export height, in either raster.
        relative_error = abs((source.width * actual.height) / (source.height * actual.width) - 1)
        tolerance = 1 / min(source.width, source.height) + 1 / min(actual.width, actual.height)
        if relative_error > tolerance:
            raise ValueError("Reference and render aspect ratios differ. Register the same canvas/crop before overlay.")
    regions = [{"name": "Full view", "box": [0, 0, 1, 1]}] + inventory.get("regions", [])
    proof_font = None
    if any(not name.isascii() for name in [reference_label] + [region["name"] for region in regions]):
        for family in ("simsun.ttc", "NotoSerifCJK-Regular.ttc", "NotoSansCJK-Regular.ttc"):
            try:
                proof_font = ImageFont.truetype(family, 15)
                break
            except OSError:
                continue

    def caption(draw, position, label):
        try:
            draw.text(position, label, fill="black", font=proof_font)
        except UnicodeEncodeError:
            # Older Pillow bitmap fonts accept Latin-1 only. Retain the identifier in the proof.
            draw.text(position, label.encode("ascii", "backslashreplace").decode("ascii"), fill="black")

    pairs = []
    measurements = []
    for index, region in enumerate(regions):
        x0, y0, x1, y1 = region["box"]
        if not 0 <= x0 < x1 <= 1 or not 0 <= y0 < y1 <= 1:
            raise ValueError("Invalid normalized crop: " + region["name"])
        crops = []
        for image in (source, actual):
            box = (round(x0*image.width), round(y0*image.height), round(x1*image.width), round(y1*image.height))
            if box[0] == box[2] or box[1] == box[3]:
                raise ValueError("Crop rounds to zero pixels: " + region["name"])
            crops.append(image.crop(box))
        if metrics:
            measurements.append({"name": region["name"], "box": region["box"], "box_px": box,
                                 **pixel_metrics(*crops)})
        tiles = [ImageOps.contain(crop, (1200, 900)) for crop in crops]
        height = max(im.height for im in tiles)
        pair = Image.new("RGB", (2440, height+70), "white")
        draw = ImageDraw.Draw(pair)
        caption(draw, (10, 8), region["name"])
        for j, tile in enumerate(tiles):
            caption(draw, (10+j*1220, 30), reference_label if j == 0 else "Actual render")
            pair.paste(tile, (10+j*1220, 60))
        pairs.append((output/f"comparison-{index:02d}.png", pair))
        if overlay:
            # Compare in the source crop's coordinates, displayed at proof size.
            registered = tiles[1].resize(tiles[0].size, Image.Resampling.LANCZOS)
            blended = Image.blend(tiles[0], registered, alpha=0.5)
            pairs.append((output/f"overlay-{index:02d}.png", blended))
    output.mkdir(parents=True)
    for target, pair in pairs:
        pair.save(target)
    files = [str(p) for p, _ in pairs]
    if metrics:
        target = output / "metrics.json"
        report = {"reference": Path(reference).name, "render": Path(rendered).name,
                  "canvas_px": source.size, "regions": measurements}
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        files.append(str(target))
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("reference", "render", "inventory", "output-dir"):
        p.add_argument("--"+field, required=True)
    p.add_argument("--reference-label", default="Approved preview")
    p.add_argument("--overlay", action="store_true", help="Add 50%% overlays for matching canvas aspect ratios")
    p.add_argument("--metrics", action="store_true", help="Measure color and edge agreement on equal, pre-registered pixel grids")
    a = p.parse_args()
    try:
        print(json.dumps(compare(a.reference, a.render, json.loads(Path(a.inventory).read_text(encoding="utf-8")),
                                 a.output_dir, a.reference_label, a.overlay, a.metrics)))
    except (ValueError, KeyError, OSError, ImportError) as exc:
        p.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
