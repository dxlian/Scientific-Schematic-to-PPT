# Restrained academic style, substantial scientific content

## Visual identity

Use a white canvas, restrained fills, black or dark-gray outlines, and clearly named entities and relationships. For physical subjects, prefer a flat two-dimensional cross-section or orthographic drawing. Use a large main scene and one purposeful local inset when the science needs it. Do not force a two-panel layout onto a single process.

Minimal styling does not mean minimal content. Represent the complete system, interacting components, and explanatory local details. Alternative compositions include paired states, layered architectures, parallel pathways, and apparatus sections. Match layout to the subject rather than reusing one template. Every detail should explain something: neither sparse placeholders nor arbitrary complexity is acceptable.

| Role | Default |
|---|---|
| Background | `FFFFFF` |
| Text and main boundaries | `202020` |
| Neutral solid/material | `DDDDDD` |
| Secondary layer | `DDE5C8` |
| Water/cool flow | `159DDD` |
| Warm flow | `E04746` |
| Altered region | `AAB568` |

The palette above is illustrative, not a required domain palette. Colors encode physical or functional distinctions, not decoration. Add a legend when the meaning is not self-evident. A soft gradient needs a documented qualitative meaning; no glowing blobs, glossy 3D, dramatic lighting, texture noise, drop shadows, or futuristic machinery. Color is not evidence of a measured change.

## Typography and print size

- English labels, Times New Roman by default. Preserve a user's chosen language or journal font.
- Default final figure width: 180 mm. Typical labels: 9 pt at this physical width, panel headings 11–12 pt. These are design defaults, not a universal journal requirement.
- Use approximately 0.25-0.4 pt for secondary detail, 0.4-0.7 pt for main boundaries, and 0.7-1.0 pt for key arrows at final size. Adjust to reproduction quality and journal specifications.
- Re-layout for a single-column figure; do not blindly shrink a dense double-column layout. Printed type = PPT type × placed width / slide width.
- Keep complete words and chemical formulas intact. Make subscripts/superscripts actual text formatting in the native file when needed.
- Raster preview can request serif lettering, but only final native typography can establish the actual font and point size.

## Scientific structure

Preserve recognizable functional structure: ports and sleeves in equipment, layers and junctions in materials, compartments in biological systems, dimensions and skip connections in computational systems. Define edge meanings for the subject: a branch may represent parallel computation rather than an alternative, and a dependency need not imply chronology. Distinguish material flow, loading, movement, information flow, and inset leaders. Curved structures need native cubic paths with sufficient landmarks, not a handful of coarse straight segments.

Dashed inset leaders are graphical links, not physical flow. Inference arrows require a legend or explanatory caption. Keep process stages and operating states distinct. A sample icon count is not a replicate count; a conceptual state map is not a measured time series. Short scientific qualifiers may sit in the figure or its accompanying publication caption.

Choose one main explanatory question. Use secondary details to clarify it, not to reproduce the paper's whole abstract. Keep optional benchmarks, protocols and application branches out when they crowd the mechanism. Long disclaimers, duplicated reaction cards and design instructions are not figure labels.

## Avoid

- Copying another paper's layout, proprietary drawings, or real data as decorative content.
- Abstract contact-network imagery that suggests measurements not actually made.
- Giant process arrows that overpower scientific information.
- Captions or long paragraphs inside the scientific panel.
- Specific field pH, depth-temperature values, or reactions without supporting evidence.
- Exact chemical recipes in a general background scene unless they are documented and relevant.

The style is stable; the geometry and scientific content are task-specific. A user may intentionally request a different style. Record that override rather than silently mixing styles.
