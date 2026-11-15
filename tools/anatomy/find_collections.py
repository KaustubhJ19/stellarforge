"""Print collections whose names match keywords with recursive real-mesh counts.
Run: Blender -b <file.blend> --python find_collections.py -- kw1 kw2 ...
"""
import sys, bpy
kws = [k.lower() for k in sys.argv[sys.argv.index("--") + 1:]]
def meshes(col):
    return {o for o in col.all_objects if o.type == "MESH" and len(o.data.vertices) > 10}
for c in bpy.data.collections:
    if any(k in c.name.lower() for k in kws):
        ms = meshes(c)
        print(f"{c.name!r:55} meshes={len(ms):4} verts={sum(len(o.data.vertices) for o in ms):8}")
