"""Inspect native object structure. Does not prove rendering or scientific correctness."""
import argparse
import json
import posixpath
import re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def audit(path, native_only=False, font=None):
    result = {"file": Path(path).name, "slides": 0, "shapes": 0, "connectors": 0,
              "textboxes": 0, "groups": 0, "freeforms": 0, "pictures": 0,
              "fonts": [], "placeholders": 0, "group_locks": 0, "errors": [], "warnings": [],
              "render_verified": False, "grouping_verified_in_app": False}
    fonts = set()
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
                if any(e.text for e in shape.iter(A+"t")): result["textboxes"] += 1
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
    if font and (not fonts or any(f != font for f in fonts)): result["errors"].append("Requested font does not match all explicit text fonts")
    if not result["slides"]: result["errors"].append("No slides")
    result["passed"] = not result["errors"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx"); parser.add_argument("--require-native-only", action="store_true")
    parser.add_argument("--font"); parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.pptx, args.require_native_only, args.font)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream: stream.write(text + "\n")
    print(text)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
