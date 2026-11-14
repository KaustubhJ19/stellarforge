"""Export the StellarForge body GLB from Z-Anatomy (Spike B, ticket 01).

Only the structures in the Indicator-to-structure map are exported as their own
named nodes, plus one simplified outline per layer. Everything else is dropped.

Run:
  Blender -b data/z-anatomy/Z-Anatomy/Startup.blend \
      --python tools/anatomy/export_body.py -- <out.glb> [--region <region>] [--female <hra.glb>]

With --region, writes only that region's structures at high detail (no outlines);
the web app loads it the first time the astronaut zooms into the region.

With --female, the organs (heart, lungs, liver, kidneys and the organ outline) come
from the Human Reference Atlas "Body, Female" model (CC BY 4.0), and the male muscle,
skeleton, vessel and brain layers are resized to the female skeleton's height and
labelled approximate in the app.

Derived from Z-Anatomy (CC BY-SA 4.0), itself from BodyParts3D (CC BY 4.0).
The output file is released under CC BY-SA 4.0.
"""
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = ARGS[0]
REGION = ARGS[ARGS.index("--region") + 1] if "--region" in ARGS else None
FEMALE = ARGS[ARGS.index("--female") + 1] if "--female" in ARGS else None

# Female mode: structure id -> HRA "Body, Female" parent objects whose meshes replace it.
FEMALE_ORGANS = {
    "heart": ["VH_F_heart"],
    "lungs": ["VH_F_lungs"],
    "liver": ["VH_F_liver"],
    "kidneys": ["VH_F_kidney"],
}
# Female organ outline: the rest of the HRA viscera.
FEMALE_ORGAN_OUTLINE = [
    "VH_F_digestive_system", "VH_F_urinary_system", "VH_F_reproductive_system", "VH_F_respiratory_system",
]
FEMALE_OUTLINE_BUDGET = 25_000

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


def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def meshes_under(names):
    """Mesh objects anywhere below the named (imported glTF) objects."""
    out = []
    def walk(o):
        if o.type == "MESH" and len(o.data.vertices) > MIN_VERTS:
            out.append(o)
        for c in o.children:
            walk(c)
    for n in names:
        walk(bpy.data.objects[n])
    return out


def female_transforms():
    """Resize the male body to the HRA female body height and place the HRA organs inside it.

    Matches outer surfaces (male muscle layer vs HRA skin): the HRA skeleton is incomplete,
    so its height (1.45 m vs 1.67 m skin) would shrink the male body too far.

    Returns (male_matrix, female_matrix): applied to baked male meshes and to HRA meshes.
    """
    male_lo, male_hi = world_bbox(gather(["Muscular system"], []))
    bpy.ops.import_scene.gltf(filepath=FEMALE)
    fem_lo, fem_hi = world_bbox(meshes_under(["VH_F_integumentary_system"]))
    scale = (fem_hi.z - fem_lo.z) / (male_hi.z - male_lo.z)
    male_centre = Vector(((male_lo.x + male_hi.x) / 2, (male_lo.y + male_hi.y) / 2, male_lo.z))
    # Male: scale about the centre of its feet, so the feet stay put.
    male_m = Matrix.Translation(male_centre) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-male_centre)
    # Female: move the HRA body's feet-centre onto the male one; no scaling.
    fem_centre = Vector(((fem_lo.x + fem_hi.x) / 2, (fem_lo.y + fem_hi.y) / 2, fem_lo.z))
    female_m = Matrix.Translation(male_centre - fem_centre)
    print(f"female: male body {male_hi.z - male_lo.z:.3f} m, female {fem_hi.z - fem_lo.z:.3f} m, scale {scale:.3f}")
    return male_m, female_m


def main():
    exported = []
    used = set()
    male_m, female_m = female_transforms() if FEMALE else (None, None)
    female_ids = set(FEMALE_ORGANS) if FEMALE else set()

    for sid, (layer, cols, names) in STRUCTURES.items():
        objs = gather(cols, names) - used
        if not objs:
            raise SystemExit(f"structure {sid} matched no geometry")
        used |= objs
        if REGION and REGION_OF[sid] != REGION:
            continue
        budget = DETAIL_BUDGET if REGION else STRUCTURE_BUDGET
        props = {"kind": "structure", "layer": layer, "id": sid}
        if sid in female_ids:
            ob = bake(meshes_under(FEMALE_ORGANS[sid]), sid, budget, props)
            ob.data.transform(female_m)
        else:
            ob = bake(objs, sid, budget, props)
            if male_m:
                ob.data.transform(male_m)
        exported.append(ob)
        print(f"structure {sid:20} objects={len(objs)}{' (HRA female)' if sid in female_ids else ''}")

    for layer, (cols, budget) in ({} if REGION else LAYERS).items():
        props = {"kind": "outline", "layer": layer, "id": f"outline.{layer}"}
        if FEMALE and layer == "organs":
            organ_meshes = set(meshes_under(FEMALE_ORGAN_OUTLINE)) - set(meshes_under(sum(FEMALE_ORGANS.values(), [])))
            ob = bake(organ_meshes, f"outline.{layer}", FEMALE_OUTLINE_BUDGET, props)
            ob.data.transform(female_m)
        else:
            ob = bake(gather(cols, []) - used, f"outline.{layer}", budget, props)
            if male_m:
                ob.data.transform(male_m)
        exported.append(ob)
        print(f"outline   {layer:20}{' (HRA female)' if FEMALE and layer == 'organs' else ''}")

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
