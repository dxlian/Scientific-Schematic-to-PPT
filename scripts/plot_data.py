"""Render a CSV line/scatter figure from a JSON spec. Paths in the spec are relative to it."""
import argparse
from contextlib import contextmanager
import csv
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.mathtext import MathTextParser
import numpy as np

from precision_annotations import add_features, line_geometry, place_labels, review_insets


def read_table(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)) or any(not h.strip() for h in fields):
            raise ValueError("Supply a CSV with named, unique headers")
        rows = list(reader)
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError("Empty data or inconsistent CSV row width")
    return rows


def column(rows, name):
    values = []
    for i, row in enumerate(rows, 2):
        raw = row[name].strip()
        if raw.lower() in ("", "nan", "na", "n/a"):
            values.append(np.nan)
            continue
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"Row {i}, {name}: expected numeric value, got {raw!r}") from exc
        if not math.isfinite(value):
            raise ValueError(f"Row {i}, {name}: infinite value")
        values.append(value)
    return np.array(values)


def error_column(rows, field):
    """Return symmetric magnitudes (N,) or paired lower/upper magnitudes (2,N)."""
    if isinstance(field, str):
        values = column(rows, field)
    elif isinstance(field, dict) and set(field) == {"lower", "upper"} and all(
            isinstance(name, str) for name in field.values()):
        values = np.stack([column(rows, field["lower"]), column(rows, field["upper"])])
    else:
        raise ValueError("yerr must name a column or specify lower and upper column names")
    if np.any(values < 0):
        raise ValueError("Negative error magnitude; use nonnegative distances from the estimate")
    return values


def set_fonts(spec):
    names = [spec.get("font_latin", "Times New Roman"), spec.get("font_cjk", "SimSun")]
    for name in names:
        font_manager.findfont(name, fallback_to_default=False)
    matplotlib.rcParams.update({"font.family": names, "font.size": 9, "axes.labelsize": 9,
                                "pdf.fonttype": 42, "ps.fonttype": 42, "axes.linewidth": 0.7,
                                "mathtext.fontset": "custom", "mathtext.rm": names[0],
                                "mathtext.it": names[0] + ":italic", "mathtext.bf": names[0] + ":bold"})
    return names


@contextmanager
def bilingual_math(cjk_font):
    """Supply the selected CJK face to MathText while retaining its math parser and font commands."""
    # Matplotlib's plain Text supports a family fallback list. Its custom MathText
    # fontset instead opens a single face, including for prose outside the dollar signs.
    mapping = MathTextParser._font_type_mapping
    original = mapping["custom"]
    fallback_path = font_manager.findfont(cjk_font, fallback_to_default=False)

    class BilingualFonts(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cjk = font_manager.get_font(fallback_path)

        def _get_glyph(self, fontname, font_class, sym):
            if len(sym) == 1 and unicodedata.east_asian_width(sym) in ("W", "F"):
                codepoint = ord(sym)
                if self.cjk.get_char_index(codepoint):
                    return self.cjk, codepoint, False
            return super()._get_glyph(fontname, font_class, sym)

    # Parser cache keys omit both the custom glyph lookup and the fallback face.
    MathTextParser._parse_cached.cache_clear()
    mapping["custom"] = BilingualFonts
    try:
        yield
    finally:
        mapping["custom"] = original
        MathTextParser._parse_cached.cache_clear()


def draw_panel(ax, panel, rows):
    ax.set(xlabel=panel["xlabel"], ylabel=panel["ylabel"])
    for axis in ("x", "y"):
        scale = panel.get(axis + "scale", "linear")
        if scale not in ("linear", "log"):
            raise ValueError("Supported scales are linear and log")
        getattr(ax, "set_" + axis + "scale")(scale)
    sources, report, artists, errors = {}, {}, {}, {}
    for series in panel["series"]:
        key = series["id"]
        if key in sources:
            raise ValueError(f"Duplicate series id {key}")
        x, y = (column(rows, series[k]) for k in ("x", "y"))
        valid = np.isfinite(x) & np.isfinite(y)
        if not valid.any():
            raise ValueError(f"No drawable data for {key}")
        if ((ax.get_xscale() == "log" and np.any(x[valid] <= 0)) or
                (ax.get_yscale() == "log" and np.any(y[valid] <= 0))):
            raise ValueError(f"Non-positive observations on a log axis: {key}")
        kind = series.get("kind", "line")
        if kind not in ("line", "scatter"):
            raise ValueError(f"Unsupported kind {kind}")
        err = None
        if "yerr" in series:
            if not series.get("error_definition", "").strip():
                raise ValueError(f"Specify error_definition for {key} (e.g. supplied SD)")
            err = error_column(rows, series["yerr"])
        options = {"color": series.get("color"), "label": series.get("label", key),
                   "linestyle": "none" if kind == "scatter" else series.get("linestyle", "-"),
                   "marker": series.get("marker", "o" if kind == "scatter" else None),
                   "linewidth": series.get("line_pt", 1.1), "markersize": series.get("marker_pt", 3)}
        if kind == "line":
            px, py, markers = line_geometry(x, y, ax.get_xscale(), ax.get_yscale())
            options["markevery"] = markers
        else:
            px, py = x, y
        artist, = ax.plot(px, py, **options)
        artists[key] = artist
        if err is not None:
            known = np.isfinite(err) if err.ndim == 1 else np.isfinite(err).all(axis=0)
            if ax.get_yscale() == "log":
                lower = err if err.ndim == 1 else err[0]
                invalid = np.flatnonzero(valid & known & (lower >= y))
                if invalid.size:
                    i = invalid[0]
                    raise ValueError(f"Series {key!r}, CSV row {i + 2}: lower error endpoint "
                                     f"({y[i]:g} - {lower[i]:g}) is non-positive on a log y axis")
            if err.ndim == 2:
                err[:, ~known] = np.nan
            ax.errorbar(x, y, yerr=err, fmt="none", color=artist.get_color(), capsize=2, linewidth=.7)
        sources[key] = (x, y)
        errors[key] = err
        report[key] = {"rows": len(rows), "valid_xy": int(valid.sum()), "missing_xy": int((~valid).sum()),
                       "error_definition": series.get("error_definition"),
                       "error_columns": series.get("yerr"),
                       "missing_error_at_valid_xy": int((valid & ~known).sum()) if err is not None else None}
    if not artists:
        raise ValueError("Each panel needs a series")
    labels, features = add_features(ax, panel.get("annotations", []), sources, artists, errors)
    for attr in ("xticks", "yticks", "xlim", "ylim"):
        if attr in panel:
            getattr(ax, "set_" + attr)(panel[attr])
    legend = panel.get("legend", len(artists) > 1)
    if isinstance(legend, dict) or legend:
        options = {"loc": "lower left", "bbox_to_anchor": (0, 1.015), "borderaxespad": 0,
                   "frameon": False, "ncol": min(3, len(artists)), "fontsize": 8}
        if isinstance(legend, dict):
            if "loc" in legend:
                options.pop("bbox_to_anchor")
            options.update(legend)
        ax.legend(**options)
    review_insets(ax, features, sources, artists)
    return labels, report, features


def render(spec_path, out):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    source = spec_path.parent / spec["data"]
    rows = read_table(source)
    with matplotlib.rc_context():
        fonts = set_fonts(spec)
        with bilingual_math(fonts[1]):
            return render_panels(spec_path, out, spec, source, rows, fonts)


def render_panels(spec_path, out, spec, source, rows, fonts):
    panels = spec["panels"]
    ncol = min(int(spec.get("columns", len(panels))), len(panels))
    if ncol < 1:
        raise ValueError("At least one panel and one column are required")
    nrow = math.ceil(len(panels) / ncol)
    size = (spec.get("width_mm", 80 if ncol == 1 else 170), spec.get("height_mm", 65 * nrow))
    if any(float(v) <= 0 or not math.isfinite(v) for v in size):
        raise ValueError("Physical dimensions must be finite and positive")
    # Measure at PNG resolution so point offsets and extents match the deliverable.
    fig, axes = plt.subplots(nrow, ncol, squeeze=False, figsize=np.array(size)/25.4, dpi=600,
                             layout="constrained")
    plots = []
    try:
        for ax, panel in zip(axes.flat, panels):
            plots.append(draw_panel(ax, panel, rows))
        for ax in list(axes.flat)[len(panels):]:
            fig.delaxes(ax)
        fixed = ["axes_box" in panel for panel in panels]
        if any(fixed):
            if not all(fixed):
                raise ValueError("Supply axes_box for every panel when matching a fixed layout")
            fig.set_layout_engine("none")
            for ax, panel in zip(axes.flat, panels):
                left, bottom, width, height = panel["axes_box"]
                if min(left, bottom) < 0 or min(width, height) <= 0 or left+width > 1 or bottom+height > 1:
                    raise ValueError("axes_box must fit in normalized figure coordinates")
                ax.set_position(panel["axes_box"])
        fig.canvas.draw()
        fig.set_layout_engine("none")
        reports = []
        for ax, (labels, report, features) in zip(axes.flat, plots):
            paths = [a.get_transform().transform_path(a.get_path()) for a in ax.lines]
            for (x, y), label in labels:
                if not ax.bbox.contains(*ax.transData.transform((x, y))):
                    raise ValueError(f"Anchor outside plotted axes: {label}")
            annotations = place_labels(ax, labels, paths)
            reports.append({"series": report, "features": features, "annotations": annotations})
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for ax, report in zip(axes.flat, reports):
            extent = ax.get_tightbbox(renderer)
            report["review_clipping"] = not (fig.bbox.contains(*extent.min) and fig.bbox.contains(*extent.max))
            report["axes_box"] = list(ax.get_position().bounds)
        out = Path(out)
        if out.exists():
            raise ValueError(f"Choose a new output directory: {out}")
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=out.parent) as temp:
            stage = Path(temp) / "result"
            stage.mkdir()
            fig.savefig(stage/"figure.pdf", dpi=600)
            fig.savefig(stage/"figure.png", dpi=600)
            state = {"data_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                     "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                     "size_mm": size, "dpi": 600, "fonts": fonts, "panels": reports}
            state["needs_layout_review"] = any(
                panel["review_clipping"] or any(a["review_overlap"] for a in panel["annotations"])
                or any(f.get("placement_audit", {}).get("review_occlusion") for f in panel["features"])
                for panel in reports)
            (stage/"measurements.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            stage.rename(out)
        return state
    finally:
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        render(args.spec, args.out)
    except (OSError, KeyError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")
