"""Create source-repository and installable-skill archives without private runtime files."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_FILES = {"SKILL.md", "README.md", "README.en.md", "LICENSE", "CONTRIBUTING.md",
              ".gitignore", ".gitattributes", "requirements-optional.txt"}
SOURCE_DIRS = {"agents", "scripts", "references", "assets", "examples", "docs", ".github"}
SUFFIXES = {".py", ".ps1", ".md", ".json", ".yaml", ".yml", ".txt", ".png", ".pptx"}
SKILL_DIRS = {"agents", "scripts", "references", "assets"}


def selected_files(root):
    files = []
    for path in root.rglob("*"):
        if path.is_symlink(): continue
        if not path.is_file(): continue
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or any(p.startswith(".env") for p in rel.parts): continue
        if len(rel.parts) == 1 and rel.name in ROOT_FILES:
            files.append(path)
        elif rel.parts[0] in SOURCE_DIRS and path.suffix.lower() in SUFFIXES:
            files.append(path)
    return sorted(files)


def package(root, output):
    root = Path(root).resolve(); output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    skill_name = root.name
    version = re.search(r'version:\s*"([0-9.]+)"', (root/"SKILL.md").read_text(encoding="utf-8")).group(1)
    files = selected_files(root)
    required = {"SKILL.md", "README.md", "README.en.md", "LICENSE", "agents/openai.yaml", "scripts/build_pptx.py", "docs/images/engineering-gallery.png", "examples/engineering-gallery.pptx"}
    missing = required - {p.relative_to(root).as_posix() for p in files}
    if missing: raise ValueError("Missing release files: " + ", ".join(sorted(missing)))
    archives = []
    for compact in (False, True):
        name = skill_name + ("-skill" if compact else "") + "-v" + version + ".zip"
        target = output/name
        chosen = []
        for path in files:
            rel = path.relative_to(root)
            if compact:
                if not (rel.as_posix() in {"SKILL.md", "LICENSE", "requirements-optional.txt"} or rel.parts[0] in SKILL_DIRS): continue
                if rel.as_posix() == "scripts/package_release.py": continue
            chosen.append(path)
        with ZipFile(target, "x", compression=ZIP_DEFLATED) as archive:
            for path in chosen: archive.write(path, (Path(skill_name)/path.relative_to(root)).as_posix())
        archives.append({"name":name, "files":len(chosen), "bytes":target.stat().st_size, "sha256":hashlib.sha256(target.read_bytes()).hexdigest()})
    with (output/"SHA256SUMS.txt").open("x", encoding="utf-8") as stream:
        stream.write("".join(x["sha256"]+"  "+x["name"]+"\n" for x in archives))
    with (output/"release-manifest.json").open("x", encoding="utf-8") as stream:
        json.dump({"version":version,"archives":archives},stream,indent=2)
    return archives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(package(args.root, args.output_dir or args.root/"dist"), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__": main()
