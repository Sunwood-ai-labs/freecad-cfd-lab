"""Read-only integrity and syntax checks for the published experiment bundle.

Run from the repository root with: uv run scripts/verify_artifacts.py
No CFD calculation or native FreeCAD/ParaView import is performed.
"""
from pathlib import Path
import ast
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
experiments = root / "experiments"
counts = {"json": 0, "python_sources": 0, "freecad_documents": 0, "manifest_entries": 0}
for path in experiments.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8-sig"))
        counts["json"] += 1
    elif path.suffix in {".py", ".FCMacro"}:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        counts["python_sources"] += 1
    elif path.suffix == ".FCStd":
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None, f"Corrupt FreeCAD ZIP: {path}"
            ET.fromstring(archive.read("Document.xml"))
        counts["freecad_documents"] += 1

manifest = json.loads((experiments / "source-manifest.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    path = root / entry["destination"]
    assert path.is_file(), f"Missing published file: {path}"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["published_sha256"], path
    counts["manifest_entries"] += 1

audit = json.loads((experiments / "family-house-airflow/mesh-geometry-audit.json").read_text(encoding="utf-8"))
assert audit["mesh_cells"] == 538479
assert audit["point_check_pass_count"] == audit["point_check_total"] == 69
adapter = json.loads((experiments / "family-house-airflow/source/adapter-final.json").read_text(encoding="utf-8"))
assert adapter["case_file"] == "case/pv.foam"
assert (experiments / "family-house-airflow" / adapter["building_shell_stl"]).is_file()
print(json.dumps({"status": "pass", **counts}, indent=2))
