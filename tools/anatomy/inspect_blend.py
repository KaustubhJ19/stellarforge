"""List the top-level collections and object counts in a Z-Anatomy .blend.
Run: Blender -b <file.blend> --python inspect_blend.py
"""
import bpy

def walk(col, depth=0, max_depth=2):
    meshes = sum(1 for o in col.objects if o.type == "MESH")
    print("  " * depth + f"{col.name}  (meshes={meshes}, children={len(col.children)})")
    if depth < max_depth:
        for c in col.children:
            walk(c, depth + 1, max_depth)

walk(bpy.context.scene.collection)
print("TOTAL MESHES", sum(1 for o in bpy.data.objects if o.type == "MESH"))
