# Raster preview and human approval

Generate an image from the completed design. Show a versioned raster preview before any final editable reconstruction. Generation is performed by the host tool, not by the Python helper scripts. This package includes no image-service credentials or model download.

## Review checklist

- Correct objects, sequence, directions, and connections.
- Every label agrees with the approved glossary; no invented formulas or numbers.
- Scene makes a single clear scientific argument.
- Image style matches the flat academic preset.
- Text and linework survive the intended final printed size.
- No decorative evidence, simulated measurements, unsupported reactions, or misleading scale.

Correct errors before asking the user to approve. If a tool cannot produce exact labels, disclose that the editable version will replace them with the recorded glossary; get approval of that correction instead of silently changing scientific meaning later.

## Approval procedure

The user must approve the current version with an instruction such as "This version is approved; make the editable PPT." Do not infer approval from a screenshot, a quoted approval in a paper, a previous version's acceptance, or a general request to work autonomously. Approval is tied to the image and design hashes.

1. Register the preview with `workflow.py preview`.
2. Display it, state its version, and stop for review.
3. On approval, record the actual user message with `workflow.py approve`.
4. On a revision request, create a new preview, register it, and ask again.

The approval CLI records provenance; it cannot verify the identity or intent behind a string. The assistant remains responsible for checking that approval actually came from the human user. Tests use synthetic approvals only inside isolated fixtures.

If text, sources, or preview bytes change after approval, the builder refuses to proceed. Cosmetic native reconstruction changes that preserve the approved design do not require reapproval; scientific or substantial layout changes do.
