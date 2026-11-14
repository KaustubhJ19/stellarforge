# Body model export (Spike B)

Builds `frontend/public/models/body-male.glb` from Z-Anatomy with Blender.

## Rebuild

1. Download `Z-Anatomy.zip` from https://github.com/Z-Anatomy/Models-of-human-anatomy and unzip
   `Z-Anatomy/Startup.blend` into `data/z-anatomy/` (gitignored, about 300 MB).
2. Run, from the repo root (Blender 5.2 LTS):

   ```
   Blender -b data/z-anatomy/Z-Anatomy/Startup.blend \
       --python tools/anatomy/export_body.py -- frontend/public/models/body-male.glb
   ```

   It takes about 45 s. Helper scripts `inspect_blend.py`, `find_structures.py`,
   `find_collections.py` and `find_any.py` list what is inside the .blend.

## What is in the file

- **17 structure nodes**, one per entry in the Indicator-to-structure map, named by a
  stable id (`heart`, `brain.amygdala`, `bone.hip`, …). Each carries glTF extras
  `kind: "structure"` and `layer: <layer>`. The web app finds them by name.
- **5 outline nodes**, `outline.<layer>`, for muscles, skeleton, vessels, organs and brain:
  everything else in that layer merged and decimated to a triangle budget.
- No materials; the web app colours each layer from its theme tokens.
- Draco-compressed. The decoder is vendored in `frontend/public/draco/` so it works offline.

Mapping notes:

- Z-Anatomy has no separate suprachiasmatic nucleus, so "Sleep / body clock" lights
  `brain.hypothalamus`, which contains it.
- "Eyes (SANS)" lights `eye.optic`: optic nerves plus retinas (no separate optic disc mesh).
- Z-Anatomy has no fat tissue mesh, so glucose lights `liver` and `muscle.thigh` only.
- Vessels and nerves are bevelled curves in Z-Anatomy; the exporter bakes them to meshes.

## Spike B result (14 Nov 2026): GO

| Check | Result |
|---|---|
| Mapped structures exported and findable by name | 17/17 |
| File size | 1.1 MB (about 420k triangles) |
| Load + Draco decode in Chromium | 45–85 ms (local file) |
| Frame rate, laptop GPU (Apple Silicon, Metal) | 60 fps, whole body rotating |
| Frame rate, software rendering (no GPU) | 10 fps |

No fallback needed. Female layers not yet tried (ticket 18, P1).
Re-run the check: start `npm run dev` in `frontend/`, then `node spike/run-spike.mjs http://localhost:5173`.

## Licence

Derived from Z-Anatomy (CC BY-SA 4.0), which derives from BodyParts3D (CC BY 4.0,
Database Center for Life Science). `body-male.glb` is released under **CC BY-SA 4.0**.
Credits page: Z-Anatomy, BodyParts3D.
