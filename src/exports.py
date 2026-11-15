"""Refresh the print-shop deliverables after an edit: cad run src/exports.py."""
from pathlib import Path
from cad import model
from lamp import enclosure, lid, assembled

ROOT = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    for make in (enclosure, lid):
        doc = make()
        model.export(doc, ROOT / "STL" / f"{make.__name__}.stl", tolerance=0.04)
        model.export(doc, ROOT / "STEP" / f"{make.__name__}.step")
    model.export(assembled(), ROOT / "STEP/amber_01_assembly.step")
    model.export(assembled(), ROOT / "GLB/amber_01.glb", tolerance=0.04)
