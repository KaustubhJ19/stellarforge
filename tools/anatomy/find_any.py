"""Print any object (any type) whose name matches keywords.
Run: Blender -b <file.blend> --python find_any.py -- kw1 kw2 ...
"""
import sys, bpy
kws = [k.lower() for k in sys.argv[sys.argv.index("--") + 1:]]
for o in bpy.data.objects:
    n = o.name.lower()
    if any(k in n for k in kws) and not n.endswith((".j", ".i", ".t")) and ".j." not in n:
        size = len(o.data.vertices) if o.type == "MESH" else (sum(len(s.points)+len(s.bezier_points) for s in o.data.splines) if o.type == "CURVE" else 0)
        print(f"{o.name!r:55} {o.type:6} size={size:6} [{','.join(c.name for c in o.users_collection)[:90]}]")
