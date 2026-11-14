"""Export the StellarForge body GLB from Z-Anatomy (Spike B, ticket 01).

Only the structures in the Indicator-to-structure map are exported as their own
named nodes, plus one simplified outline per layer. Everything else is dropped.

Run:
  Blender -b data/z-anatomy/Z-Anatomy/Startup.blend \
      --python tools/anatomy/export_body.py -- <out.glb> [--region <region>]

With --region, writes only that region's structures at high detail (no outlines);
the web app loads it the first time the astronaut zooms into the region.

Derived from Z-Anatomy (CC BY-SA 4.0), itself from BodyParts3D (CC BY 4.0).
The output file is released under CC BY-SA 4.0.
"""
import sys
import bpy
import bmesh

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = ARGS[0]
REGION = ARGS[ARGS.index("--region") + 1] if "--region" in ARGS else None

# Structure id -> (layer, collections to include, extra object names to include).
# Ids are the contract between this file and the web app's structure map.
STRUCTURES = {
    "brain.prefrontal":   ("brain",    ["Frontal lobe"], []),
    "brain.amygdala":     ("brain",    ["Amygdaloid body"], []),
    "brain.parietal":     ("brain",    ["Parietal lobe"], []),
    "brain.occipital":    ("brain",    ["Occipital lobe"], []),
    "brain.thalamus":     ("brain",    ["Thalamus"], []),
    # Z-Anatomy has no separate suprachiasmatic nucleus; it sits in the hypothalamus.
    "brain.hypothalamus": ("brain",    [], ["Hypothalamus"]),
    "brain.cerebellum":   ("brain",    ["Cerebellum"], []),
    "ear.vestibular":     ("brain",    ["Vestibule", "Vestibulocochlear nerve (VIII)"], []),
    "eye.optic":          ("brain",    [], ["Optic nerve (II).l", "Optic nerve (II).r", "Retina.l", "Retina.r"]),
    "heart":              ("organs",   ["Heart"], []),
    "vessels.carotids":   ("vessels",  [], ["Left common carotid artery", "Right common carotid artery",
                                            "Internal carotid artery.l", "Internal carotid artery.r",
                                            "External carotid artery.l", "External carotid artery.r"]),
    "lungs":              ("organs",   ["Lungs"], []),
    "liver":              ("organs",   ["Liver"], ["Liver"]),
    "kidneys":            ("organs",   [], ["Kidney.l", "Kidney.r"]),
    "bone.hip":           ("skeleton", [], ["Hip bone.l", "Hip bone.r", "Sacrum"]),
    "bone.spine":         ("skeleton", ["Bones of vertebral column"], []),
    "muscle.thigh":       ("muscles",  ["Anterior compartment of thigh"], []),
}

# Layer -> source collections, and triangle budget for its outline.
LAYERS = {
    "muscles":  (["Muscular system"], 60_000),
    "skeleton": (["Skeletal system"], 50_000),
    "vessels":  (["5: Cardiovascular system"], 30_000),
    "organs":   (["Visceral systems"], 25_000),
    "brain":    (["Brain"], 25_000),
}
# Structure id -> zoom region (matches the web app's structure table).
REGION_OF = {
    "brain.prefrontal": "head", "brain.amygdala": "head", "brain.parietal": "head",
    "brain.occipital": "head", "brain.thalamus": "head", "brain.hypothalamus": "head",
    "brain.cerebellum": "head", "ear.vestibular": "head", "eye.optic": "head",
    "heart": "chest", "vessels.carotids": "chest", "lungs": "chest",
    "liver": "abdomen", "kidneys": "abdomen", "bone.spine": "abdomen",
    "bone.hip": "legs", "muscle.thigh": "legs",
}
STRUCTURE_BUDGET = 12_000  # triangles per mapped structure, at most
DETAIL_BUDGET = 60_000     # triangles per structure in a region detail file
MIN_VERTS = 10           # Z-Anatomy label anchors are 2-vertex meshes; skip them


def is_geometry(o):
    if o.type == "MESH":
        return len(o.data.vertices) > MIN_VERTS and not o.name.endswith((".j", ".i", ".t", ".g"))
    if o.type == "CURVE":
        return o.data.bevel_depth > 0 or o.data.bevel_object is not None
    return False


def gather(collections, names):
    objs = set()
    for c in collections:
        objs |= {o for o in bpy.data.collections[c].all_objects if is_geometry(o)}
    for n in names:
        o = bpy.data.objects[n]
        if is_geometry(o):
            objs.add(o)
    return objs


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def bake(objs, name, budget, props):
    """Merge evaluated geometry of objs into one new world-space mesh object."""
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.transform(ev.matrix_world)
        bm.from_mesh(me)
        ev.to_mesh_clear()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    for k, v in props.items():
        ob[k] = v
    bpy.context.scene.collection.objects.link(ob)
    ratio = budget / max(tri_count(me), 1)
    if ratio < 1:
        mod = ob.modifiers.new("dec", "DECIMATE")
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = ob
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier="dec")
    return ob


def main():
    exported = []
    used = set()
    for sid, (layer, cols, names) in STRUCTURES.items():
        objs = gather(cols, names) - used
        if not objs:
            raise SystemExit(f"structure {sid} matched no geometry")
        used |= objs
        if REGION and REGION_OF[sid] != REGION:
            continue
        budget = DETAIL_BUDGET if REGION else STRUCTURE_BUDGET
        exported.append(bake(objs, sid, budget, {"kind": "structure", "layer": layer, "id": sid}))
        print(f"structure {sid:20} objects={len(objs)}")

    for layer, (cols, budget) in ({} if REGION else LAYERS).items():
        objs = gather(cols, []) - used
        exported.append(bake(objs, f"outline.{layer}", budget, {"kind": "outline", "layer": layer, "id": f"outline.{layer}"}))
        print(f"outline   {layer:20} objects={len(objs)}")

    bpy.ops.object.select_all(action="DESELECT")
    for ob in exported:
        ob.select_set(True)
        print(f"  {ob.name:22} tris~{tri_count(ob.data)}")

    bpy.ops.export_scene.gltf(
        filepath=OUT,
        use_selection=True,
        export_format="GLB",
        export_extras=True,
        export_materials="NONE",
        export_normals=True,
        export_texcoords=False,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=7,
    )
    print("WROTE", OUT)


main()
