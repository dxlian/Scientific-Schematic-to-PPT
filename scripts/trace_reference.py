"""Trace a local scientific illustration into a draft native PowerPoint scene."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile

from build_pptx import validate_scene


def load_crop(source, crop, max_edge, matte):
    from PIL import Image, ImageOps

    try:
        opened = Image.open(source)
    except Image.DecompressionBombError as exc:
        raise ValueError("Image exceeds the decoder limit. Crop the intended panel before tracing.") from exc
    with opened as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("Select one frame or page and export it as a still image first.")
        oriented = ImageOps.exif_transpose(image)
        width, height = oriented.size
        box = tuple(crop) if crop else (0, 0, width, height)
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError(f"Crop must lie inside the oriented {width} x {height} pixels.")
        rgba = oriented.crop(box).convert("RGBA")
    rgb = Image.new("RGB", rgba.size, "#" + matte)
    rgb.paste(rgba, mask=rgba.getchannel("A"))
    rgb.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return rgb, (width, height), box


def quantize(image, budget):
    import cv2
    import numpy as np

    rgb = np.asarray(image)
    if image.getcolors(maxcolors=budget) is not None:
        palette, labels = np.unique(rgb.reshape(-1, 3), axis=0, return_inverse=True)
        return palette, labels.reshape(rgb.shape[:2])

    filtered = cv2.bilateralFilter(rgb, 5, 10, 1)
    pixels = filtered.reshape(-1, 3).astype(np.float32)
    if len(pixels) > 16000:
        indices = np.random.default_rng(1247).choice(len(pixels), 16000, replace=False)
        sample = pixels[indices]
    else:
        sample = pixels
    distinct = np.unique(sample, axis=0)
    if len(distinct) <= budget:
        centers = distinct
    else:
        cv2.setRNGSeed(1247)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 45, 0.12)
        _, _, centers = cv2.kmeans(sample, budget, None, criteria, 1, cv2.KMEANS_PP_CENTERS)

    # Two real-valued centers can become the same RGB after rounding.
    palette = np.unique(np.rint(centers).astype(np.uint8), axis=0)
    centers = palette.astype(np.float32)
    labels = np.empty(len(pixels), dtype=np.uint8)
    for start in range(0, len(pixels), 4096):
        part = pixels[start:start + 4096]
        distances = np.square(part[:, None, :] - centers).sum(axis=2)
        labels[start:start + len(part)] = distances.argmin(axis=1)
    return palette, labels.reshape(rgb.shape[:2])


def components(mask, epsilon, min_area):
    """Return outer/inner ring sets with opposite winding for native compound paths."""
    import cv2
    import numpy as np

    zoom = 3
    large = cv2.resize(mask, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
    loops, hierarchy = cv2.findContours(large, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return
    hierarchy = hierarchy[0]

    def simplify(index):
        contour = loops[index]
        if cv2.contourArea(contour) < min_area * zoom ** 2:
            return None
        polygon = cv2.approxPolyDP(contour, epsilon * zoom, True)
        if len(polygon) < 3:
            return None
        return (polygon.reshape(-1, 2).astype(np.float64) + 0.5) / zoom

    for index, (_, _, child, parent) in enumerate(hierarchy):
        if parent != -1:
            continue
        outer = simplify(index)
        if outer is None:
            continue
        rings = [outer]
        while child != -1:
            hole = simplify(child)
            if hole is not None:
                rings.append(hole)
            child = hierarchy[child, 0]
        yield rings


def trace_shade(mask, color, scale_x, scale_y, epsilon, min_area, pen_px):
    shapes = []
    detail = None
    count = 0
    stroke = color if pen_px else None
    points_per_mm = 72 / 25.4
    line_pt = pen_px * min(scale_x, scale_y) * points_per_mm
    for rings in components(mask, epsilon, min_area):
        count += 1
        commands = []
        for ring in rings:
            for j, (x, y) in enumerate(ring):
                commands.append(["M" if j == 0 else "L", round(x * scale_x, 5), round(y * scale_y, 5)])
            commands.append(["Z"])
        size_x, size_y = rings[0].max(axis=0) - rings[0].min(axis=0)
        width, height = size_x * scale_x, size_y * scale_y
        tiny = width * height <= 0.9 and max(width, height) <= 3.5
        if tiny and detail is not None and len(detail["commands"]) + len(commands) <= 1800:
            detail["commands"].extend(commands)
            continue
        shape = {"type": "path", "id": f"fill-{color}-{len(shapes) + 1}",
                 "fill": color, "stroke": stroke, "line_pt": line_pt, "commands": commands}
        shapes.append(shape)
        if tiny:
            detail = shape
    return shapes, count


def make_scene(options):
    import numpy as np

    image, size, box = load_crop(options.image, options.crop, options.max_edge, options.matte)
    left, top, right, bottom = box
    width = options.width_mm
    height = width * (bottom - top) / (right - left)
    if not math.isfinite(height) or not (0 < height <= 1422.4):
        raise ValueError("The crop aspect ratio yields a slide over 1422.4 mm high; reduce its target width or adjust the crop.")
    if min(width, height) < 1 / 36000:
        raise ValueError("The requested size is below one DrawingML coordinate unit.")
    scale_x, scale_y = width / image.width, height / image.height
    palette, labels = quantize(image, options.colors)
    counts = np.bincount(labels.ravel(), minlength=len(palette))
    order = np.argsort(-counts, kind="stable")
    hex_colors = [bytes(rgb).hex().upper() for rgb in palette]
    base = hex_colors[order[0]]
    elements = [{"id":"reference-background", "type":"rect", "x":0, "y":0,
                 "w":width, "h":height, "fill":base, "stroke":None}]
    region_count = 0
    shape_count = 0
    for index in order[1:]:
        if counts[index] == 0:
            continue
        color = hex_colors[index]
        shapes, regions = trace_shade((labels == index).astype("uint8"), color,
                                      scale_x, scale_y, options.epsilon, options.min_area, options.seam)
        if shapes:
            elements.append({"id":"shade-" + color, "type":"group", "children":shapes})
        region_count += regions
        shape_count += len(shapes)

    digest = hashlib.sha256()
    with options.image.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    review = {"status":"draft_requires_review", "source_sha256":digest.hexdigest(),
              "oriented_source_size_px":size, "crop_ltrb_px":box, "tracing_grid_px":image.size,
              "color_budget":options.colors, "used_palette":sum(int(n > 0) for n in counts),
              "matte_rgb":options.matte, "max_edge_px":options.max_edge,
              "epsilon_px":options.epsilon, "minimum_area_px2":options.min_area,
              "seam_stroke_px":options.seam, "retained_components":region_count,
              "native_freeforms":shape_count, "label_fidelity":"Outlined only; verify and retype labels.",
              "editable_scope":"Connected fills and shade-grouped small marks. Scientific parts may span several paths."}
    return validate_scene({"version":1, "width_mm":width, "height_mm":height, "background":base,
                           "font_latin":"Times New Roman", "font_ea":"SimSun", "group_all":True,
                           "elements":elements, "trace_review":review})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Local still image file")
    parser.add_argument("--out", required=True, type=Path, help="Output scene JSON")
    parser.add_argument("--width-mm", required=True, type=float, help="Physical width of the selected image region")
    parser.add_argument("--crop", nargs=4, metavar=("LEFT","TOP","RIGHT","BOTTOM"), type=int,
                        help="Oriented source pixels, left/top inclusive and right/bottom exclusive")
    parser.add_argument("--max-edge", type=int, default=480, help="Maximum working edge in pixels (16–1024, default 480)")
    parser.add_argument("--colors", type=int, default=24, help="Maximum colors (2–64, default 24)")
    parser.add_argument("--epsilon", type=float, default=0.23, help="Contour simplification in working pixels")
    parser.add_argument("--min-area", type=float, default=0.30, help="Minimum contour area in working pixels squared")
    parser.add_argument("--seam", type=float, default=0.42, help="Same-color seam stroke in working pixels; 0 disables")
    parser.add_argument("--matte", default="FFFFFF", help="Six-digit RGB background for transparent pixels")
    options = parser.parse_args()
    options.matte = options.matte.removeprefix("#").upper()
    if not re.fullmatch("[0-9A-F]{6}", options.matte):
        parser.error("--matte requires a six-digit RGB color")
    if not (0 < options.width_mm <= 1422.4 and 16 <= options.max_edge <= 1024 and 2 <= options.colors <= 64):
        parser.error("Use a positive width up to 1422.4 mm, a 16–1024 pixel edge and a 2–64 color budget.")
    if not all(math.isfinite(n) and n >= 0 for n in (options.epsilon, options.min_area, options.seam)):
        parser.error("Contour and seam parameters must be finite and nonnegative.")
    if options.image.resolve() == options.out.resolve():
        parser.error("Use a different file for the output scene.")
    try:
        scene = make_scene(options)
        options.out.parent.mkdir(parents=True, exist_ok=True)
        staged = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=options.out.parent,
                                             prefix=".trace-", suffix=".json", delete=False) as output:
                staged = Path(output.name)
                json.dump(scene, output, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                output.write("\n")
            staged.replace(options.out)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    except ImportError as exc:
        parser.exit(2, f"Missing optional tracing dependency ({exc}). Install Pillow, numpy and opencv-python-headless.\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot trace image: {exc}\n")
    review = scene["trace_review"]
    print(f"Draft scene: {review['retained_components']} components, {review['native_freeforms']} native freeforms.")
    print("Review the geometry and replace outlined lettering with verified native labels before approval.", file=sys.stderr)


if __name__ == "__main__":
    main()
