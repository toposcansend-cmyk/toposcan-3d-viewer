"""
Conversao Z-up -> Y-up para GLBs do projeto.
GLTF 2.0 spec exige Y-up. model-viewer interpreta tudo como Y-up.
Modelos Z-up (CAD/Blender) precisam ser rotacionados -90 em X.
"""
import os
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "models")

# Rotacao -90 em X transforma Z-up para Y-up
R = rotation_matrix(-np.pi/2, [1, 0, 0])

files = [
    os.path.join(MODELS, "torre_radar_v3.glb"),
    os.path.join(MODELS, "demo", "cena_torre_terreno.glb"),
]

for path in files:
    if not os.path.exists(path):
        print(f"  PULAR (nao existe): {path}")
        continue

    print(f"Processando: {path}")
    scene = trimesh.load(path, force="scene")
    b0 = scene.bounds
    print(f"  ANTES bounds: X={b0[1][0]-b0[0][0]:.2f} Y={b0[1][1]-b0[0][1]:.2f} Z={b0[1][2]-b0[0][2]:.2f}")

    # Aplicar rotacao em todos os meshes da cena
    new_scene = trimesh.Scene()
    for node_name, mesh in scene.geometry.items():
        m = mesh.copy()
        m.apply_transform(R)
        # Preservar cores
        if hasattr(mesh.visual, 'face_colors'):
            m.visual.face_colors = mesh.visual.face_colors
        new_scene.add_geometry(m, geom_name=node_name, node_name=node_name)

    b1 = new_scene.bounds
    print(f"  DEPOIS bounds: X={b1[1][0]-b1[0][0]:.2f} Y={b1[1][1]-b1[0][1]:.2f} Z={b1[1][2]-b1[0][2]:.2f}")
    print(f"  (esperado: Y agora deve ser a maior dimensao = altura)")

    # Exportar de volta no mesmo lugar
    new_scene.export(path)
    print(f"  OK gravado")

# Tambem regenerar OBJ/PLY/STL com Y-up
print("\n--- Regenerando OBJ/PLY/STL (Y-up) ---")
scene = trimesh.load(os.path.join(MODELS, "torre_radar_v3.glb"), force="scene")
combined = trimesh.util.concatenate(list(scene.geometry.values()))

scene.export(os.path.join(MODELS, "torre_radar_v3.obj"))
combined.export(os.path.join(MODELS, "torre_radar_v3.ply"))
combined.export(os.path.join(MODELS, "torre_radar_v3.stl"))
print("  OBJ/PLY/STL exportados (Y-up)")

print("\nDONE")
