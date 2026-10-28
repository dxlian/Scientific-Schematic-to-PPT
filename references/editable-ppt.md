# Native reconstruction and verification

Map the approved image to a scene, preserving proportions, labels, stacking, and physical connections. Never use a full-slide screenshot with transparent labels laid on top and call it editable.

## Preferred representation

Text -> native text box with explicit font. Simple object -> native shape. Fracture/layer -> native freeform or cubic path. Flow and loading -> native line/arrow. A set of related objects -> native group with independently selectable children.

Create an outer figure group when convenient, with panel or component groups inside. Preserve stacking order: moving all labels into a separate top-level group can incorrectly reorder occlusions. Bind connectors when the selected backend supports it; the bundled builder uses positioned lines and does not promise automatic connector rerouting after objects move.

The bundled builder is intentionally small. It supports explicit scene geometry, not automatic segmentation, editable charts, photos, video, or import of arbitrary SVG. Use an available native presentation backend for those cases and keep evidence intact. Do not claim an untested alternative backend works.

## Scope and compatibility checks

`audit_pptx.py` counts native objects, groups, freeforms, images, fonts, zero-size geometry, placeholders, and grouping locks. It checks duplicate shape IDs and package relationships. It cannot establish semantic correctness, text fit, or app-level groupability.

Use `render_check.ps1` on Windows with an installed PowerPoint or WPS application. Export the actual saved PPTX, exercise group and ungroup in memory, and report each operation separately. Rendering success in one app is not a guarantee for all Office versions. Do not save test changes or close other open presentations.

On other platforms, use an available renderer; document limitations. Do not install Office, change registry entries, enable macros, or bypass security settings. A timeout is a reason to inspect application state, not start repeated copies.

## Final review

Compare to the approved image panel by panel. Check all exact label strings, arrow directions, formulas, units, object bounds, overlap, line thickness, font size at print scale, and intended color semantics. Pixel similarity is optional and diagnostic only: vector simplification can be appropriate, and a high score cannot prove editability.

Deliver the `.pptx` and actual rendered `.png`, plus a brief disclosure of differences or unverified compatibility. Keep source analysis and validation details in the local project. Do not add mandatory personal branding or watermarks to the user's scientific figure.
