"""Print mesh objects whose names match keywords, with their top collection.
Run: Blender -b <file.blend> --python find_structures.py -- kw1 kw2 ...
"""
import sys, bpy
kws = [k.lower() for k in sys.argv[sys.argv.index("--") + 1:]]
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    n = o.name.lower()
    if any(k in n for k in kws):
        cols = ",".join(c.name for c in o.users_collection)
        print(f"{o.name!r:60} verts={len(o.data.vertices):6} hidden={o.hide_get() if o.name in bpy.context.view_layer.objects else 'n/a'} [{cols}]")
