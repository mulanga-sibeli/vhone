"""Geometric verification; run with cad run src/check_lamp.py."""
import json
from pathlib import Path
import build123d as bd
from cad.build123d import leaves, closest_points, overlap_volume
from lamp import enclosure, lid, assembled, exploded

ROOT = Path(__file__).resolve().parent.parent


def find_part(tree, label):
    matches = [p for p in leaves(tree) if p.label == label]
    if len(matches) != 1:
        raise ValueError(f"Expected one {label}, found {len(matches)}")
    return matches[0]


def near(actual, expected):
    assert abs(actual-expected) < 1e-5, (actual, expected)


def plane_coordinate(shape, axis, value):
    # Locate measured planar wall faces, not bounding-box stand-ins for bores.
    faces = [f for f in shape.faces() if f.geom_type == bd.GeomType.PLANE
             and abs(getattr(f.center(), axis)-value) < 1e-5
             and abs(getattr(f.normal_at(), axis)) > 0.999]
    assert faces, (axis, value)
    return max(faces, key=lambda f: f.area)


if __name__ == "__main__":
    manifest = {}
    for make in (enclosure, lid, assembled, exploded):
        doc = make()
        part = doc.shape
        size = part.bounding_box().size
        manifest[make.__name__] = {"id": doc.id,
            "bounds_mm": [round(size.X, 4), round(size.Y, 4), round(size.Z, 4)],
            "volume_mm3": round(part.volume, 3)}
    kit = assembled().shape
    body = find_part(kit, "amber_enclosure")
    cap = find_part(kit, "lift_off_lid")
    assert len(list(leaves(kit))) == 2
    near(kit.bounding_box().size.Z, 256)
    near(closest_points(body, cap).distance, 0)
    inner = plane_coordinate(body, "X", 65)
    outer = plane_coordinate(body, "X", 70)
    skirt = plane_coordinate(cap, "X", 64.6)
    near(closest_points(inner, outer).distance, 5.0)
    near(closest_points(inner, skirt).distance, 0.4)
    for axis, sign in (("X", -1), ("Y", -1), ("Y", 1)):
        near(closest_points(plane_coordinate(body, axis, sign*65), plane_coordinate(body, axis, sign*70)).distance, 5.0)
    near(body.bounding_box().min.Y, -71.2)
    glyph_faces = [f for f in body.faces() if f.geom_type == bd.GeomType.PLANE
                   and abs(f.center().Y+71.2) < 1e-5 and f.normal_at().Y < -0.999]
    assert len(glyph_faces) == 5, len(glyph_faces)
    glyph_bounds = bd.Compound(children=glyph_faces).bounding_box()
    near(glyph_bounds.center().X, 0)
    near(glyph_bounds.center().Z, 125)
    near(closest_points(plane_coordinate(body, "Z", 0), plane_coordinate(body, "Z", 5)).distance, 5.0)
    near(cap.bounding_box().max.Z, 256)
    near(closest_points(plane_coordinate(cap, "Z", 251), plane_coordinate(cap, "Z", 256)).distance, 5.0)
    # User supplied L x H = 77 x 40 mm, with no separate width.
    # Check a conservative 77 mm square footprint, including a round base of Ø77.
    floor = plane_coordinate(body, "Z", 5)
    holder = bd.Pos(0, 0, floor.center().Z) * bd.Box(
        77, 77, 40, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    for part in (body, cap):
        near(overlap_volume(part, holder), 0)
    near(closest_points(floor, holder).distance, 0)
    clearances = []
    for axis in ("X", "Y"):
        for sign in (-1, 1):
            wall = plane_coordinate(body, axis, sign*65)
            distance = closest_points(wall, holder).distance
            near(distance, 26.5)
            clearances.append(distance)
    near(closest_points(plane_coordinate(body, "X", -65), inner).distance, 130)
    lid_underside = plane_coordinate(cap, "Z", 251)
    headroom = closest_points(lid_underside, holder).distance
    near(headroom, 206)
    # Verify the same footprint's vertical insertion path through the open cup.
    # A swept solid checks the entire path, not just a few sampled positions.
    insertion_sweep = bd.Pos(0, 0, floor.center().Z) * bd.Box(
        77, 77, 300, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    near(overlap_volume(body, insertion_sweep), 0)
    # Negative controls demonstrate that overlap tests detect invalid placements.
    assert overlap_volume(body, bd.Pos(2, 0, 0) * cap) > 1
    assert overlap_volume(body, bd.Pos(27, 0, 0) * holder) > 1
    assert overlap_volume(body, bd.Pos(0, 0, -1) * holder) > 1
    manifest["verified"] = {
        "wall_mm": 5.0, "floor_mm": 5.0, "lid_plate_mm": 5.0,
        "emboss_text": "VHONE", "emboss_depth_mm": 1.2,
        "emboss_front_width_mm": round(glyph_bounds.size.X, 3),
        "emboss_front_height_mm": round(glyph_bounds.size.Z, 3),
        "lid_side_clearance_mm": 0.4,
        "internal_floor_width_depth_mm": [130, 130],
        "holder_check_envelope_mm": [77, 77, 40],
        "holder_width_assumption": "Width no greater than supplied 77 mm length; square envelope also contains a diameter-77 mm round base.",
        "holder_mount_surface_z_mm": round(floor.center().Z, 3),
        "holder_wall_clearance_mm": round(min(clearances), 3),
        "holder_top_to_central_lid_underside_mm": round(headroom, 3),
        "holder_insertion": "77 mm square vertical sweep clears open enclosure",
        "negative_controls": "passed: shifted lid, shifted holder and holder below floor collide",
        "limits": ["new bulb dimensions not supplied; bulb fit not checked",
                   "adhesive thickness, bond strength and thermal performance not checked",
                   "holder envelope check only; no vendor CAD or universal E27 holder dimensions"]
    }
    (ROOT / "docs/model_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print("PASS: two printable parts; 140 x 141.2 x 256 mm envelope; measured 5 mm walls/floor/lid and 0.4 mm lid side clearance.")
    print("PASS: centred 77 x 77 x 40 mm holder envelope rests on floor without overlap; 26.5 mm side clearance; 206 mm to central lid underside; full insertion sweep clear.")
    print("PASS: negative controls detect shifted lid, shifted holder and holder penetrating floor.")
    print("LIMIT: holder width assumed <=77 mm; new bulb fit, adhesive and operating temperatures not checked.")
