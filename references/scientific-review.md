# Evidence and semantic review

Use this alongside visual review for research-derived schematics. These are manual scientific checks, not functions performed by the geometric validator.

## Select the scientific focus

Record the question the figure answers and a small set of necessary relationships. Distinguish an original conceptual illustration from a reconstruction of a specific apparatus. Do not invent dimensions, component counts, material placement or anatomy to make the image look complete. Biomimetic inspiration does not imply biological anatomy.

For each substantive feature, record its source locator and evidence type: conceptual, hypothesized, source-reported, simulated or measured. Keep any qualification necessary to understand the figure with the figure or its publication caption. Never generate calibrated heatmaps, spectra, trajectories or microscopy as visual decoration.

## Bind labels to their meaning

Maintain separate lists for visible labels and non-rendering instructions. Each label should name its target entity, interface or relationship. Object IDs, review statuses, exclusions and layout notes do not belong in the rendered text. Check the image for unexpected labels and arrows pointing to the wrong material.

Bind numerical annotations to value, unit, metric, device or specimen, conditions, evidence type and source locator. Distinguish fabrication from operating conditions, half-cell from full-cell results, certified from scanned efficiency, and laboratory from clinical findings. Do not attach a published benchmark to newly invented geometry. If the required context will not fit, omit the numerical annotation.

## Check relationships, not just objects

- Apparatus: trace each directed circuit; every necessary chamber must have distinct functional inlet/outlet ports, without unintended bypasses. Match independent circuits to their actual controls and sources.
- Layered devices: verify layer order, electrode polarity, carrier direction, and which regions a bracket spans.
- Biological systems: verify compartment separation, air-liquid interfaces, barrier orientation and external versus intrinsic actuation.
- Mechanics: distinguish state symbols from actual geometry; preserve entities/counts between states, and separate loading, propagation and material motion.
- Field-driven systems: check vector directions and the direction of induced motion or torque. A bidirectional decoration cannot stand in for a directional physical response.
- Material networks: distinguish periodic meshes from nonwoven fibers and random porous regions. Preserve relevant connected paths, interfaces and occlusions without implying measured microstructure.
- Computing: verify tensor dimensions, operation order, branches, shared weights and data/control paths.
- Chemistry: distinguish dissolved species, precipitated solids and gases; do not imply an unsupported reaction or missing source of a reactant.

The main view and its enlargement must agree. Matched port labels may replace unreadable long circuit routes if their meaning is explicit. Remove redundant annotations rather than shrinking them below useful print size.

When labels assert equal volumes, matched geometry or identical starting conditions, inspect the drawing for that equality. When a material layer appears only after a process, ensure that its label points into that layer rather than an adjacent collector or substrate. Check the final rendered leader endpoints, not only their coordinates in the scene.

## Record what was actually done

Keep a private review record tied to the artifact revision: checks performed, observed issues, corrections and unresolved items. Separate source reading, preview generation, scientific inspection, human reconstruction approval, native build, native render and visual comparison. Use pending or not-run where appropriate. A generated PNG is not an editable PPT; successful serialization is not visual verification.

Source-only or design-only outputs are valid when requested. Showcase captions must match the actual deliverable. A set of examples exercises the workflow but does not establish universal reliability, and journal prestige is not validation of the newly drawn schematic.
