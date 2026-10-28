"""Build a native editable PPTX from an explicit scene, after recorded approval.

This is a small OOXML writer, not an image recognizer or an Office renderer.
"""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
from workflow import require_approval, record_build

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
for prefix, uri in NS.items(): ET.register_namespace(prefix, uri)
EMU = 36000


def node(tag, attrs=None, children=()):
    prefix, name = tag.split(":")
    result = ET.Element("{" + NS[prefix] + "}" + name, {k: str(v) for k, v in (attrs or {}).items()})
    result.extend(children)
    return result


def xml(element):
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Expected a finite number, got {value!r}")
    return value


def emu(value):
    return round(num(value) * EMU)


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        raise ValueError(f"Use a six-digit RGB color without #: {value!r}")
    return value.upper()


def walk(elements):
    for e in elements:
        if "children" in e and e.get("type") != "group":
            raise ValueError("Only groups may contain children: " + str(e.get("id", "")))
        yield e
        yield from walk(e.get("children", []))


def path_points(e):
    points = []
    for command in e["commands"]:
        if command[0] not in ("M", "L", "C", "Z"):
            raise ValueError("Path commands must be M, L, C, or Z")
        expected = {"M": 3, "L": 3, "C": 7, "Z": 1}[command[0]]
        if len(command) != expected: raise ValueError("Invalid path command length")
        points += [[num(command[i]), num(command[i + 1])] for i in range(1, len(command), 2)]
    if not e["commands"] or e["commands"][0][0] != "M":
        raise ValueError("A path must begin with M")
    return points


def bounds(e):
    kind = e["type"]
    if kind == "group":
        boxes = [bounds(c) for c in e["children"]]
        if not boxes: raise ValueError("Empty groups are not supported")
        x = min(b[0] for b in boxes); y = min(b[1] for b in boxes)
        return x, y, max(b[0]+b[2] for b in boxes)-x, max(b[1]+b[3] for b in boxes)-y
    if kind in ("text", "rect", "ellipse"):
        return tuple(num(e[key]) for key in ("x", "y", "w", "h"))
    if kind == "line":
        points = [e["start"], e["end"]]
    elif kind == "polygon":
        points = e["points"]
        if len(points) < 3: raise ValueError("A polygon needs at least three points")
    elif kind == "path": points = path_points(e)
    else: raise ValueError(f"Unsupported native object type: {kind}")
    if not points or any(len(p) != 2 for p in points): raise ValueError("Use coordinate pairs")
    xs = [num(p[0]) for p in points]; ys = [num(p[1]) for p in points]
    return min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)


def validate_text(e):
    if "text" not in e and "runs" not in e: raise ValueError("Text requires text or runs")
    if num(e.get("font_pt", 9)) <= 0: raise ValueError("Font size must be positive")
    if e.get("align", "left") not in ("left", "center", "right"): raise ValueError("Invalid text alignment")
    if "runs" in e:
        if not isinstance(e["runs"], list) or not e["runs"]:
            raise ValueError("Text runs must be a nonempty list")
        for run in e["runs"]:
            if not isinstance(run, dict) or not isinstance(run.get("text"), str):
                raise ValueError("Each text run requires a text string")
            if "runs" in run or "children" in run:
                raise ValueError("Nested text runs are not supported")
            if num(run.get("font_pt", e.get("font_pt", 9))) <= 0:
                raise ValueError("Run font size must be positive")
            if run.get("baseline") is not None: num(run["baseline"])


def validate_scene(scene):
    if scene.get("version") != 1: raise ValueError("Unsupported scene version")
    width = num(scene["width_mm"]); height = num(scene["height_mm"])
    if width <= 0 or height <= 0: raise ValueError("Canvas dimensions must be positive")
    if not scene.get("elements"): raise ValueError("A scene must contain objects")
    seen = set()
    for e in walk(scene["elements"]):
        name = e["id"]
        if not isinstance(name, str) or not name or name in seen: raise ValueError("Object IDs must be unique nonempty strings")
        seen.add(name)
        x, y, w, h = bounds(e)
        if x < -0.001 or y < -0.001 or x+w > width+0.001 or y+h > height+0.001:
            raise ValueError(f"Object outside canvas: {name}")
        if w < 0 or h < 0 or (e["type"] in ("text", "rect", "ellipse") and (w == 0 or h == 0)):
            raise ValueError(f"Invalid dimensions: {name}")
        if e["type"] == "line" and w == 0 and h == 0: raise ValueError("Zero-length line")
        for field in ("fill", "stroke"):
            if e.get(field) is not None: color(e[field])
        if num(e.get("line_pt", 0.65)) < 0: raise ValueError("Negative line width")
        if e["type"] == "text":
            validate_text(e)
        if e.get("arrow_start", False) not in (True, False) or e.get("arrow_end", False) not in (True, False):
            raise ValueError("Arrow flags must be booleans")
        gradient = e.get("gradient")
        if gradient:
            stops = gradient["stops"]
            if len(stops) < 2: raise ValueError("Gradient needs two or more stops")
            previous = -1
            for position, rgb in stops:
                if not 0 <= num(position) <= 100 or position < previous: raise ValueError("Gradient positions must increase from 0 to 100")
                color(rgb); previous = position
            num(gradient.get("angle", 90))
    return scene


def validate_labels(scene, labels_path):
    normalize = lambda text: " ".join(str(text).replace("\\n", "\n").split())
    approved = Counter(normalize(line) for line in Path(labels_path).read_text(encoding="utf-8-sig").splitlines() if line.strip())
    actual = Counter()
    for e in walk(scene["elements"]):
        if e["type"] == "text":
            validate_text(e)
            text = "".join(str(r["text"]) for r in e["runs"]) if "runs" in e else e["text"]
            actual[normalize(text)] += 1
    if actual != approved:
        raise ValueError(f"Native labels differ from the approved glossary. Extra: {list((actual-approved).elements())}; missing: {list((approved-actual).elements())}")


def fill(e):
    if e.get("gradient"):
        g = e["gradient"]
        stops = [node("a:gs", {"pos": round(p*1000)}, [node("a:srgbClr", {"val": color(c)})]) for p, c in g["stops"]]
        return node("a:gradFill", {"rotWithShape": "1"}, [node("a:gsLst", children=stops), node("a:lin", {"ang": round(g.get("angle", 90)*60000), "scaled": "1"})])
    if e.get("fill") is None: return node("a:noFill")
    return node("a:solidFill", children=[node("a:srgbClr", {"val": color(e["fill"])})])


def line_style(e):
    ln = node("a:ln", {"w": round(e.get("line_pt", 0.65)*12700), "cap": "flat"})
    ln.append(node("a:solidFill", children=[node("a:srgbClr", {"val": color(e["stroke"])})]) if e.get("stroke") else node("a:noFill"))
    if e.get("dash"): ln.append(node("a:prstDash", {"val": "dash"}))
    # In DrawingML headEnd is the start endpoint and tailEnd is the end endpoint.
    for flag, tag in (("arrow_start", "headEnd"), ("arrow_end", "tailEnd")):
        if e.get(flag): ln.append(node("a:"+tag, {"type": "triangle", "w": "med", "len": "med"}))
    return ln


def transform(box, group=False, flips=None):
    x, y, w, h = box
    result = node("a:xfrm", flips or {}, [node("a:off", {"x": emu(x), "y": emu(y)}), node("a:ext", {"cx": max(1, emu(w)), "cy": max(1, emu(h))})])
    if group:
        result.extend([node("a:chOff", {"x": emu(x), "y": emu(y)}), node("a:chExt", {"cx": max(1, emu(w)), "cy": max(1, emu(h))})])
    return result


def custom_geometry(e, box):
    x, y, w, h = box
    if e["type"] == "polygon": commands = [["M", *e["points"][0]]] + [["L", *p] for p in e["points"][1:]] + [["Z"]]
    else: commands = e["commands"]
    path = node("a:path", {"w": max(1, emu(w)), "h": max(1, emu(h))})
    for c in commands:
        name = {"M": "moveTo", "L": "lnTo", "C": "cubicBezTo", "Z": "close"}[c[0]]
        command = node("a:"+name)
        for i in range(1, len(c), 2): command.append(node("a:pt", {"x": emu(c[i]-x), "y": emu(c[i+1]-y)}))
        path.append(command)
    return node("a:custGeom", children=[node("a:avLst"), node("a:gdLst"), node("a:ahLst"), node("a:cxnLst"), node("a:rect", {"l": "0", "t": "0", "r": "r", "b": "b"}), node("a:pathLst", children=[path])])


def text_body(e, font):
    body = node("p:txBody", children=[node("a:bodyPr", {"wrap": "square", "lIns": "0", "rIns": "0", "tIns": "0", "bIns": "0", "anchor": "t"}, [node("a:noAutofit")]), node("a:lstStyle")])
    paragraphs = [e["runs"]] if "runs" in e else [[{"text": t}] for t in str(e["text"]).split("\n")]
    for runs in paragraphs:
        paragraph = node("a:p", children=[node("a:pPr", {"algn": {"left": "l", "center": "ctr", "right": "r"}[e.get("align", "left")]}, [node("a:buNone")])])
        for run in runs:
            attrs = {"lang": "en-US", "sz": round(run.get("font_pt", e.get("font_pt", 9))*100)}
            if run.get("bold", e.get("bold", False)): attrs["b"] = "1"
            if run.get("italic", e.get("italic", False)): attrs["i"] = "1"
            if run.get("baseline") is not None: attrs["baseline"] = round(num(run["baseline"])*1000)
            rp = node("a:rPr", attrs, [node("a:solidFill", children=[node("a:srgbClr", {"val": color(e.get("color", "202020"))})]), node("a:latin", {"typeface": e.get("font", font)}), node("a:ea", {"typeface": e.get("font", font)}), node("a:cs", {"typeface": e.get("font", font)})])
            t = node("a:t"); t.text = str(run["text"])
            paragraph.append(node("a:r", children=[rp, t]))
        paragraph.append(node("a:endParaRPr", {"lang": "en-US", "sz": round(e.get("font_pt", 9)*100)}))
        body.append(paragraph)
    return body


def shape(e, ids, font):
    ident = next(ids); kind = e["type"]; box = bounds(e)
    props = node("p:cNvPr", {"id": ident, "name": "SCHEM_"+e["id"]})
    if kind == "group":
        return node("p:grpSp", children=[node("p:nvGrpSpPr", children=[props, node("p:cNvGrpSpPr"), node("p:nvPr")]), node("p:grpSpPr", children=[transform(box, True)])] + [shape(c, ids, font) for c in e["children"]])
    connector = kind == "line"
    nv = node("p:nvCxnSpPr" if connector else "p:nvSpPr", children=[props, node("p:cNvCxnSpPr" if connector else "p:cNvSpPr", {"txBox": "1"} if kind == "text" else {}), node("p:nvPr")])
    flips = {}
    if connector:
        if e["start"][0] > e["end"][0]: flips["flipH"] = "1"
        if e["start"][1] > e["end"][1]: flips["flipV"] = "1"
    sppr = node("p:spPr", children=[transform(box, flips=flips)])
    if kind in ("polygon", "path"): sppr.append(custom_geometry(e, box))
    else: sppr.append(node("a:prstGeom", {"prst": "line" if connector else "ellipse" if kind == "ellipse" else "rect"}, [node("a:avLst")]))
    sppr.extend([fill(e), line_style(e), node("a:effectLst")])
    result = node("p:cxnSp" if connector else "p:sp", children=[nv, sppr])
    if kind == "text": result.append(text_body(e, font))
    return result


def tree():
    return node("p:spTree", children=[node("p:nvGrpSpPr", children=[node("p:cNvPr", {"id": "1", "name": ""}), node("p:cNvGrpSpPr"), node("p:nvPr")]), node("p:grpSpPr", children=[transform((0,0,1,1), True)])])


def rels(entries):
    root = ET.Element("Relationships", {"xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"})
    for ident, kind, target in entries:
        ET.SubElement(root, "Relationship", {"Id": ident, "Type": NS["r"]+"/"+kind, "Target": target})
    return xml(root)


def package(scene):
    from itertools import count
    ids = count(2); font = scene.get("font", "Times New Roman")
    objects = tree()
    elements = scene["elements"]
    if scene.get("group_all", True): elements = [{"id": "figure", "type": "group", "children": elements}]
    for e in elements: objects.append(shape(e, ids, font))
    slide = node("p:sld", children=[node("p:cSld", children=[node("p:bg", children=[node("p:bgPr", children=[fill({"fill": scene.get("background", "FFFFFF")}), node("a:effectLst")])]), objects]), node("p:clrMapOvr", children=[node("a:masterClrMapping")])])
    rid = "{"+NS["r"]+"}id"
    presentation = node("p:presentation", children=[node("p:sldMasterIdLst", children=[node("p:sldMasterId", {"id": "2147483648", rid: "rId1"})]), node("p:sldIdLst", children=[node("p:sldId", {"id": "256", rid: "rId2"})]), node("p:sldSz", {"cx": emu(scene["width_mm"]), "cy": emu(scene["height_mm"])}), node("p:notesSz", {"cx": "6858000", "cy": "9144000"})])
    cmap = {"bg1":"lt1", "tx1":"dk1", "bg2":"lt2", "tx2":"dk2", **{f"accent{i}":f"accent{i}" for i in range(1,7)}, "hlink":"hlink", "folHlink":"folHlink"}
    master = node("p:sldMaster", children=[node("p:cSld", children=[tree()]), node("p:clrMap", cmap), node("p:sldLayoutIdLst", children=[node("p:sldLayoutId", {"id":"2147483649", rid:"rId1"})]), node("p:txStyles", children=[node("p:titleStyle"), node("p:bodyStyle"), node("p:otherStyle")])])
    layout = node("p:sldLayout", {"type":"blank", "preserve":"1"}, [node("p:cSld", {"name":"Blank"}, [tree()]), node("p:clrMapOvr", children=[node("a:masterClrMapping")])])
    scheme = node("a:clrScheme", {"name":"Scientific"}, [node("a:"+k, children=[node("a:srgbClr", {"val":v})]) for k,v in {"dk1":"202020","lt1":"FFFFFF","dk2":"505050","lt2":"EEEEEE","accent1":"159DDD","accent2":"E04746","accent3":"AAB568","accent4":"DDE5C8","accent5":"999999","accent6":"777777","hlink":"0563C1","folHlink":"954F72"}.items()])
    fonts = node("a:fontScheme", {"name":"Scientific"}, [node("a:"+k, children=[node("a:latin", {"typeface":font}), node("a:ea", {"typeface":font}), node("a:cs", {"typeface":font})]) for k in ("majorFont","minorFont")])
    phfill = lambda: node("a:solidFill", children=[node("a:schemeClr", {"val":"phClr"})])
    fmt = node("a:fmtScheme", {"name":"Scientific"}, [node("a:fillStyleLst", children=[phfill() for _ in range(3)]), node("a:lnStyleLst", children=[node("a:ln", {"w":"12700"}, [phfill(), node("a:prstDash", {"val":"solid"})]) for _ in range(3)]), node("a:effectStyleLst", children=[node("a:effectStyle", children=[node("a:effectLst")]) for _ in range(3)]), node("a:bgFillStyleLst", children=[phfill() for _ in range(3)])])
    theme = node("a:theme", {"name":"Scientific"}, [node("a:themeElements", children=[scheme,fonts,fmt])])
    files = {"ppt/presentation.xml":xml(presentation), "ppt/slides/slide1.xml":xml(slide), "ppt/slideMasters/slideMaster1.xml":xml(master), "ppt/slideLayouts/slideLayout1.xml":xml(layout), "ppt/theme/theme1.xml":xml(theme),
             "_rels/.rels":rels([("rId1","officeDocument","ppt/presentation.xml")]),
             "ppt/_rels/presentation.xml.rels":rels([("rId1","slideMaster","slideMasters/slideMaster1.xml"),("rId2","slide","slides/slide1.xml")]),
             "ppt/slides/_rels/slide1.xml.rels":rels([("rId1","slideLayout","../slideLayouts/slideLayout1.xml")]),
             "ppt/slideMasters/_rels/slideMaster1.xml.rels":rels([("rId1","slideLayout","../slideLayouts/slideLayout1.xml"),("rId2","theme","../theme/theme1.xml")]),
             "ppt/slideLayouts/_rels/slideLayout1.xml.rels":rels([("rId1","slideMaster","../slideMasters/slideMaster1.xml")])}
    types = ET.Element("Types", {"xmlns":"http://schemas.openxmlformats.org/package/2006/content-types"})
    ET.SubElement(types,"Default",{"Extension":"rels","ContentType":"application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(types,"Default",{"Extension":"xml","ContentType":"application/xml"})
    for part, kind in (("ppt/presentation.xml","presentationml.presentation.main"),("ppt/slides/slide1.xml","presentationml.slide"),("ppt/slideMasters/slideMaster1.xml","presentationml.slideMaster"),("ppt/slideLayouts/slideLayout1.xml","presentationml.slideLayout"),("ppt/theme/theme1.xml","theme")):
        ET.SubElement(types,"Override",{"PartName":"/"+part,"ContentType":"application/vnd.openxmlformats-officedocument."+kind+"+xml"})
    files["[Content_Types].xml"] = xml(types)
    return files


def build(scene, output):
    validate_scene(scene)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting a user-edited presentation.
    files = package(scene)
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for name, data in files.items(): archive.writestr(name, data)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True); parser.add_argument("--scene", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        state = require_approval(args.project)
        scene = json.loads(Path(args.scene).read_text(encoding="utf-8"))
        validate_scene(scene)
        validate_labels(scene, state["preview"]["assets"]["labels"]["path"])
        inventory = state["preview"]["assets"].get("inventory")
        if not inventory:
            raise ValueError("Register and approve a reconstruction inventory with the current preview")
        from check_fidelity import check
        check(scene, json.loads(Path(inventory["path"]).read_text(encoding="utf-8")))
        build(scene, args.output)
        record_build(args.project, args.scene, args.output)
        print(json.dumps({"output": str(Path(args.output).resolve()), "native_only": True, "render_verified": False}))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
