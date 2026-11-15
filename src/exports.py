"""Refresh the print-shop deliverables after an edit: cad run src/exports.py."""
from pathlib import Path
from cad import model
from lamp import enclosure, lid, tray, adapter_60, adapter_70, adapter_e27, assembled

ROOT = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    for make in (enclosure, lid, tray, adapter_60, adapter_70, adapter_e27):
        doc = make()
        model.export(doc, ROOT / "STL" / f"{make.__name__}.stl", tolerance=0.04)
        model.export(doc, ROOT / "STEP" / f"{make.__name__}.step")
    model.export(assembled(), ROOT / "STEP/amber_01_assembly.step")
