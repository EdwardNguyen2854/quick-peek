"""
Optional FreeCAD conversion helper.
Usage idea:
  FreeCADCmd tools/freecad_step_to_glb.py input.step output.glb

FreeCAD export support depends on your FreeCAD build. This helper must produce GLB
because Quick Peek renders tessellated STEP geometry from GLB in the browser.
"""
import sys
import FreeCAD
import Import
import Mesh

if len(sys.argv) < 3:
    raise SystemExit("Usage: FreeCADCmd freecad_step_to_glb.py input.step output.glb")

inp, out = sys.argv[-2], sys.argv[-1]
doc = FreeCAD.newDocument("quick_peek_preview")
Import.insert(inp, doc.Name)
doc.recompute()
objects = [obj for obj in doc.Objects if hasattr(obj, "Shape")]
if not objects:
    raise SystemExit("No shape objects found")
# FreeCAD's exporter availability varies by version/build.
Mesh.export(objects, out)
print(f"Exported {out}")
