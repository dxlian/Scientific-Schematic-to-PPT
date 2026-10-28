"""Check planned geometric coverage; this is not a visual-quality score."""
import argparse
import json
import math
from pathlib import Path
from build_pptx import bounds, walk, validate_scene


def union(objects):
    boxes = [visible_bounds(e) for e in objects]
    x = min(b[0] for b in boxes)
    y = min(b[1] for b in boxes)
    return [x, y, max(b[0]+b[2] for b in boxes)-x, max(b[1]+b[3] for b in boxes)-y]


def cubic_extrema(p0, p1, p2, p3):
    d0, d1, d2 = p1-p0, p2-p1, p3-p2
    a, b, c = d0-2*d1+d2, 2*(d1-d0), d0
    scale = max(abs(a), abs(b), abs(c))
    if scale == 0: return []
    a, b, c = a/scale, b/scale, c/scale
    if a == 0:
        roots = [-c/b] if b else []
    else:
        discriminant = b*b-4*a*c
        if discriminant < 0: return []
        # This quadratic form avoids cancellation when one root is near zero.
        q = -0.5*(b+math.copysign(math.sqrt(discriminant), b))
        roots = [q/a, c/q] if q else [-b/(2*a)]
    return [t for t in roots if 0 < t < 1]


def visible_bounds(e):
    """Geometric bounds, excluding stroke/arrow extents and off-curve handles."""
    if e["type"] == "group": return union(e["children"])
    if e["type"] != "path": return bounds(e)
    points = []
    current = start = None
    for command in e["commands"]:
        if command[0] == "M":
            current = start = command[1:3]
        elif command[0] == "L":
            end = command[1:3]
            points.extend([current, end])
            current = end
        elif command[0] == "C":
            controls = [current, command[1:3], command[3:5], command[5:7]]
            points.extend([current, controls[3]])
            for axis in (0, 1):
                for t in cubic_extrema(*(p[axis] for p in controls)):
                    weights = [(1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3]
                    points.append([sum(w*p[i] for w, p in zip(weights, controls)) for i in (0, 1)])
            current = controls[3]
        elif command[0] == "Z":
            points.extend([current, start])
            current = start
    if not points: return bounds(e)
    xs, ys = zip(*points)
    return [min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)]


def close(actual, expected, tolerance, label):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid tolerance: " + label)
    if len(actual) != len(expected) or any(not math.isfinite(v) for v in expected):
        raise ValueError("Invalid expected geometry: " + label)
    if any(abs(a-b) > tolerance for a, b in zip(actual, expected)):
        raise ValueError("Geometry differs from approved inventory: " + label)


def check(scene, inventory):
    validate_scene(scene)
    if inventory.get("version") != 1 or not inventory.get("features"):
        raise ValueError("Inventory needs version 1 and nonempty features")
    close([scene["width_mm"], scene["height_mm"]], inventory["canvas_mm"], .001, "canvas")
    objects = {e["id"]: e for e in walk(scene["elements"])}
    for feature in inventory["features"]:
        ids = feature["object_ids"]
        if not ids or any(i not in objects for i in ids):
            raise ValueError("Missing required objects: " + feature["name"])
        selected = [objects[i] for i in ids]
        close(union(selected), feature["expected_bbox_mm"], feature.get("tolerance_mm", 1), feature["name"])
        unique = {e["id"]: e for e in walk(selected)}
        curves = sum(c[0] == "C" for e in unique.values() for c in e.get("commands", []))
        if curves < feature.get("min_cubic_segments", 0):
            raise ValueError("Required curved detail was simplified: " + feature["name"])
    for arrow in inventory.get("arrows", []):
        e = objects.get(arrow["object_id"])
        if not e or e["type"] != "line":
            raise ValueError("Missing arrow: " + arrow["object_id"])
        for field in ("start", "end"):
            close(e[field], arrow[field+"_mm"], arrow.get("tolerance_mm", 1), arrow["object_id"])
        for flag in ("arrow_start", "arrow_end"):
            if flag in arrow and bool(e.get(flag)) != bool(arrow[flag]):
                raise ValueError("Changed arrow direction: " + arrow["object_id"])
    return {"features_checked": len(inventory["features"]), "arrows_checked": len(inventory.get("arrows", [])), "visual_review_required": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene", required=True)
    p.add_argument("--inventory", required=True)
    a = p.parse_args()
    try:
        print(json.dumps(check(json.loads(Path(a.scene).read_text(encoding="utf-8")), json.loads(Path(a.inventory).read_text(encoding="utf-8")))))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        p.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
