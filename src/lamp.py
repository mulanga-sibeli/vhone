"""AMBER / 01 — serviceable rectangular battery lamp, dimensions in mm.

All individual parts are modelled flat on their print bed, Z up.
Check each printable model:
cad model dfm ID --process printing --technology fdm --material petg \
    --nozzle 0.4 --layer-height 0.2 --build-volume 256x256x256
Assembly: cad model interference ID
Reference: examples/cosmos_723682210.webp; dimensions are design choices.
"""
import build123d as bd
from bd_materials import plastics
from bd_materials.processes import fdm
from cad import model

WIDTH = 140.0
DEPTH = 140.0
BODY_HEIGHT = 250.0
WALL = 5.0
FLOOR = 5.0
CORNER = 2.4
INNER_CORNER = 0.8
EMBOSS_TEXT = "VHONE"
EMBOSS_DEPTH = 1.2
EMBOSS_FONT_SIZE = 20.0
EMBOSS_CENTER_Z = 125.0
FIT = 0.4                 # radial/per-side clearance, not diametral
LID_THICKNESS = 5.0
LID_GAP = 1.0
SKIRT_HEIGHT = 8.0
SKIRT_WALL = 2.0
TRAY_THICKNESS = 3.0
SEAT_DIAMETER = 102.0
SEAT_WALL = 2.0
SEAT_HEIGHT = 8.0
ASSEMBLED_HEIGHT = BODY_HEIGHT + LID_GAP + LID_THICKNESS


def box(w, d, h, x=0, y=0, z=0):
    return bd.Pos(x, y, z) * bd.Box(w, d, h, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))


def cylinder(diameter, height, z=0):
    return bd.Pos(0, 0, z) * bd.Cylinder(diameter / 2, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))


def rounded_box(w, d, h, radius, z=0):
    return bd.Pos(0, 0, z) * bd.extrude(bd.RectangleRounded(w, d, radius), amount=h)


def finish(shape, label, amber=True):
    shape.label = label
    shape.material = plastics.petg(process=fdm(layer_height_mm=0.2))
    if amber:
        shape.material.pbr = shape.material.pbr.override(transmission=1.0, roughness=0.28, ior=1.57)
        shape.color = "#E99B42"
    else:
        shape.color = "#E7D8BC"
    assert shape.is_valid, label
    assert len(shape.solids()) == 1, (label, len(shape.solids()))
    return shape


@model
def enclosure():
    outer = rounded_box(WIDTH, DEPTH, BODY_HEIGHT, CORNER)
    inner = rounded_box(WIDTH - 2*WALL, DEPTH - 2*WALL, BODY_HEIGHT, INNER_CORNER, FLOOR)
    part = outer - inner
    # Narrow 3 mm bridges: eight low intake slots on each of two opposing sides.
    for y in (-DEPTH/2, DEPTH/2):
        for x in (-28, -20, -12, -4, 4, 12, 20, 28):
            part = part - box(3, 2*WALL+2, 8, x=x, y=y, z=8)
    # Raised lettering faces the viewer on -Y; slight penetration fuses it to the wall.
    letters = bd.Text(EMBOSS_TEXT, EMBOSS_FONT_SIZE, font="DejaVu Sans", font_style=bd.FontStyle.BOLD)
    bounds = letters.bounding_box()
    letters = bd.Pos(-bounds.center().X, -bounds.center().Y, 0) * letters
    # Oblique relief rises 1 mm for every 1 mm outward: underside >=45 degrees.
    relief = bd.extrude(letters, amount=(EMBOSS_DEPTH+0.2)*2**0.5, dir=(0, 1, 1))
    part += bd.Pos(0, -DEPTH/2+0.2, EMBOSS_CENTER_Z-EMBOSS_DEPTH-0.2) * bd.Rot(90, 0, 0) * relief
    assert abs(part.bounding_box().min.Y - (-DEPTH/2-EMBOSS_DEPTH)) < 1e-6
    assert abs(part.bounding_box().size.Z - BODY_HEIGHT) < 1e-6
    return finish(part, "amber_enclosure")


@model
def lid():
    # Printed cosmetic face on the bed, turned over for assembly.
    part = rounded_box(WIDTH, DEPTH, LID_THICKNESS, CORNER)
    skirt_w, skirt_d = WIDTH-2*WALL-2*FIT, DEPTH-2*WALL-2*FIT
    skirt = rounded_box(skirt_w, skirt_d, SKIRT_HEIGHT, 2.0, LID_THICKNESS)
    skirt -= box(skirt_w-2*SKIRT_WALL, skirt_d-2*SKIRT_WALL, SKIRT_HEIGHT+1, z=LID_THICKNESS)
    # Open channels from cavity to the 1 mm shadow gap, no large bridges.
    for y in (-skirt_d/2, skirt_d/2):
        skirt -= box(24, 8, SKIRT_HEIGHT+1, y=y, z=LID_THICKNESS)
    part += skirt
    # Four stop pads rest on the rim, maintaining the ventilation gap.
    for x in (-48, 48):
        for y in (-DEPTH/2+(WALL+0.8)/2, DEPTH/2-(WALL+0.8)/2):
            part += box(8, WALL+0.8, LID_GAP, x=x, y=y, z=LID_THICKNESS)
    return finish(part, "lift_off_lid")


@model
def tray():
    part = rounded_box(WIDTH-2*WALL-2*FIT, DEPTH-2*WALL-2*FIT, TRAY_THICKNESS, 2)
    # Ribbon slots: a removable ribbon loop lifts the tray out of the deep body.
    for x in (-60, 60):
        part -= box(3, 12, TRAY_THICKNESS+2, x=x, z=-1)
    seat = cylinder(SEAT_DIAMETER+2*SEAT_WALL, SEAT_HEIGHT, TRAY_THICKNESS)
    seat -= cylinder(SEAT_DIAMETER, SEAT_HEIGHT+1, TRAY_THICKNESS)
    # Four open-top finger/air notches, retaining four connected cradle arcs.
    for angle in (0, 90, 180, 270):
        seat -= bd.Rot(0, 0, angle) * box(12, 12, SEAT_HEIGHT+1, x=SEAT_DIAMETER/2, z=TRAY_THICKNESS)
    part += seat
    return finish(part, "removable_tray", amber=False)


def adapter_body(bore, height, label):
    # Full flange locates in the tray; an upright collar supports the light.
    outer = SEAT_DIAMETER-2*FIT
    part = cylinder(outer, 2.4) - cylinder(bore, 3.4)
    collar = cylinder(bore+4, height, 2.4) - cylinder(bore, height+1, 2.4)
    part += collar
    # Finger notches in the flange, clear of the collar.
    for x in (-outer/2, outer/2):
        part -= box(8, 12, 3.4, x=x, z=-0.5)
    return finish(part, label, amber=False)


@model
def adapter_60():
    return adapter_body(61.0, 10, "adapter_60mm_lantern")


@model
def adapter_70():
    return adapter_body(70.5, 6, "adapter_69_5mm_puck")


@model
def adapter_e27():
    # Mechanical cradle only. No electrical contacts or printed screw thread.
    return adapter_body(28.4, 24, "adapter_usb_e27_mechanical_only")


@model
def assembled():
    body = enclosure().shape
    cap = bd.Pos(0, 0, ASSEMBLED_HEIGHT) * bd.Rot(180, 0, 0) * lid().shape
    insert = bd.Pos(0, 0, FLOOR) * tray().shape
    reducer = bd.Pos(0, 0, FLOOR+TRAY_THICKNESS) * adapter_60().shape
    result = bd.Compound(children=[body, cap, insert, reducer], label="AMBER_01")
    assert abs(result.bounding_box().size.Z - ASSEMBLED_HEIGHT) < 1e-6
    return result


@model
def exploded():
    # Side-by-side components expose the opening and holder, without hiding either.
    body = enclosure().shape
    cap = bd.Pos(0, 0, ASSEMBLED_HEIGHT+65) * bd.Rot(180, 0, 0) * lid().shape
    insert = bd.Pos(195, 0, 0) * tray().shape
    reducer = bd.Pos(195, 0, 35) * adapter_60().shape
    return bd.Compound(children=[body, cap, insert, reducer], label="AMBER_01_parts")


if __name__ == "__main__":
    assembled()
    exploded()
    adapter_70()
    adapter_e27()
