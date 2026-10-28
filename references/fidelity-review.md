# Preserve the approved design

Before approval, write an inventory derived from the preview and design. Include every scientifically important feature. Match IDs to planned native objects, not whichever objects survive a simplified reconstruction. Example coordinates are millimeters.

```json
{
  "version": 1,
  "canvas_mm": [180, 100],
  "features": [
    {"name": "Layered interface", "object_ids": ["boundary", "rim"],
     "expected_bbox_mm": [100, 20, 60, 65], "tolerance_mm": 2,
     "details": "Preserve both boundaries and the intervening rim.",
     "min_cubic_segments": 4}
  ],
  "arrows": [
    {"object_id": "inlet", "start_mm": [5, 20], "end_mm": [20, 20],
     "tolerance_mm": 1, "arrow_end": true}
  ],
  "regions": [
    {"name": "Interface detail", "box": [0.55, 0.15, 0.95, 0.9]}
  ]
}
```

`box` uses normalized left, top, right, bottom coordinates. Geometry checks catch missing features, displacement, lost curves, and reversed endpoints. They cannot judge physics, exact contour fidelity, overlap, or visual quality. Choose tolerances reflecting the actual design. Inspect corresponding PPT render crops beside the approved image; never remove a necessary feature or its check simply to pass.

Keep a separate semantic review using [scientific-review.md](scientific-review.md): connectivity, compartment separation, layer/state order, label ownership and transport direction. Verify both the preview and reconstruction against the evidence. Faithfully copying a scientific error does not pass review; a necessary scientific correction requires a revised preview and renewed approval.
