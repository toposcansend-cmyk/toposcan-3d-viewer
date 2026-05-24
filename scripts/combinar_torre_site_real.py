"""
Combina a torre 3D + nuvem real do site SIMEPAR em uma unica cena GLB.

Algoritmo de posicionamento da torre:
1. Carrega point cloud (Y-up centralizado, Y = altura)
2. Detecta o ponto mais alto perto do centro (X≈0, Z≈0)
3. Translada a torre 3D para esse (x, y, z)
"""
import os
import numpy as np
import trimesh
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOUD = os.path.join(ROOT, "models", "simepar", "simepar_site.glb")
TORRE = os.path.join(ROOT, "models", "torre_radar_v3.glb")
OUT = os.path.join(ROOT, "models", "simepar", "simepar_torre_real.glb")

print(f"[1/4] Carregando point cloud: {os.path.basename(CLOUD)}")
cloud_scene = trimesh.load(CLOUD, force='scene')
# Pode ser PointCloud ou Scene
if hasattr(cloud_scene, 'geometry'):
    cloud_obj = list(cloud_scene.geometry.values())[0]
else:
    cloud_obj = cloud_scene
cloud_verts = np.asarray(cloud_obj.vertices)
cloud_colors = cloud_obj.colors if hasattr(cloud_obj, 'colors') else None
print(f"      {len(cloud_verts):,} pontos · cores: {cloud_colors is not None}")

print(f"[2/4] Detectando ponto mais alto perto do centro (raio 20m)...")
# Filtra pontos dentro de raio 20m do centro XZ
xz_dist = np.sqrt(cloud_verts[:, 0]**2 + cloud_verts[:, 2]**2)
mask = xz_dist < 20.0
if mask.sum() > 0:
    near_center = cloud_verts[mask]
    # Ponto mais alto = maior Y
    high_idx_local = np.argmax(near_center[:, 1])
    high_pt = near_center[high_idx_local]
else:
    # fallback: ponto mais alto da nuvem inteira
    high_pt = cloud_verts[np.argmax(cloud_verts[:, 1])]
print(f"      Ponto torre (Y-up): X={high_pt[0]:.2f} Y={high_pt[1]:.2f} Z={high_pt[2]:.2f}")

print(f"[3/4] Carregando torre: {os.path.basename(TORRE)}")
torre_scene = trimesh.load(TORRE, force='scene')
print(f"      {len(torre_scene.geometry)} geometrias")

# Composicao final
out_scene = trimesh.Scene()

# Adicionar nuvem
out_scene.add_geometry(cloud_obj, geom_name="simepar_pointcloud", node_name="simepar_pointcloud")

# Adicionar torre transladada (origem da torre = (0,0,0), base no Y=0)
# Trasladar para o ponto detectado
offset = (high_pt[0], high_pt[1], high_pt[2])
for node, m in torre_scene.geometry.items():
    mc = m.copy()
    mc.apply_translation(offset)
    out_scene.add_geometry(mc, geom_name=node, node_name=node)

print(f"[4/4] Exportando cena combinada...")
out_scene.export(OUT)
print(f"      OK: {OUT}")
print(f"      Tamanho: {os.path.getsize(OUT)/1024/1024:.1f} MB")
print("DONE")
