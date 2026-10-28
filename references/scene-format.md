# Explicit native scene format (version 1)

The assistant interprets the approved image and writes this file. The builder does not segment an image or infer scientific content. All positions and paths use **millimeters in the full-slide coordinate system**, including children of groups. Text sizes and line widths use points. RGB colors use six hex digits without `#`.

`labels.txt` contains one exact label per line, including panel headings and footnotes. Represent a multiline label on one glossary line using the literal `\n` escape. Repeat a glossary entry when the identical label appears in several text objects. The CLI compares the native text with this approved glossary, preserving counts and normalizing whitespace only. Rich-text subscripts use the same plain characters (for example `H2O`) in the glossary.

```json
{
  "version": 1,
  "width_mm": 180,
  "height_mm": 100,
  "font": "Times New Roman",
  "background": "FFFFFF",
  "group_all": true,
  "elements": [
    {"id":"layer", "type":"rect", "x":10, "y":30, "w":150, "h":50,
     "fill":"DDDDDD", "stroke":"202020", "line_pt":0.65},
    {"id":"label", "type":"text", "x":15, "y":35, "w":60, "h":10,
     "text":"Rock formation", "font_pt":9},
    {"id":"flow", "type":"line", "start":[80,40], "end":[80,70],
     "stroke":"159DDD", "line_pt":1.1, "arrow_end":true}
  ]
}
```

## Objects

- `rect`, `ellipse`: `x`, `y`, `w`, `h`; optional `fill`, `stroke`, `line_pt`.
- `text`: same bounding fields; `text` with newline-separated paragraphs, or `runs` with formatted text; `font_pt`, `font`, `color`, `bold`, `italic`, `align` (`left`, `center`, `right`). Native text has zero internal margins and does not auto-shrink. Inspect overflow after rendering.
- `line`: `start`, `end`, `stroke`, `line_pt`; optional `arrow_start`, `arrow_end`, `dash`. The arrow end points to `end`, including reversed coordinates. These are positioned native connectors, without automatic object binding.
- `polygon`: at least three `points`; closed automatically; optional fill and stroke.
- `path`: `commands` using `["M",x,y]`, `["L",x,y]`, `["C",cx1,cy1,cx2,cy2,x,y]`, `["Z"]`. Cubic control points also must lie on the canvas. Curves remain native editable freeforms.
- `group`: `children`, all using full-slide coordinates. Groups must not be empty. Child order is stacking order.

Fill can be omitted/`null` for transparent interior. A native linear gradient replaces solid fill:

```json
"gradient": {"angle":90, "stops":[[0,"DDDDDD"],[100,"F4CCCC"]]}
```

Formatted chemical text example:

```json
"runs": [{"text":"H"},{"text":"2","baseline":-25,"font_pt":7},{"text":"O"}]
```

`baseline` is a percentage of font height (negative for subscript). A `runs` array forms one paragraph. For multiline rich text, use multiple text objects. IDs must be unique. The outer figure group is generated automatically unless `group_all` is false.

## Limits

One slide per build. No raster image objects, arbitrary SVG imports, charts, tables, or font embedding. Add those only through an explicitly disclosed alternate backend. Unfilled/open paths remain unfilled unless a fill is assigned. No automatic text measurement, collision correction, curve recognition, or scientific inference. The saved PPTX must still be rendered and inspected.

The full repository includes `examples/cases/04-carbon-capture.json`, a conceptual scene with detailed curves and components. Use it to understand the format, not as a compulsory layout or a substitute for approval in a new task.
