"""Choose a schematic palette by topic, named recipe, or colors from a reference."""
import argparse
import json
import math
import re
import sys
from itertools import combinations
import unicodedata
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1] / "references" / "palettes.json"


def normalized(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[-‐‑–—_/]+", " ", text)


def theme_matches(theme, palettes):
    text = normalized(theme)
    ranked = []
    for palette in palettes:
        hits = []
        for lang, keywords in palette["keywords"].items():
            for word in keywords:
                needle = normalized(word)
                pattern = re.escape(needle)
                if lang == "en":
                    pattern = r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])"
                if re.search(pattern, text):
                    hits.append(needle)
        # A longer matching expression already accounts for its contained synonyms.
        independent = sorted({hit for hit in hits if not any(hit != other and hit in other for other in hits)})
        if independent:
            ranked.append({"id": palette["id"], "matches": independent, "score": len(independent)})
    return sorted(ranked, key=lambda entry: -entry["score"])


def parse_named(values):
    result = {}
    for item in values:
        name, sep, value = item.partition("=")
        if not sep or not name.strip() or not value.strip():
            raise ValueError(f"Expected role=value, got {item!r}")
        name = name.strip()
        if name in result:
            raise ValueError(f"Duplicate role: {name}")
        result[name] = value.strip()
    return result


def hex_colors(values):
    colors = {}
    for role, raw in parse_named(values).items():
        if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", raw):
            raise ValueError(f"Expected a six-digit RGB color for {role}: {raw}")
        colors[role] = "#" + raw.lstrip("#").upper()
    return colors


def reference_swatches(path, samples):
    from PIL import Image, ImageOps
    with Image.open(path) as source:
        oriented = ImageOps.exif_transpose(source)
        rgba = oriented.convert("RGBA")
        image = Image.new("RGB", rgba.size, "white")
        image.paste(rgba, mask=rgba.getchannel("A"))
    swatches = {}
    for role, position in parse_named(samples).items():
        try:
            x, y = map(float, position.split(","))
        except ValueError as exc:
            raise ValueError(f"Expected normalized x,y for {role}") from exc
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError(f"Coordinates out of bounds for {role}: {position}")
        pixel = round(x * (image.width - 1)), round(y * (image.height - 1))
        swatches[role] = "#%02X%02X%02X" % image.getpixel(pixel)
    if swatches:
        return swatches
    # Select real visible RGB values. Quantities from an entire photo or multi-panel
    # figure do not establish which colors belong to a particular scientific object.
    image.thumbnail((512, 512), Image.Resampling.NEAREST)
    counts = sorted(image.getcolors(image.width * image.height), key=lambda item: (-item[0], item[1]))
    chosen = []
    for _, rgb in counts:
        if all(math.dist(rgb, previous) >= 45 for previous in chosen):
            chosen.append(rgb)
            if len(chosen) == 8:
                break
    return {f"ref_{i}": "#%02X%02X%02X" % rgb for i, rgb in enumerate(chosen, 1)}


def relative_luminance(color):
    rgb = [int(color[i:i + 2], 16) / 255.0 for i in [1, 3, 5]]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return sum(a * b for a, b in zip(linear, [0.2126, 0.7152, 0.0722]))


def label_for(color):
    luminance = relative_luminance(color)
    return "#000000" if (luminance + 0.05) / 0.05 >= 1.05 / (luminance + 0.05) else "#FFFFFF"


def grayscale_check(roles, cues):
    threshold = 1.5
    levels = {role: relative_luminance(value) for role, value in roles.items()
              if role not in ("text", "background")}
    pairs = []
    for first, second in combinations(levels, 2):
        dark, light = sorted((levels[first], levels[second]))
        ratio = (light + 0.05) / (dark + 0.05)
        if ratio < threshold:
            pairs.append({"roles": [first, second], "ratio": round(ratio, 4)})
    pairs.sort(key=lambda entry: entry["ratio"])
    suggestion = ""
    if pairs:
        suggestion = cues or "相邻的近灰度对象用不同线型、轮廓或纹理标记，并直接标注名称。"
    return {
        "metric": "linear_srgb_luminance_contrast_ratio",
        "local_warning_below": threshold,
        "compared_pairs": len(levels) * (len(levels) - 1) // 2,
        "close_pairs": pairs,
        "suggestion": suggestion,
    }


def choose(palettes, theme="", palette_id=None, reference_colors=None, unassigned=False):
    table = {entry["id"]: entry for entry in palettes}
    ranked = theme_matches(theme, palettes)
    notes = []
    selected = None
    if palette_id:
        if palette_id not in table:
            raise ValueError(f"Unknown palette {palette_id!r}. Use --list to see available IDs.")
        selected = table[palette_id]
    elif ranked and (len(ranked) == 1 or ranked[0]["score"] >= ranked[1]["score"] + 1):
        selected = table[ranked[0]["id"]]
    elif ranked:
        notes.append("多个主题同分。按图中央承担解释任务的对象选择候选方案，或按面板分别指定。")
    elif theme:
        notes.append("当前库缺少该主题的关键词匹配。可指定相近方案并核对其角色，或指定参考图颜色。")

    roles = dict(selected["roles"]) if selected and not unassigned else {}
    origins = dict.fromkeys(roles, "theme_recipe")
    locked = reference_colors or {}
    if set(roles) & set(locked):
        notes.append("参考颜色已覆盖同名角色，其他角色沿用所选方案。")
    roles.update(locked)
    origins.update(dict.fromkeys(locked, "reference"))
    if unassigned:
        notes.append("参考图整体色样已锁定为 ref_*。请用原图中对象内部的采样点建立语义映射。")
    if not roles:
        roles = {"text": "#24333E", "background": "#FFFFFF"}
        origins = dict.fromkeys(roles, "neutral_fallback")
        if not theme:
            notes.append("请提供主题或参考图对象颜色，以确定示意图各角色。")
    needs_choice = unassigned or (not selected and not locked)
    recipe_id = selected["id"] if selected else None
    cues = selected["noncolor_cues"] if selected and not unassigned else ""
    gray = grayscale_check(roles, cues)
    if gray["close_pairs"]:
        notes.append("部分角色转为灰度后亮度接近。若它们相邻或须相互辨认，请参考 grayscale_check 中的角色对和辅助标记建议。")
    return {
        "status": "needs_review" if needs_choice else "ready", "theme": theme,
        "source": "reference" if locked else ("explicit" if palette_id else ("theme" if selected else "fallback")),
        "palette_id": recipe_id, "candidates": ranked, "roles": roles, "role_origin": origins,
        "theme_accents": list(dict.fromkeys(value for key, value in roles.items()
                                            if key not in ("text", "background")))[:6],
        "label_colors": {k: label_for(v) for k, v in roles.items()},
        "source_dois": selected["source_dois"] if selected and not unassigned else [],
        "role_labels": {k: selected["role_labels"].get(k, k) if selected else k for k in roles},
        "noncolor_cues": cues, "grayscale_check": gray,
        "notes": notes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List available recipe IDs and names")
    parser.add_argument("--theme", default="", help="User's Chinese or English topic")
    parser.add_argument("--palette", help="Explicit recipe ID, overriding inferred theme")
    parser.add_argument("--reference-image", type=Path, help="Local user-supplied PNG/JPEG etc.")
    parser.add_argument("--reference-colors", nargs="+", action="extend", default=[], metavar="ROLE=#RRGGBB")
    parser.add_argument("--sample", nargs="+", action="extend", default=[], metavar="ROLE=X,Y",
                        help="Point inside component; relative coordinates in displayed image")
    parser.add_argument("--out", type=Path, help="Write UTF-8 JSON here instead of stdout")
    args = parser.parse_args()
    name_map = json.loads(LIBRARY.read_text(encoding="utf-8"))["palettes"]
    try:
        if args.list:
            result = [{"id": p["id"], "name": p["name"], "name_en": p["name_en"]} for p in name_map]
        else:
            if args.reference_image and not args.reference_image.is_file():
                raise ValueError(f"Reference image does not exist: {args.reference_image}")
            if args.sample and not args.reference_image:
                raise ValueError("--sample requires --reference-image")
            locked = hex_colors(args.reference_colors)
            auto = bool(args.reference_image) and not (args.sample or locked)
            if args.reference_image and (auto or args.sample):
                measured = reference_swatches(args.reference_image, args.sample)
                # A role explicitly named by the user takes priority over a sampled pixel.
                measured.update(locked)
                locked = measured
            result = choose(name_map, args.theme, args.palette, locked, auto)
            if args.reference_image:
                result["reference_image"] = str(args.reference_image)
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        sys.stdout.buffer.write(output.encode("utf-8"))


if __name__ == "__main__":
    main()
