"""
SIMEPAR v2 — Mesh reconstruction OTIMIZADA + posicao correta + densidade alta.

Mudancas vs v1:
- 8M pontos (era 15M, evita OOM)
- Poisson depth=9 (era 10, 5x mais rapido)
- orient_normals SKIP do consistent_tangent_plane (era O(N²) - travava)
- Detecta radome existente (esfera branca + alta) e posiciona torre la
"""
import os, sys, json
import numpy as np
import pye57
import trimesh
import open3d as o3d

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E57 = r"C:\Users\23GAMER\Downloads\Simepar_CM.e57"
OUT_DIR = os.path.join(ROOT, "models", "simepar")
TORRE_GLB = os.path.join(ROOT, "models", "torre_radar_v3.glb")
os.makedirs(OUT_DIR, exist_ok=True)

TARGET_POINTS = 8_000_000
POISSON_DEPTH = 9
TARGET_FACES = 1_200_000

# ============================================================================
print(f"[1/7] E57 ({os.path.getsize(E57)/1024**3:.2f} GB)")
e57 = pye57.E57(E57)
data = e57.read_scan(0, ignore_missing_fields=True, intensity=False, colors=True, transform=True)
x = data['cartesianX']; y = data['cartesianY']; z = data['cartesianZ']
r = data['colorRed']; g = data['colorGreen']; b = data['colorBlue']
n = len(x)
print(f"      {n:,} pontos | colors: R{r.dtype}")

if n > TARGET_POINTS:
    np.random.seed(42)
    idx = np.random.choice(n, TARGET_POINTS, replace=False)
    x = x[idx]; y = y[idx]; z = z[idx]
    r = r[idx]; g = g[idx]; b = b[idx]
print(f"      subsample -> {len(x):,}")

if r.dtype != np.uint8:
    if r.max() <= 1.0:
        r = (r * 255).astype(np.uint8); g = (g * 255).astype(np.uint8); b = (b * 255).astype(np.uint8)
    else:
        r = r.astype(np.uint8); g = g.astype(np.uint8); b = b.astype(np.uint8)

pts_utm = np.column_stack([x, y, z]).astype(np.float64)
xmin, ymin, zmin = pts_utm.min(0); xmax, ymax, zmax = pts_utm.max(0)
print(f"      UTM: X{xmax-xmin:.0f}m Y{ymax-ymin:.0f}m Z{zmax-zmin:.0f}m")

# ============================================================================
print("[2/7] Detectando radome existente (cluster branco no topo)...")
bright = (r > 200) & (g > 200) & (b > 200)
high = z > np.percentile(z, 85)
cand_mask = bright & high
nc = cand_mask.sum()
if nc > 500:
    cand = pts_utm[cand_mask]
    radome_utm = cand.mean(axis=0)
    print(f"      {nc:,} candidatos -> centroide UTM ({radome_utm[0]:.1f}, {radome_utm[1]:.1f}, {radome_utm[2]:.1f})")
else:
    radome_utm = pts_utm[np.argmax(z)]
    print(f"      Fallback ponto mais alto: {radome_utm}")

tower_pos = {
    "easting": float(radome_utm[0]),
    "northing": float(radome_utm[1]),
    "elevation_radome_center": float(radome_utm[2]),
    "candidates_count": int(nc),
}
with open(os.path.join(OUT_DIR, "tower_position.json"), "w") as f:
    json.dump(tower_pos, f, indent=2)

# ============================================================================
print("[3/7] Centralizando + Y-up...")
cx = (xmin + xmax) / 2
cy = (ymin + ymax) / 2
cz_base = zmin
pts_local = pts_utm.copy()
pts_local[:, 0] -= cx
pts_local[:, 1] -= cy
pts_local[:, 2] -= cz_base
# Z-up -> Y-up: (x, y, z) -> (x, z, -y)
pts_yup = np.column_stack([pts_local[:, 0], pts_local[:, 2], -pts_local[:, 1]]).astype(np.float32)

# Radome em coords locais Y-up
rad_yup = np.array([
    radome_utm[0] - cx,
    radome_utm[2] - cz_base,   # Y = altura (Z UTM)
    -(radome_utm[1] - cy),     # Z = -Y_UTM
])
print(f"      Radome local Y-up: ({rad_yup[0]:.2f}, {rad_yup[1]:.2f}, {rad_yup[2]:.2f})")

# ============================================================================
print(f"[4/7] Open3D PointCloud + estimate_normals (sem orient_consistent)...")
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(pts_yup.astype(np.float64))
colors_rgb = np.column_stack([r, g, b]).astype(np.float64) / 255.0
pcd.colors = o3d.utility.Vector3dVector(colors_rgb)
pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=1.5, max_nn=20))
# Camera_location oriente as normais p/ baixo (sem O(N²))
pcd.orient_normals_towards_camera_location(camera_location=[0, 200, 0])
print(f"      Normais OK")

# ============================================================================
print(f"[5/7] Poisson reconstruction (depth={POISSON_DEPTH})...")
mesh_o3d, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd, depth=POISSON_DEPTH, scale=1.1, linear_fit=False
)
print(f"      Bruto: {len(mesh_o3d.vertices):,} v / {len(mesh_o3d.triangles):,} f")

# Limpar artefatos baixa densidade
print("      Limpando artefatos (densidade < q05)...")
dens = np.asarray(densities)
mesh_o3d.remove_vertices_by_mask(dens < np.quantile(dens, 0.05))
print(f"      Apos: {len(mesh_o3d.vertices):,} v / {len(mesh_o3d.triangles):,} f")

if len(mesh_o3d.triangles) > TARGET_FACES:
    print(f"      Decimando -> {TARGET_FACES:,}...")
    mesh_o3d = mesh_o3d.simplify_quadric_decimation(target_number_of_triangles=TARGET_FACES)
    print(f"      Apos: {len(mesh_o3d.vertices):,} v / {len(mesh_o3d.triangles):,} f")

mesh_o3d.compute_vertex_normals()

# ============================================================================
print("[6/7] Exportando mesh GLB...")
verts = np.asarray(mesh_o3d.vertices, dtype=np.float32)
faces = np.asarray(mesh_o3d.triangles, dtype=np.uint32)
vcols = (np.asarray(mesh_o3d.vertex_colors) * 255).astype(np.uint8)
vcols_rgba = np.column_stack([vcols, np.full(len(vcols), 255, dtype=np.uint8)])

tm = trimesh.Trimesh(vertices=verts, faces=faces, vertex_colors=vcols_rgba, process=False)
mesh_out = os.path.join(OUT_DIR, "simepar_site_mesh.glb")
tm.export(mesh_out)
print(f"      OK {mesh_out}  ({os.path.getsize(mesh_out)/1024**2:.1f} MB)")

# ============================================================================
print("[7/7] Combinando com torre + posicionamento INTELIGENTE...")
torre_scene = trimesh.load(TORRE_GLB, force='scene')
out_scene = trimesh.Scene()
out_scene.add_geometry(tm, geom_name="simepar_terrain_mesh", node_name="simepar_terrain_mesh")

# OFFSET p/ posicao livre: 25m a OESTE do radome existente (em direcao -X local)
# Conforme CAD aerial do projeto SIMEPAR, novo radar fica a oeste do existente
TOWER_OFFSET_FROM_RADOME_X = -25.0   # 25m oeste
TOWER_OFFSET_FROM_RADOME_Z = 0.0     # mesma latitude

tower_target_x = rad_yup[0] + TOWER_OFFSET_FROM_RADOME_X
tower_target_z = rad_yup[2] + TOWER_OFFSET_FROM_RADOME_Z

# AMOSTRAR a altura do mesh no (target_x, target_z) p/ fundacao no nivel certo
print(f"      Amostrando altura do mesh em XZ=({tower_target_x:.1f}, {tower_target_z:.1f})...")
mesh_verts = np.asarray(mesh_o3d.vertices)
# Pegar vertices proximos do target XZ
xz_dist = np.sqrt((mesh_verts[:, 0] - tower_target_x)**2 + (mesh_verts[:, 2] - tower_target_z)**2)
near_idx = np.argsort(xz_dist)[:200]  # 200 mais proximos
local_terrain_y = mesh_verts[near_idx, 1].mean()
print(f"      Altura mesh local: Y={local_terrain_y:.2f}m")

# Torre offset = (target_x, terrain_y, target_z) — base da torre cai no nivel do terreno
offset = (tower_target_x, local_terrain_y - 0.5, tower_target_z)  # -0.5 evita levitar
print(f"      Torre offset final: ({offset[0]:.2f}, {offset[1]:.2f}, {offset[2]:.2f})")

# SUPRIMIR componentes redundantes (edif terrea + carro + mureta + gradil + fossa
# JA estao no mesh fotogrametrico real do terreno)
SUPPRESS_KEYWORDS = ['edif_', 'carro_', 'mureta', 'gradil', 'fossa', 'sumidouro']
for node, m in torre_scene.geometry.items():
    if any(k in node for k in SUPPRESS_KEYWORDS):
        continue  # nao adicionar - ja existe no mesh real
    mc = m.copy()
    mc.apply_translation(offset)
    out_scene.add_geometry(mc, geom_name=node, node_name=node)
print(f"      Componentes mantidos da torre: foundacao + torre + escadas + plataforma + radome + refletores")

combo_out = os.path.join(OUT_DIR, "simepar_torre_real.glb")
out_scene.export(combo_out)
print(f"      OK {combo_out}  ({os.path.getsize(combo_out)/1024**2:.1f} MB)")

print(f"\nVerificacoes:")
print(f"  Mesh terrain: {verts[:,0].max()-verts[:,0].min():.0f}m x {verts[:,2].max()-verts[:,2].min():.0f}m")
print(f"  Altura mesh:  {verts[:,1].max()-verts[:,1].min():.0f}m")
print(f"  Torre h:      ~29m (22m plat + 7m radome)")
print(f"  Torre cabe ~{(verts[:,0].max()-verts[:,0].min())/27:.0f}x no terreno em X")
print("DONE")
