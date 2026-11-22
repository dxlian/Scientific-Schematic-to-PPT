"""Create paired full-view and region images for human visual review (Pillow)."""
import argparse
import json
from pathlib import Path


def compare(reference, rendered, inventory, output, reference_label="Approved preview", overlay=False):
    from PIL import Image, ImageOps, ImageDraw
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
    if overlay:
        # Allow the normal one-pixel rounding of export height, in either raster.
        relative_error = abs((source.width * actual.height) / (source.height * actual.width) - 1)
        tolerance = 1 / min(source.width, source.height) + 1 / min(actual.width, actual.height)
        if relative_error > tolerance:
            raise ValueError("Reference and render aspect ratios differ. Register the same canvas/crop before overlay.")
    regions = [{"name": "Full view", "box": [0, 0, 1, 1]}] + inventory.get("regions", [])
    pairs = []
    for index, region in enumerate(regions):
        x0, y0, x1, y1 = region["box"]
        if not 0 <= x0 < x1 <= 1 or not 0 <= y0 < y1 <= 1:
            raise ValueError("Invalid normalized crop: " + region["name"])
        tiles = []
        for image in (source, actual):
            box = (round(x0*image.width), round(y0*image.height), round(x1*image.width), round(y1*image.height))
            tiles.append(ImageOps.contain(image.crop(box), (1200, 900)))
        height = max(im.height for im in tiles)
        pair = Image.new("RGB", (2440, height+70), "white")
        draw = ImageDraw.Draw(pair)
        draw.text((10, 8), region["name"], fill="black")
        for j, tile in enumerate(tiles):
            draw.text((10+j*1220, 30), reference_label if j == 0 else "Actual render", fill="black")
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
    return [str(p) for p, _ in pairs]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("reference", "render", "inventory", "output-dir"):
        p.add_argument("--"+field, required=True)
    p.add_argument("--reference-label", default="Approved preview")
    p.add_argument("--overlay", action="store_true", help="Add 50%% overlays for matching canvas aspect ratios")
    a = p.parse_args()
    try:
        print(json.dumps(compare(a.reference, a.render, json.loads(Path(a.inventory).read_text(encoding="utf-8")),
                                 a.output_dir, a.reference_label, a.overlay)))
    except (ValueError, KeyError, OSError, ImportError) as exc:
        p.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
