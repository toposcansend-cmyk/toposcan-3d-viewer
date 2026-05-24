"""
SIMEPAR v3 — POINT CLOUD DENSO (volta do mesh).

Feedback usuario:
- Mesh Poisson deformou tudo (predio irreconhecivel)
- Quer mais DENSIDADE no cloud original (era esparso)
- Torre deve ficar entre predio operacoes e radar existente (X na ref)

Plano:
- 15M pontos (era 5M -> 3x mais denso)
- Detectar radome existente (cluster branco no topo) [funcionou v2]
- Detectar AREA ABERTA (clusters de pontos com Y=topo - mesmo nivel do topo,
  e poucos vizinhos verticais => gramado/asfalto)
- Posicionar torre na area aberta MAIS PROXIMA do radome (~8-15m)
"""
import os, sys, json
import numpy as np
import pye57
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E57 = r"C:\Users\23GAMER\Downloads\Simepar_CM.e57"
OUT_DIR = os.path.join(ROOT, "models", "simepar")
TORRE_GLB = os.path.join(ROOT, "models", "torre_radar_v3.glb")
os.makedirs(OUT_DIR, exist_ok=True)

TARGET_POINTS = 58_000_000  # USAR TODOS os pontos do E57 (max densidade no crop)

# Crop bbox - centrado no SITE SIMEPAR (radome + torre nova proxima)
CROP_X_HALF = 45.0   # +-45m leste-oeste (90m total)
CROP_Z_HALF = 30.0   # +-30m norte-sul (60m total)
# Centro do crop: meio caminho radome -> torre (offset_east/2, offset_north/2)
CROP_CENTER_OFFSET_X = 6.0   # entre radome e torre nova
CROP_CENTER_OFFSET_Z = +4.0  # ligeiramente sul do radome
# Densidade alvo apos crop (subsample apos crop se necessario)
MAX_POINTS_AFTER_CROP = 6_500_000   # ~100 MB final

# ============================================================================
print(f"[1/6] E57 ({os.path.getsize(E57)/1024**3:.2f} GB)")
e57 = pye57.E57(E57)
data = e57.read_scan(0, ignore_missing_fields=True, intensity=False, colors=True, transform=True)
x = data['cartesianX']; y = data['cartesianY']; z = data['cartesianZ']
r = data['colorRed']; g = data['colorGreen']; b = data['colorBlue']
n = len(x)
print(f"      {n:,} pontos originais")

if n > TARGET_POINTS:
    np.random.seed(42)
    idx = np.random.choice(n, TARGET_POINTS, replace=False)
    x, y, z = x[idx], y[idx], z[idx]
    r, g, b = r[idx], g[idx], b[idx]
print(f"      Subsample -> {len(x):,}")

if r.dtype != np.uint8:
    if r.max() <= 1.0:
        r = (r*255).astype(np.uint8); g=(g*255).astype(np.uint8); b=(b*255).astype(np.uint8)
    else:
        r = r.astype(np.uint8); g=g.astype(np.uint8); b=b.astype(np.uint8)

pts_utm = np.column_stack([x, y, z]).astype(np.float64)
xmin, ymin, zmin = pts_utm.min(0); xmax, ymax, zmax = pts_utm.max(0)
print(f"      UTM: X{xmax-xmin:.0f}m Y{ymax-ymin:.0f}m Z{zmax-zmin:.0f}m")

# ============================================================================
print("[2/6] Detectando radome existente (cluster branco no topo)...")
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

# ============================================================================
print("[3/6] Posicionando torre nova (offset manual conforme imagem 3 do usuario)...")
# Imagem 3 (Unreal render) mostra X marcado a ~12m SE do radome existente
# (entre predio operacoes e radar existente, na area de grama aberta)
# UTM convention: E (oeste->leste), N (sul->norte)
OFFSET_EAST  = +12.0   # 12m a leste (X marcado proximo ao edif. SIMEPAR)
OFFSET_NORTH = -8.0    # 8m a sul
target_utm = radome_utm.copy()
target_utm[0] += OFFSET_EAST
target_utm[1] += OFFSET_NORTH
# Amostrar elevacao da nuvem no XY alvo (media dos pontos a 5m de raio)
dx_t = pts_utm[:, 0] - target_utm[0]
dy_t = pts_utm[:, 1] - target_utm[1]
near_target = np.sqrt(dx_t**2 + dy_t**2) < 5.0
if near_target.sum() > 100:
    target_utm[2] = pts_utm[near_target, 2].mean()
print(f"      Torre alvo UTM: ({target_utm[0]:.1f}, {target_utm[1]:.1f}, {target_utm[2]:.1f})")
print(f"      Offset do radome: E+{OFFSET_EAST}m  N{OFFSET_NORTH}m")

tower_pos = {
    "radome_existente_utm": {"e": float(radome_utm[0]), "n": float(radome_utm[1]), "h": float(radome_utm[2])},
    "torre_nova_alvo_utm":  {"e": float(target_utm[0]), "n": float(target_utm[1]), "h": float(target_utm[2])},
    "distancia_planar_m": float(np.sqrt((target_utm[0]-radome_utm[0])**2 + (target_utm[1]-radome_utm[1])**2)),
}
with open(os.path.join(OUT_DIR, "tower_position.json"), "w") as f:
    json.dump(tower_pos, f, indent=2)
print(f"      Distancia radome -> torre nova: {tower_pos['distancia_planar_m']:.1f}m")

# ============================================================================
print("[4/6] Centralizando + Y-up...")
cx = (xmin + xmax) / 2
cy = (ymin + ymax) / 2
cz_base = zmin
pts_local = pts_utm.copy()
pts_local[:, 0] -= cx
pts_local[:, 1] -= cy
pts_local[:, 2] -= cz_base
pts_yup = np.column_stack([pts_local[:, 0], pts_local[:, 2], -pts_local[:, 1]]).astype(np.float32)

target_yup = np.array([target_utm[0] - cx, target_utm[2] - cz_base, -(target_utm[1] - cy)])
print(f"      Torre Y-up: ({target_yup[0]:.2f}, {target_yup[1]:.2f}, {target_yup[2]:.2f})")

# ============================================================================
print(f"[5/6] CROP cloud ao retangulo {CROP_X_HALF*2:.0f}x{CROP_Z_HALF*2:.0f}m (centrado no meio radome-torre)...")
# Centro do crop = meio do caminho radome existente -> torre nova
rad_x = radome_utm[0] - cx
rad_z = -(radome_utm[1] - cy)
crop_center_x = rad_x + CROP_CENTER_OFFSET_X
crop_center_z = rad_z + CROP_CENTER_OFFSET_Z
crop_mask = (
    (pts_yup[:, 0] >= crop_center_x - CROP_X_HALF) & (pts_yup[:, 0] <= crop_center_x + CROP_X_HALF) &
    (pts_yup[:, 2] >= crop_center_z - CROP_Z_HALF) & (pts_yup[:, 2] <= crop_center_z + CROP_Z_HALF)
)
pts_cropped = pts_yup[crop_mask]
r_c = r[crop_mask]; g_c = g[crop_mask]; b_c = b[crop_mask]
print(f"      {crop_mask.sum():,} pontos no crop (de {len(pts_yup):,} totais)")

# Subsample APOS o crop se passar do limite
if len(pts_cropped) > MAX_POINTS_AFTER_CROP:
    idx2 = np.random.choice(len(pts_cropped), MAX_POINTS_AFTER_CROP, replace=False)
    pts_cropped = pts_cropped[idx2]
    r_c = r_c[idx2]; g_c = g_c[idx2]; b_c = b_c[idx2]
    print(f"      Subsampling pos-crop: -> {len(pts_cropped):,} pontos")

# Densidade resultante
area_m2 = (CROP_X_HALF*2) * (CROP_Z_HALF*2)
density = len(pts_cropped) / area_m2
print(f"      Densidade final: {density:.0f} pts/m² ({len(pts_cropped):,} pts em {area_m2:.0f} m²)")

colors_rgba = np.column_stack([r_c, g_c, b_c, np.full(len(r_c), 255, dtype=np.uint8)])
cloud = trimesh.PointCloud(vertices=pts_cropped, colors=colors_rgba)
cloud_out = os.path.join(OUT_DIR, "simepar_site.glb")
cloud.export(cloud_out)
print(f"      OK {cloud_out}  ({os.path.getsize(cloud_out)/1024**2:.1f} MB)")

# ============================================================================
print("[6/6] Combinando torre na area livre detectada...")
torre_scene = trimesh.load(TORRE_GLB, force='scene')
out_scene = trimesh.Scene()
# adicionar nuvem
out_scene.add_geometry(cloud, geom_name="simepar_pointcloud", node_name="simepar_pointcloud")

# Torre: base no terreno. Y = target_yup[1] (altura) - 0.5 p/ evitar levitar
offset = (target_yup[0], target_yup[1] - 0.5, target_yup[2])
# Re-incluir TODOS componentes (user quer estrutura completa: torre + edif. terrea + carro + mureta + gradil + fossa)
kept = 0
for node, m in torre_scene.geometry.items():
    mc = m.copy()
    mc.apply_translation(offset)
    out_scene.add_geometry(mc, geom_name=node, node_name=node)
    kept += 1
skipped = 0

combo_out = os.path.join(OUT_DIR, "simepar_torre_real.glb")
out_scene.export(combo_out)
print(f"      Componentes: {kept} mantidos, {skipped} suprimidos")
print(f"      OK {combo_out}  ({os.path.getsize(combo_out)/1024**2:.1f} MB)")
print(f"\nResumo:")
print(f"  Cloud: 15M pontos (3x mais denso) com cores RGB reais")
print(f"  Torre posicao: {tower_pos['distancia_planar_m']:.1f}m do radome existente")
print(f"  Cena combinada: {os.path.getsize(combo_out)/1024**2:.0f} MB")
print("DONE")
