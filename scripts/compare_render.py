"""Create paired full-view and region images for human visual review (Pillow)."""
import argparse
import json
from pathlib import Path


def compare(reference, rendered, inventory, output):
    from PIL import Image, ImageOps, ImageDraw
    output = Path(output)
    if output.exists():
        raise ValueError("Choose a new review directory")
    source = Image.open(reference).convert("RGB")
    actual = Image.open(rendered).convert("RGB")
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
            draw.text((10+j*1220, 30), "Approved preview" if j == 0 else "Actual PPT render", fill="black")
            pair.paste(tile, (10+j*1220, 60))
        pairs.append((output/f"comparison-{index:02d}.png", pair))
    output.mkdir(parents=True)
    for target, pair in pairs:
        pair.save(target)
    return [str(p) for p, _ in pairs]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("reference", "render", "inventory", "output-dir"):
        p.add_argument("--"+field, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(compare(a.reference, a.render, json.loads(Path(a.inventory).read_text(encoding="utf-8")), a.output_dir)))
    except (ValueError, KeyError, OSError, ImportError) as exc:
        p.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
