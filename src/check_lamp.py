"""Geometric verification; run with cad run src/check_lamp.py."""
import json
from pathlib import Path
import build123d as bd
from cad.build123d import leaves, closest_points, overlap_volume
from lamp import enclosure, lid, tray, adapter_60, adapter_70, adapter_e27, assembled, exploded

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
    for make in (enclosure, lid, tray, adapter_60, adapter_70, adapter_e27, assembled, exploded):
        doc = make()
        part = doc.shape
        size = part.bounding_box().size
        manifest[make.__name__] = {"id": doc.id, "url": doc.url,
            "bounds_mm": [round(size.X, 4), round(size.Y, 4), round(size.Z, 4)],
            "volume_mm3": round(part.volume, 3)}
    kit = assembled().shape
    body = find_part(kit, "amber_enclosure")
    cap = find_part(kit, "lift_off_lid")
    insert = find_part(kit, "removable_tray")
    reducer = find_part(kit, "adapter_60mm_lantern")
    near(kit.bounding_box().size.Z, 256)
    near(closest_points(body, insert).distance, 0)
    near(closest_points(body, cap).distance, 0)
    near(closest_points(insert, reducer).distance, 0)
    inner = plane_coordinate(body, "X", 65)
    outer = plane_coordinate(body, "X", 70)
    skirt = plane_coordinate(cap, "X", 64.6)
    tray_edge = plane_coordinate(insert, "X", 64.6)
    near(closest_points(inner, outer).distance, 5.0)
    near(closest_points(inner, skirt).distance, 0.4)
    near(closest_points(inner, tray_edge).distance, 0.4)
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
    cylindrical_radii = sorted({round(f.geom_adaptor().Cylinder().Radius(), 5)
                              for f in reducer.faces() if f.geom_type == bd.GeomType.CYLINDER})
    assert 30.5 in cylindrical_radii, cylindrical_radii
    # A conservative Ø60 x 145 mm light envelope; does not certify its foot shape.
    light = bd.Pos(0, 0, 8.0) * bd.Cylinder(30, 145, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    for p in leaves(kit):
        near(overlap_volume(p, light), 0)
    near(closest_points(reducer, light).distance, 0.5)
    large_light = bd.Pos(0, 0, 8.0) * bd.Cylinder(50, 150, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    for p in (body, cap, insert):
        near(overlap_volume(p, large_light), 0)
    for make in (adapter_70, adapter_e27):
        alternate = bd.Pos(0, 0, 8.0) * make().shape
        for p in (body, cap, insert):
            near(overlap_volume(p, alternate), 0)
    for lift in (20, 120, 250):
        near(overlap_volume(body, bd.Pos(0, 0, lift) * insert), 0)
    # Negative controls prove that a bad lateral lid placement and oversize lamp fail.
    assert overlap_volume(body, bd.Pos(2, 0, 0) * cap) > 1
    bad_light = bd.Pos(0, 0, 8.0) * bd.Cylinder(32, 145, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    assert overlap_volume(reducer, bad_light) > 1
    manifest["verified"] = {"wall_mm": 5.0, "floor_mm": 5.0, "lid_plate_mm": 5.0, "emboss_text": "VHONE", "emboss_depth_mm": 1.2, "emboss_front_width_mm": round(glyph_bounds.size.X, 3), "emboss_front_height_mm": round(glyph_bounds.size.Z, 3), "lid_and_tray_side_clearance_mm": 0.4,
                            "60mm_light_radial_clearance_mm": 0.5,
                            "light_envelope_mm": [60, 60, 145],
                            "large_light_envelope_mm": [100, 100, 150],
                            "alternate_rings": "no interference with body, cap or tray",
                            "tray_lift_samples_mm": [20, 120, 250],
                            "negative_controls": "passed: shifted lid and oversize light collide"}
    (ROOT / "docs/model_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print("PASS: valid parts; 140 x 141.2 x 256 envelope (including emboss); measured walls, mating gaps, contacts and light fit; negative controls detect interference.")
