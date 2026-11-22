"""Make an editable Origin project in a fresh external Origin session."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import tempfile


def load_xy(args):
    with args.csv.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        names = reader.fieldnames or []
        if len(names) != len(set(names)) or args.x not in names or args.y not in names:
            raise ValueError("Supply unique CSV headers and valid x and y column names")
        points = []
        for row_number, row in enumerate(reader, 2):
            if None in row or None in row.values():
                raise ValueError(f"Inconsistent field count at CSV row {row_number}")
            try:
                pair = (float(row[args.x]), float(row[args.y]))
            except ValueError as exc:
                raise ValueError(f"Missing or nonnumeric x/y at CSV row {row_number}") from exc
            if not all(map(math.isfinite, pair)):
                raise ValueError(f"Nonfinite x/y at CSV row {row_number}")
            points.append(pair)
    if len(points) < 2:
        raise ValueError("At least two finite observations are required")
    x, y = map(list, zip(*points))
    if args.fit_linear and min(x) == max(x):
        raise ValueError("A linear fit requires distinct x values")
    if args.sg:
        window, degree = args.sg
        if not (3 <= window <= len(x) and window % 2 and 0 <= degree < window):
            raise ValueError("SG requires an odd window between 3 and n, and 0 <= order < window")
        steps = [b - a for a, b in zip(x, x[1:])]
        if steps[0] <= 0 or not all(math.isclose(s, steps[0], rel_tol=1e-6) for s in steps):
            raise ValueError("SG requires uniformly spaced increasing x; retain and resolve irregular samples explicitly")
    return x, y


def origin_text(label):
    # Format only Chinese runs. The object's base font handles Latin text and
    # parentheses in unit expressions. Literal backslashes are doubled.
    def chinese(char):
        return bool(re.match(r"[\u2e80-\u303f\u3400-\u9fff\uf900-\ufaff\uff01-\uff60\U00020000-\U0002fa1f]", char))
    result = []
    for is_chinese, chars in itertools.groupby(label, key=chinese):
        run = "".join(chars).replace("\\", "\\\\")
        result.append(r"\f:SimSun(" + run + ")" if is_chinese else run)
    return "".join(result)


def create_project(op, args, x, y, target):
    sheet = op.new_sheet("w", lname="Experimental data")
    sheet.name = "Curve"
    sheet.from_list(0, x, lname=args.x, axis="X")
    sheet.from_list(1, y, lname=args.y, axis="Y")
    curves = [(1, "Raw", "#465A70")]
    metadata = {"source": args.csv.name, "source_sha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
                "source_columns": [args.x, args.y], "rows": len(x), "origin_version": op.org_ver(),
                "smoothing": None, "fit": None}
    if args.sg:
        window, degree = args.sg
        sheet.cols = 3
        sheet.lt_exec(f"smooth iy:=col(2) method:=sg npts:={window} polyorder:={degree} "
                      "boundary:=reflect oy:=col(3);")
        smooth = sheet.to_list(2)
        if len(smooth) != len(x) or not all(math.isfinite(v) and abs(v) < 1e300 for v in smooth):
            raise RuntimeError("Origin did not return a complete smoothed column")
        sheet.set_label(2, "Savitzky-Golay")
        curves.append((2, "Savitzky-Golay", "#217F77"))
        metadata["smoothing"] = {"input": "raw Y", "engine": "Origin smooth", "window_points": window,
                                 "order": degree, "boundary": "reflect"}
    if args.fit_linear:
        fit = op.LinearFit()
        fit.set_data(sheet, 0, 1)
        result = fit.result()["Parameters"]
        slope = float(result["Slope"]["Value"])
        intercept = float(result["Intercept"]["Value"])
        if not all(map(math.isfinite, (slope, intercept))):
            raise RuntimeError("Origin returned a nonfinite linear fit")
        fitted = [slope * xi + intercept for xi in x]
        index = len(curves) + 1
        sheet.from_list(index, fitted, lname="Linear fit", axis="Y")
        curves.append((index, "Linear fit", "#B95E46"))
        mean_y = sum(y) / len(y)
        ss_total = sum((value - mean_y) ** 2 for value in y)
        ss_res = sum((value - pred) ** 2 for value, pred in zip(y, fitted))
        metadata["fit"] = {"input": "raw XY, all rows", "engine": "Origin LinearFit", "weights": "equal",
                           "intercept_fixed": False, "slope": slope, "intercept": intercept,
                           "r_squared": 1 - ss_res / ss_total if ss_total else None}
    graph = op.new_graph(lname="Experimental curve")
    layer = graph[0]
    for index, label, color in curves:
        plot = layer.add_plot(sheet, coly=index, colx=0, type="y" if label == "Raw" else "l")
        if not plot:
            raise RuntimeError(f"Could not create Origin plot {label}")
        plot.color = color
    layer.rescale()
    layer.lt_exec('legend -r; layer.x.label.font=font(Times New Roman); '
                  'layer.y.label.font=font(Times New Roman); xb.font=font(Times New Roman); '
                  'yl.font=font(Times New Roman); legend.font=font(Times New Roman);')
    layer.label("xb").text = origin_text(args.xlabel or args.x)
    layer.label("yl").text = origin_text(args.ylabel or args.y)
    layer.label("legend").text = "\n".join(r"\l(" + str(i) + ") " + name
                                           for i, (_, name, _) in enumerate(curves, 1))
    notes = op.new_notes("Processing")
    notes.text = json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False)
    graph.activate()
    if not op.save(str(target)) or not target.is_file() or not target.stat().st_size:
        raise RuntimeError("Origin did not save the project")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--x", required=True)
    parser.add_argument("--y", required=True)
    parser.add_argument("--xlabel")
    parser.add_argument("--ylabel")
    parser.add_argument("--sg", type=int, nargs=2, metavar=("WINDOW", "ORDER"))
    parser.add_argument("--fit-linear", action="store_true")
    args = parser.parse_args()
    x, y = load_xy(args)
    output = args.output.resolve()
    if output.suffix.lower() != ".opju" or output.exists():
        parser.error("Choose a new .opju output file")
    try:
        import originpro as op
    except ImportError as exc:
        parser.exit(2, f"External Python with originpro and a licensed Origin installation is required: {exc}\n")
    if not op.oext:
        parser.error("Run this CLI from a fresh external Python process for an isolated Origin session")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as stage:
        project = Path(stage) / output.name
        try:
            # External originpro creates OriginExt.Application() on first access.
            # Calling attach() would select the interactive user's session.
            create_project(op, args, x, y, project)
        finally:
            op.exit()
        project.rename(output)


if __name__ == "__main__":
    main()
