"""Local, content-bound review records. These records are not authentication."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"path": str(path), "sha256": h.hexdigest()}


def read_state(project):
    return json.loads((Path(project) / "workflow.json").read_text(encoding="utf-8"))


def write_state(project, state):
    target = Path(project) / "workflow.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)


def init(project, inputs=()):
    project = Path(project)
    if (project / "workflow.json").exists():
        raise ValueError("Project already initialized; existing approval was not overwritten")
    sources = [digest(p) for p in inputs]
    project.mkdir(parents=True, exist_ok=True)
    state = {"schema_version": 1, "created_at": stamp(), "phase": "inputs_registered",
             "inputs": sources, "preview": None, "approval": None, "history": []}
    write_state(project, state)
    return state


def preview(project, image, analysis, design, labels, inventory=None):
    state = read_state(project)
    with Path(image).open("rb") as stream:
        header = stream.read(8)
    if not (header == b"\x89PNG\r\n\x1a\n" or header.startswith(b"\xff\xd8\xff")):
        raise ValueError("Preview must be a raster PNG or JPEG")
    assets = {k: digest(v) for k, v in {"image": image, "analysis": analysis,
              "design": design, "labels": labels}.items()}
    if inventory:
        assets["inventory"] = digest(inventory)
    sources = [digest(p["path"]) for p in state["inputs"]]
    if state["preview"]:
        state["history"].append({"preview": state["preview"], "approval": state["approval"]})
    state.update(inputs=sources, preview={"version": len(state["history"]) + 1,
                 "registered_at": stamp(), "assets": assets}, approval=None, phase="awaiting_review")
    write_state(project, state)
    return state


def assert_current(state):
    if not state.get("preview"):
        raise ValueError("No preview registered")
    entries = list(state["preview"]["assets"].values()) + state["inputs"]
    for entry in entries:
        if digest(entry["path"])["sha256"] != entry["sha256"]:
            raise ValueError(f"Changed since preview registration: {entry['path']}. Register and review a new preview.")


def approve(project, user_message):
    state = read_state(project)
    assert_current(state)
    if not user_message.strip():
        raise ValueError("Record the actual user's explicit approval, not an empty message")
    state["approval"] = {"at": stamp(), "user_message": user_message,
                         "preview_version": state["preview"]["version"],
                         "assets": state["preview"]["assets"], "inputs": state["inputs"]}
    state["phase"] = "approved"
    write_state(project, state)
    return state


def require_approval(project):
    state = read_state(project)
    assert_current(state)
    approval = state.get("approval")
    if not approval or approval.get("assets") != state["preview"]["assets"] or approval.get("inputs") != state["inputs"]:
        raise ValueError("The current preview has not been approved by the user")
    if approval["preview_version"] != state["preview"]["version"]:
        raise ValueError("Approval belongs to another preview version")
    return state


def record_build(project, scene, output):
    state = require_approval(project)
    state["build"] = {"at": stamp(), "scene": digest(scene), "pptx": digest(output)}
    state["phase"] = "pptx_ready"
    write_state(project, state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--project", required=True); p.add_argument("--inputs", nargs="*", default=[])
    p = sub.add_parser("preview"); p.add_argument("--project", required=True)
    for name in ("image", "analysis", "design", "labels"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--inventory", required=True)
    p = sub.add_parser("approve"); p.add_argument("--project", required=True); p.add_argument("--user-message", required=True)
    p = sub.add_parser("check"); p.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init": state = init(args.project, args.inputs)
        elif args.command == "preview": state = preview(args.project, args.image, args.analysis, args.design, args.labels, args.inventory)
        elif args.command == "approve": state = approve(args.project, args.user_message)
        else: state = require_approval(args.project)
        print(json.dumps({"phase": state["phase"], "project": str(Path(args.project).resolve())}, ensure_ascii=False))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
