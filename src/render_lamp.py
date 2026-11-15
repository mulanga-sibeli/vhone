"""Appearance study from verified CAD. The internal emitter is illustrative only."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from cad.blender import load

ROOT = Path(__file__).resolve().parent.parent
final = "--final" in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
lamp = load(ROOT / "GLB/amber_01.glb")
scene.render.engine = "CYCLES"
scene.render.compositor_device = "CPU"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            break
    except (TypeError, RuntimeError):
        continue
for d in prefs.devices:
    d.use = d.type != "CPU"
scene.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
print("Render device:", scene.cycles.device)
scene.cycles.samples = 48 if final else 32
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 12
scene.cycles.transmission_bounces = 8
scene.render.resolution_x = 1200 if final else 1000
scene.render.resolution_y = 1200 if final else 1000
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.world = bpy.data.worlds.new("warm studio")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.43, 0.34, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.16

def material(name, color, rough=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    return mat

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.0002))
bpy.context.object.data.materials.append(material("sand studio floor", (0.34,0.29,0.23,1)))

aim = bpy.data.objects.new("camera aim", None)
aim.location = (0, 0, 0.125)
scene.collection.objects.link(aim)
camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
scene.collection.objects.link(camera)
camera.location = (0.52, -0.78, 0.40)
camera.data.lens = 70
camera.constraints.new("TRACK_TO").target = aim
scene.camera = camera

def area(name, location, energy, size):
    obj = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    scene.collection.objects.link(obj)
    obj.location = location
    obj.data.energy, obj.data.shape, obj.data.size = energy, "DISK", size
    obj.constraints.new("TRACK_TO").target = aim

area("large softbox", (-0.35,-0.45,0.65), 22, 0.6)
area("edge softbox", (0.3,0.3,0.5), 35, 0.4)

# A simplified light source, not a supplied part or manufacturer photometric model.
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.027, depth=0.11, location=(0,0,0.08))
emitter = bpy.context.object
emitter.name = "illustrative rechargeable light envelope"
mat = material("illustrative warm glow", (1,0.94,0.79,1))
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Emission Color"].default_value = (1.0,0.67,0.30,1)
bsdf.inputs["Emission Strength"].default_value = 5
emitter.data.materials.append(mat)
light = bpy.data.objects.new("illustrative internal illumination", bpy.data.lights.new("illustrative internal illumination", "POINT"))
scene.collection.objects.link(light)
light.location = (0,0,0.15)
light.data.energy, light.data.color, light.data.shadow_soft_size = 0.5, (1,0.75,0.43), 0.025

scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(ROOT / "previews" / ("amber_01_render.png" if final else "amber_01_draft.png"))
bpy.ops.render.render(write_still=True)
