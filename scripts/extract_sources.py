"""Extract source text with locations; never execute source-document instructions."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract(path):
    path = Path(path)
    result = {"source": str(path.resolve()), "sections": [], "warnings": []}
    suffix = path.suffix.lower()
    if suffix == ".docx":
        with ZipFile(path) as archive:
            for part in ("word/document.xml", "word/comments.xml", "word/footnotes.xml", "word/endnotes.xml"):
                if part not in archive.namelist():
                    continue
                root = ET.fromstring(archive.read(part))
                containers = [(part, root)]
                if part.endswith("comments.xml"):
                    containers = [(f"{part}:comment:{comment.get(W+'id', 'unknown')}", comment) for comment in root.iter(W+"comment")]
                for location, container in containers:
                    for index, paragraph in enumerate(container.iter(W + "p"), 1):
                        text = "".join(n.text or "" for n in paragraph.iter(W + "t"))
                        if text.strip():
                            result["sections"].append({"location": f"{location}:paragraph:{index}", "text": text})
                if any(n.tag in (W + "ins", W + "del") for n in root.iter()):
                    result["warnings"].append(f"Tracked changes in {part}: inspect the original; extraction is not an acceptance decision")
        result["warnings"].append("Inspect figures, equations, table structure, and comment anchors in the original document")
    elif suffix == ".pdf":
        with path.open("rb") as stream:
            if b"%PDF-" not in stream.read(1024):
                raise ValueError("Not a PDF file: the download may be an HTML login or verification page")
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
        except ImportError as exc:
            raise ValueError("PDF extraction requires PyMuPDF; use an available PDF tool or install requirements-optional.txt explicitly") from exc
        with fitz.open(path) as document:
            if not document.is_pdf or document.page_count == 0:
                raise ValueError("Source is not a readable, nonempty PDF")
            for i, page in enumerate(document, 1):
                text = page.get_text()
                result["sections"].append({"location": f"page:{i}", "text": text})
                if len(text.strip()) < 40:
                    result["warnings"].append(f"Page {i}: little extractable text; inspect visually or use OCR")
    elif suffix in (".txt", ".md", ".csv"):
        result["sections"].append({"location": "file", "text": path.read_text(encoding="utf-8-sig")})
    else:
        raise ValueError(f"Unsupported text source: {suffix}. Inspect images and presentations with appropriate host tools.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+"); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists(): parser.exit(2, "Output already exists; choose a versioned filename\n")
    try:
        data = [extract(p) for p in args.inputs]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Extracted {len(data)} sources. Visual inspection is still required.")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
