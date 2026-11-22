"""Inspect native object structure. Does not prove rendering or scientific correctness."""
import argparse
import json
import posixpath
import re
import unicodedata
from functools import lru_cache
from itertools import groupby
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


@lru_cache(maxsize=256)
def measuring_font(face, size, bold, italic):
    from PIL import ImageFont
    from matplotlib.font_manager import FontProperties, findfont
    font = FontProperties(family=[face], weight="bold" if bold else "normal",
                          style="italic" if italic else "normal")
    # 720 dpi gives ten samples per typographic point.
    return ImageFont.truetype(findfont(font, fallback_to_default=False), max(1, round(size / 10)))


def text_width_check(shape, slide):
    body = shape.find(P+"txBody")
    extent = shape.find(P+"spPr/"+A+"xfrm/"+A+"ext")
    if body is None or extent is None:
        return None
    name_node = shape.find(P+"nvSpPr/"+P+"cNvPr")
    name = name_node.get("name", "") if name_node is not None else ""
    props = body.find(A+"bodyPr")
    result = {"slide": slide, "shape": name}
    if props is None or props.get("vert", "horz") != "horz":
        return dict(result, status="unmeasured", reason="Missing or vertical text frame")
    available = (int(extent.get("cx")) - int(props.get("lIns", 91440)) -
                 int(props.get("rIns", 91440))) / 12700
    widths = []
    for para in body.findall(A+"p"):
        width = 0
        for node in para:
            if node.tag == A+"br":
                widths.append(width)
                width = 0
                continue
            if node.tag not in (A+"r", A+"fld"):
                continue
            text = node.findtext(A+"t") or ""
            rp = node.find(A+"rPr")
            if not text:
                continue
            if rp is None or rp.get("sz") is None:
                return dict(result, status="unmeasured", reason="Inherited font size")
            for cjk, chars in groupby(text, lambda c: unicodedata.east_asian_width(c) in ("W", "F")):
                family = rp.find(A+("ea" if cjk else "latin"))
                if family is None or not family.get("typeface"):
                    return dict(result, status="unmeasured", reason="Inherited font face")
                try:
                    font = measuring_font(family.get("typeface"), int(rp.get("sz")),
                                          rp.get("b") in ("1","true"), rp.get("i") in ("1","true"))
                except (ValueError, OSError) as exc:
                    return dict(result, status="unmeasured", reason=str(exc))
                width += font.getlength("".join(chars)) / 10
        widths.append(width)
    longest = max(widths, default=0)
    return dict(result, status="review_wrap" if longest > available + .3 else "fits_width",
                longest_line_pt=round(longest, 2), available_pt=round(available, 2))


def audit(path, native_only=False, font=None, font_latin=None, font_ea=None, check_text_width=False):
    result = {"file": Path(path).name, "slides": 0, "shapes": 0, "connectors": 0,
              "textboxes": 0, "groups": 0, "freeforms": 0, "pictures": 0,
              "fonts": [], "placeholders": 0, "group_locks": 0, "errors": [], "warnings": [],
              "render_verified": False, "grouping_verified_in_app": False}
    fonts = set()
    by_script = {"latin": set(), "ea": set()}
    requested = {"latin": font_latin, "ea": font_ea}
    if check_text_width:
        result["text_width_checks"] = []
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        if archive.testzip(): result["errors"].append("ZIP CRC failure")
        for required in ("[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"):
            if required not in names: result["errors"].append("Missing package part: " + required)
        for name in names:
            if name.endswith(".rels"):
                root = ET.fromstring(archive.read(name))
                base = posixpath.dirname(posixpath.dirname(name))
                for rel in root:
                    if native_only and rel.get("Type", "").endswith("/image"):
                        result["errors"].append("Image relationship present in native-only output: " + name)
                    if rel.get("TargetMode") == "External": continue
                    target = rel.get("Target", "")
                    resolved = posixpath.normpath(posixpath.join(base, target)) if not target.startswith("/") else target[1:]
                    if resolved not in names: result["errors"].append(f"Broken relationship: {name} -> {target}")
            is_slide = bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", name))
            if not is_slide and not (native_only and name.startswith("ppt/") and name.endswith(".xml")): continue
            root = ET.fromstring(archive.read(name))
            if native_only and (list(root.iter(A+"blip")) or list(root.iter(A+"blipFill"))):
                result["errors"].append("Image fill/reference present in native-only output: " + name)
            if not is_slide: continue
            result["slides"] += 1
            ids = [e.get("id") for e in root.iter(P+"cNvPr")]
            if len(ids) != len(set(ids)): result["errors"].append("Duplicate shape IDs in " + name)
            for tag, key in (("sp","shapes"),("cxnSp","connectors"),("grpSp","groups"),("pic","pictures"),("ph","placeholders")):
                result[key] += len(list(root.iter(P+tag)))
            result["freeforms"] += len(list(root.iter(A+"custGeom")))
            for shape in root.iter(P+"sp"):
                if any(e.text for e in shape.iter(A+"t")):
                    result["textboxes"] += 1
                    if check_text_width:
                        row = text_width_check(shape, name)
                        if row:
                            result["text_width_checks"].append(row)
                            if row["status"] != "fits_width":
                                result["warnings"].append(f"{name}: {row['shape']} {row['status']}")
            for run in root.iter(A+"r"):
                if not run.findtext(A+"t"):
                    continue
                for slot, expected in requested.items():
                    face = run.find(A+"rPr/"+A+slot)
                    actual = face.get("typeface") if face is not None else None
                    if actual:
                        by_script[slot].add(actual)
                    if expected and actual != expected:
                        error = f"{name}: {slot} text font {actual!r}, expected {expected!r}"
                        if error not in result["errors"]:
                            result["errors"].append(error)
            for e in root.iter():
                if e.get("noGrp") in ("1", "true"): result["group_locks"] += 1
                if e.tag in (A+"latin", A+"ea", A+"cs") and e.get("typeface"): fonts.add(e.get("typeface"))
                if e.tag == A+"ext" and (int(e.get("cx", "1")) <= 0 or int(e.get("cy", "1")) <= 0):
                    result["warnings"].append("Zero-size transform; inspect lines and grouping in the target app")
            if list(root.iter(P+"graphicFrame")): result["warnings"].append("Graphic frames present; check table/chart grouping restrictions")
        if native_only and result["pictures"]: result["errors"].append("Raster/image objects present in native-only output")
        if native_only and any(n.startswith("ppt/media/") for n in names): result["errors"].append("Embedded media present in native-only output")
        if result["group_locks"]: result["errors"].append("Objects contain noGrp restrictions")
        if result["placeholders"]: result["warnings"].append("Placeholders may prevent grouping with other objects")
    result["fonts"] = sorted(fonts)
    result["fonts_by_script"] = {slot: sorted(faces) for slot, faces in by_script.items()}
    for slot, expected in requested.items():
        if expected and not by_script[slot]:
            result["errors"].append(f"No explicit {slot} font on nonempty text runs")
    if font and (not fonts or any(f != font for f in fonts)): result["errors"].append("Requested font does not match all explicit text fonts")
    if not result["slides"]: result["errors"].append("No slides")
    result["passed"] = not result["errors"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx"); parser.add_argument("--require-native-only", action="store_true")
    parser.add_argument("--font", help="Require a single font across all explicit font slots (legacy scenes)")
    parser.add_argument("--font-latin", help="Require this explicit Latin font on every text run")
    parser.add_argument("--font-ea", help="Require this explicit East Asian font on every text run")
    parser.add_argument("--check-text-width", action="store_true",
                        help="Measure explicitly formatted native lines and flag possible wrapping (Pillow and Matplotlib)")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.pptx, args.require_native_only, args.font, args.font_latin, args.font_ea, args.check_text_width)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream: stream.write(text + "\n")
    print(text)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
