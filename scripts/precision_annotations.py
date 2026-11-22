"""Compute anchors in source coordinates and place labels after the axes have been laid out."""
import re

import numpy as np
from matplotlib.text import Text
from matplotlib.transforms import Bbox


def line_geometry(x, y, xscale, yscale):
    """Represent straight segments in physical units faithfully on logarithmic axes."""
    if xscale == yscale == "linear" or len(x) < 2:
        return x, y, None
    xx, yy, markers = [], [], []
    for i in range(len(x)):
        if i and np.isfinite([x[i-1], y[i-1], x[i], y[i]]).all():
            fractions = []
            for data, scale in ((x, xscale), (y, yscale)):
                a, b = data[i-1], data[i]
                if scale == "log" and a != b:
                    if min(a, b) <= 0:
                        raise ValueError("Line falls outside the log domain")
                    count = min(4097, 2 + int(96 * abs(np.log10(b) - np.log10(a))))
                    fractions.extend((np.geomspace(a, b, count)[1:-1] - a)/(b-a))
            for f in np.unique(fractions):
                xx.append((1-f)*x[i-1] + f*x[i])
                yy.append((1-f)*y[i-1] + f*y[i])
        markers.append(len(xx))
        xx.append(x[i])
        yy.append(y[i])
    return xx, yy, markers


def threshold_crossings(x, y, level):
    """One location per crossing; a threshold plateau is represented by its first sample."""
    points = []
    for i, (xi, yi) in enumerate(zip(x, y)):
        if not np.isfinite([xi, yi]).all():
            continue
        if yi == level:
            if i == 0 or not np.isfinite(x[i - 1]) or y[i - 1] != level:
                points.append(float(xi))
        elif i and np.isfinite([x[i - 1], y[i - 1]]).all():
            before = y[i - 1] - level
            if (before < 0 < yi - level) or (before > 0 > yi - level):
                fraction = (level - y[i - 1]) / (yi - y[i - 1])
                points.append(float(x[i - 1] + fraction * (xi - x[i - 1])))
    return points


def numeric_anchor(x, y, request):
    valid = np.isfinite(x) & np.isfinite(y)
    if not valid.any():
        raise ValueError("Series has no finite points")
    kind = request["kind"]
    if kind in ("peak", "minimum"):
        target = (np.max if kind == "peak" else np.min)(y[valid])
        candidates = x[valid & (y == target)].tolist()
    elif kind == "threshold":
        target = float(request["value"])
        if not np.isfinite(target):
            raise ValueError("Threshold must be finite")
        candidates = threshold_crossings(x, y, target)
    elif kind == "inflection":
        if not valid.all() or len(x) < 5 or not np.all(np.diff(x) > 0):
            raise ValueError("Inflection needs a contiguous, strictly increasing segment with at least five finite observations")
        # Curvature at interior observations, from adjacent secant slopes on an uneven grid.
        second = 2 * np.diff(np.diff(y) / np.diff(x)) / (x[2:] - x[:-2])
        core = x[1:-1]
        nz = np.flatnonzero(second)
        candidates = []
        for left, right in zip(nz[:-1], nz[1:]):
            if np.sign(second[left]) != np.sign(second[right]):
                if right > left + 1:
                    candidates.append(float((core[left + 1] + core[right - 1]) / 2))
                else:
                    candidates.extend(threshold_crossings(core[left:right+1], second[left:right+1], 0))
        target = None
    else:
        raise ValueError(f"Unsupported point annotation: {kind}")
    if not candidates:
        raise ValueError(f"No observed {kind} in this series")
    if len(candidates) > 1 and "occurrence" not in request:
        raise ValueError(f"{kind} has {len(candidates)} candidates in acquisition order. Specify occurrence (1-based).")
    which = request.get("occurrence", 1)
    if type(which) is not int or not 1 <= which <= len(candidates):
        raise ValueError("Invalid occurrence")
    xpos = candidates[which - 1]
    if target is None:
        target = np.interp(xpos, x, y)
    return float(xpos), float(target)


def coordinate_label(template, x, y):
    """Format only coordinates; leave TeX commands, groups and subscripts intact."""
    values = {"x": x, "y": y}
    in_math = False

    def substitute(match):
        nonlocal in_math
        token = match[0]
        if token == "$":
            in_math = not in_math
        if match[1] and (not in_math or match[2] is not None):
            return format(values[match[1]], match[2] or "")
        if not in_math and token in ("{{", "}}"):
            return token[0]
        return token

    return re.sub(r"\\.|\$|\{\{|\}\}|\{([xy])(?::([^{}]+))?\}", substitute, template)


def inset_box(box):
    if (len(box) != 4 or not np.isfinite(box).all() or min(box) < 0 or
            min(box[2:]) <= 0 or box[0] + box[2] > 1 or box[1] + box[3] > 1):
        raise ValueError("Inset box must fit in axes-fraction coordinates")
    return Bbox.from_bounds(*box)


def intersecting_segments(start, end, box):
    """Count finite line segments touching a rectangle, including crossings with no vertex inside."""
    if not len(start):
        return 0
    delta = end - start
    low, high = np.zeros(len(start)), np.ones(len(start))
    ok = np.isfinite(start).all(axis=1) & np.isfinite(end).all(axis=1)
    for axis in (0, 1):
        fixed = delta[:, axis] == 0
        ok &= ~fixed | ((start[:, axis] >= box.min[axis]) & (start[:, axis] <= box.max[axis]))
        with np.errstate(divide="ignore", invalid="ignore"):
            a = (box.min[axis] - start[:, axis]) / delta[:, axis]
            b = (box.max[axis] - start[:, axis]) / delta[:, axis]
        low = np.maximum(low, np.where(fixed, -np.inf, np.minimum(a, b)))
        high = np.minimum(high, np.where(fixed, np.inf, np.maximum(a, b)))
    return int(np.count_nonzero(ok & (low <= high)))


def review_insets(ax, features, sources, artists):
    """Assess each inset against all parent series in axes coordinates after limits are final."""
    items = [f for f in features if f["kind"] == "inset"]
    if not items:
        return
    transform = ax.transData - ax.transAxes
    points = np.concatenate([transform.transform(np.column_stack(pair)) for pair in sources.values()])
    paths = [transform.transform(artist.get_xydata()) for artist in artists.values()
             if artist.get_linestyle() not in ("None", "", "none")]
    reserved = [inset_box(f["box"]) for f in items if f.get("placement", "fixed") == "fixed"]
    for child, item in zip(ax.child_axes, items):
        initial = inset_box(item["box"])
        placement = item.get("placement", "fixed")
        if placement not in ("auto", "fixed"):
            raise ValueError("Inset placement must be auto or fixed")
        options = [initial]
        if placement == "auto":
            if "candidates" in item:
                options.extend(inset_box(b) for b in item["candidates"])
            else:
                w, h = initial.width, initial.height
                mx, my = min(.04, (1-w)/2), min(.04, (1-h)/2)
                options.extend(Bbox.from_bounds(x, y, w, h)
                               for y in (1-h-my, my, (1-h)/2)
                               for x in (1-w-mx, mx, (1-w)/2))
        elif "candidates" in item:
            raise ValueError("Set placement to auto before providing inset candidates")

        def count(box):
            point_hits = int(np.sum(np.all((points >= box.min) & (points <= box.max), axis=1)))
            crossings = sum(intersecting_segments(path[:-1], path[1:], box) for path in paths)
            return point_hits, crossings

        counts = [count(box) for box in options]
        if placement == "auto":
            def score(i):
                collisions = sum(options[i].overlaps(occupied) for occupied in reserved)
                return collisions, sum(counts[i]), counts[i][0]
            best = min(range(len(options)), key=score)
            chosen = options[best]
            reserved.append(chosen)
            # Axes.inset_axes installs a live locator. Replace the locator so the
            # chosen box follows the parent through layout and both export backends.
            child.set_axes_locator(lambda child, renderer, b=chosen:
                                   (ax.transAxes - ax.figure.transFigure).transform_bbox(b))
        else:
            best, chosen = 0, initial
        hits, crossings = counts[best]
        item["placement_audit"] = {
            "placement": placement, "requested_box": list(initial.bounds), "actual_box": list(chosen.bounds),
            "initial_covered_points": counts[0][0], "initial_intersecting_segments": counts[0][1],
            "covered_points": hits, "intersecting_segments": crossings,
            "review_occlusion": bool(hits or crossings), "candidate_count": len(options)}
    actual = [inset_box(f["placement_audit"]["actual_box"]) for f in items]
    for i, item in enumerate(items):
        by_other = any(actual[i].overlaps(b) for j, b in enumerate(actual) if i != j)
        item["placement_audit"]["overlaps_other_inset"] = by_other
        item["placement_audit"]["review_occlusion"] |= by_other


def add_features(ax, items, sources, artists, errors):
    """Translate declared statistical results and data series into artists and an audit trail."""
    labels, details = [], []
    for item in items:
        kind = item["kind"]
        if kind in ("interval", "span"):
            left, right = item["bounds"]
            if not np.isfinite([left, right]).all() or left >= right:
                raise ValueError("Interval bounds must increase")
            if kind == "interval":
                ax.axvspan(left, right, color=item.get("color", "#9EC6D9"), alpha=.22, zorder=0)
            else:
                y = float(item["y"])
                ax.annotate("", (left, y), (right, y), arrowprops={"arrowstyle": "<->", "lw": .7})
                labels.append((((left + right)/2, y), item["label"]))
        elif kind == "reference":
            axis = item["axis"]
            if axis not in ("x", "y"):
                raise ValueError("Reference axis must be x or y")
            (ax.axvline if axis == "x" else ax.axhline)(item["value"], lw=.7, ls="--",
                                                       color=item.get("color", "#656565"))
        elif kind == "significance":
            left, right = item["bounds"]
            pvalue = float(item["p"])
            y = float(item["y"])
            if not (0 <= pvalue <= 1 and left < right and item["test"].strip() and item["source"].strip()):
                raise ValueError("Significance needs a real test, source, p value and comparison bounds")
            ax.plot([left, right], [y, y], lw=.7, color="#383838", marker="|", clip_on=False)
            labels.append((((left + right)/2, y), f"p = {pvalue:.3g}"))
        elif kind == "inset":
            box = item["box"]
            inset_box(box)
            for field in ("xlim", "ylim"):
                lo, hi = item[field]
                if not np.isfinite([lo, hi]).all() or lo >= hi:
                    raise ValueError("Inset limits must increase")
            inset = ax.inset_axes(box)
            inset.set_xscale(ax.get_xscale())
            inset.set_yscale(ax.get_yscale())
            for key in item.get("series", list(sources)):
                artist = artists[key]
                inset.plot(*artist.get_data(), color=artist.get_color(), linestyle=artist.get_linestyle(),
                           marker=artist.get_marker(), markevery=artist.get_markevery(), markersize=2, lw=.7)
                if errors[key] is not None:
                    inset.errorbar(*sources[key], yerr=errors[key], fmt="none", color=artist.get_color(),
                                   capsize=1.5, linewidth=.6)
            inset.set(xlim=item["xlim"], ylim=item["ylim"])
            inset.tick_params(labelsize=6, pad=1, length=2)
            ax.indicate_inset_zoom(inset, edgecolor="#505050", linewidth=.65)
        elif kind == "linear_fit":
            x, y = sources[item["series"]]
            valid = np.isfinite(x) & np.isfinite(y)
            if "bounds" in item:
                low, high = item["bounds"]
                valid &= (x >= low) & (x <= high)
            x, y = x[valid], y[valid]
            if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
                raise ValueError("Linear fit requires three finite observations, varying x and varying y")
            slope, intercept = np.polyfit(x, y, 1)
            predicted = slope*x + intercept
            r2 = 1 - np.sum((y - predicted)**2)/np.sum((y - y.mean())**2)
            extent = np.array([x.min(), x.max()])
            fit_y = slope*extent + intercept
            if ax.get_yscale() == "log" and np.min(fit_y) <= 0:
                raise ValueError("Fit crosses a non-positive ordinate on a log axis. Review the fit range.")
            fit_x, fit_y, _ = line_geometry(extent, fit_y, ax.get_xscale(), ax.get_yscale())
            ax.plot(fit_x, fit_y, color="#555555", lw=.75, ls="--")
            xm = float(np.mean(extent))
            labels.append(((xm, slope*xm+intercept),
                           f"y = {slope:.3g}x {intercept:+.3g}\n$R^2$ = {r2:.3g}"))
            details.append({"kind": kind, "series": item["series"], "n": len(y),
                            "slope": float(slope), "intercept": float(intercept), "r2": float(r2),
                            "x_bounds": extent.tolist(), "model": "unweighted OLS with intercept"})
            continue
        else:
            series = item["series"]
            if kind == "threshold" and artists[series].get_linestyle() == "None" and not item.get("interpolate"):
                raise ValueError("A scatter threshold needs an explicit interpolation model (interpolate: true for linear)")
            xy = numeric_anchor(*sources[series], item)
            label = coordinate_label(item.get("label", "{x:.3g}, {y:.3g}"), *xy)
            labels.append((xy, label))
        details.append(dict(item))
    return labels, details


def place_labels(ax, requests, paths):
    """Try offsets at final scale. Unresolved placements must be reviewed at export size."""
    placed = []
    boxes = [child.bbox for child in ax.child_axes]
    renderer = ax.figure.canvas.get_renderer()
    if ax.get_legend() is not None:
        boxes.append(ax.get_legend().get_window_extent(renderer))
    for xy, label in requests:
        annotation = ax.annotate(label, xy, xytext=(0, 0), textcoords="offset points",
                                 fontsize=8, ha="center", va="center",
                                 arrowprops={"arrowstyle": "->", "lw": 0.65, "shrinkB": 0},
                                 annotation_clip=False)
        offsets = [(dx, dy) for dy in (15, -15, 27, -27, 40, -40) for dx in (0, 22, -22, 40, -40)]
        best = None
        for dx, dy in offsets:
            annotation.set_position((dx, dy))
            annotation.update_positions(renderer)
            box = Text.get_window_extent(annotation, renderer).expanded(1.08, 1.15)
            if not ax.bbox.contains(*box.min) or not ax.bbox.contains(*box.max):
                continue
            hits = sum(box.overlaps(other) for other in boxes)
            hits += sum(path.intersects_bbox(box, filled=False) for path in paths)
            if best is None or hits < best[0]:
                best = hits, (dx, dy), Bbox.from_extents(*box.extents)
            if hits == 0:
                break
        if best is None:
            raise ValueError(f"Label does not fit inside axes: {label}. Increase width or shorten label.")
        hits, offset, box = best
        annotation.set_position(offset)
        boxes.append(box)
        placed.append({"text": label, "xy": list(xy), "offset_pt": list(offset),
                       "review_overlap": bool(hits)})
    return placed
