"""
Converte Simepar_CM.e57 (nuvem de pontos REAL do site) -> GLB web-ready.

Pipeline:
1. pye57 carrega o E57 (1.2 GB)
2. Subsample para alvo ~5M pontos
3. Detecta centroide + bounds para georreferenciar
4. Rotacao Z-up -> Y-up
5. Centralizar XY na area da torre (ponto mais alto)
6. Exportar GLB point cloud + JSON com offset UTM
"""
import os
import sys
import numpy as np
import pye57
import trimesh
from trimesh.transformations import rotation_matrix

E57_PATH = r"C:\Users\23GAMER\Downloads\Simepar_CM.e57"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "simepar")
os.makedirs(OUT_DIR, exist_ok=True)

# Alvo: ~5 milhoes de pontos (fica ~50-100 MB de GLB)
TARGET_POINTS = 5_000_000

print(f"[1/6] Abrindo E57: {E57_PATH}")
print(f"      Tamanho: {os.path.getsize(E57_PATH)/1024/1024/1024:.2f} GB")
e57 = pye57.E57(E57_PATH)
scan_count = e57.scan_count
print(f"      Scans: {scan_count}")

# E57 pode ter multiplos scans - vamos ler o primeiro (ou combinar)
header = e57.get_header(0)
print(f"      Pontos no scan 0: {header.point_count:,}")
print(f"      Has colors: {'colorRed' in header.point_fields}")

print("[2/6] Carregando todos os pontos (pode levar 1-2 min)...")
data = e57.read_scan(0, ignore_missing_fields=True, intensity=False, colors=True, transform=True)

# data['cartesianX/Y/Z'] e data['colorRed/Green/Blue']
x = data['cartesianX']
y = data['cartesianY']
z = data['cartesianZ']
n = len(x)
print(f"      {n:,} pontos lidos")

# Subsample
if n > TARGET_POINTS:
    ratio = TARGET_POINTS / n
    print(f"[3/6] Subsampling: {n:,} -> ~{TARGET_POINTS:,} ({ratio:.4f})")
    idx = np.random.choice(n, TARGET_POINTS, replace=False)
    x = x[idx]
    y = y[idx]
    z = z[idx]
    if 'colorRed' in data:
        r = data['colorRed'][idx]
        g = data['colorGreen'][idx]
        b = data['colorBlue'][idx]
    else:
        r = g = b = None
else:
    if 'colorRed' in data:
        r = data['colorRed']
        g = data['colorGreen']
        b = data['colorBlue']
    else:
        r = g = b = None

pts = np.column_stack([x, y, z]).astype(np.float32)
print(f"[4/6] Bounds originais:")
print(f"      X: [{pts[:,0].min():.2f}, {pts[:,0].max():.2f}]  ({pts[:,0].max()-pts[:,0].min():.2f}m)")
print(f"      Y: [{pts[:,1].min():.2f}, {pts[:,1].max():.2f}]  ({pts[:,1].max()-pts[:,1].min():.2f}m)")
print(f"      Z: [{pts[:,2].min():.2f}, {pts[:,2].max():.2f}]  ({pts[:,2].max()-pts[:,2].min():.2f}m)")

# Centralizar XY no centroide, base no Z=0
centroid_x = (pts[:,0].min() + pts[:,0].max()) / 2
centroid_y = (pts[:,1].min() + pts[:,1].max()) / 2
min_z = pts[:, 2].min()

# Salvar offset (georreferenciar de volta no MDT depois)
offset = {
    "easting": float(centroid_x),
    "northing": float(centroid_y),
    "elevation_base": float(min_z),
    "crs_hint": "presumido UTM (E57 native coords)",
    "bounds_original": {
        "x_min": float(pts[:,0].min()), "x_max": float(pts[:,0].max()),
        "y_min": float(pts[:,1].min()), "y_max": float(pts[:,1].max()),
        "z_min": float(pts[:,2].min()), "z_max": float(pts[:,2].max()),
    },
    "point_count": int(len(pts)),
}

pts[:, 0] -= centroid_x
pts[:, 1] -= centroid_y
pts[:, 2] -= min_z

# Rotacao Z-up -> Y-up (GLTF spec)
# Em vez de transformar matriz, troca colunas: (x, y, z) -> (x, z, -y)
pts_yup = np.column_stack([pts[:,0], pts[:,2], -pts[:,1]]).astype(np.float32)

print(f"[5/6] Y-up bounds (centralizado):")
print(f"      X: [{pts_yup[:,0].min():.2f}, {pts_yup[:,0].max():.2f}]")
print(f"      Y: [{pts_yup[:,1].min():.2f}, {pts_yup[:,1].max():.2f}]  (altura)")
print(f"      Z: [{pts_yup[:,2].min():.2f}, {pts_yup[:,2].max():.2f}]")

# Cores
if r is not None:
    # E57 colors podem vir como int 0-255 ou float 0-1
    if r.dtype == np.float32 or r.dtype == np.float64:
        if r.max() <= 1.0:
            r = (r * 255).astype(np.uint8)
            g = (g * 255).astype(np.uint8)
            b = (b * 255).astype(np.uint8)
        else:
            r = r.astype(np.uint8)
            g = g.astype(np.uint8)
            b = b.astype(np.uint8)
    else:
        r = r.astype(np.uint8)
        g = g.astype(np.uint8)
        b = b.astype(np.uint8)
    colors_rgba = np.column_stack([r, g, b, np.full_like(r, 255)])
else:
    # Cor padrao verde-marrom
    colors_rgba = np.column_stack([
        np.full(len(pts_yup), 110, dtype=np.uint8),
        np.full(len(pts_yup), 130, dtype=np.uint8),
        np.full(len(pts_yup),  90, dtype=np.uint8),
        np.full(len(pts_yup), 255, dtype=np.uint8),
    ])

print(f"[6/6] Exportando GLB...")
cloud = trimesh.PointCloud(vertices=pts_yup, colors=colors_rgba)
out_glb = os.path.join(OUT_DIR, "simepar_site.glb")
cloud.export(out_glb)
print(f"      OK gravado: {out_glb}")
print(f"      Tamanho: {os.path.getsize(out_glb)/1024/1024:.1f} MB")

# Salvar offset JSON
import json
offset_path = os.path.join(OUT_DIR, "simepar_site_offset.json")
with open(offset_path, "w") as f:
    json.dump(offset, f, indent=2)
print(f"      Offset georeferencia: {offset_path}")
print(f"      Centroide UTM: E={offset['easting']:.2f}  N={offset['northing']:.2f}  h={offset['elevation_base']:.2f}")
print("DONE")
