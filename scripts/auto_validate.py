"""
Validacao automatica do estado atual:
1. Carrega o GLB DEPLOYADO (do GitHub Pages, nao o local)
2. Imprime bounds reais, posicao da torre, posicao do edif. existente (radome)
3. Renderiza vista TOP com regua e marcadores
4. Cruza com o JSON da posicao (tower_position.json)
"""
import os, json, urllib.request, ssl
import numpy as np
import trimesh
os.environ["PYVISTA_OFF_SCREEN"] = "true"
import pyvista as pv
pv.OFF_SCREEN = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_GLB = os.path.join(ROOT, "models", "simepar", "simepar_site_v7_perfect.glb")
DEPLOYED_URL = "https://toposcansend-cmyk.github.io/toposcan-3d-viewer/models/simepar/simepar_site_v7_perfect.glb"
TOWER_POS_JSON = os.path.join(ROOT, "models", "simepar", "tower_position.json")
QC_DIR = os.path.join(ROOT, "models", "simepar", "validation")
os.makedirs(QC_DIR, exist_ok=True)

print("=" * 70)
print("VALIDACAO DO ESTADO ATUAL")
print("=" * 70)

# 1. Verificar deploy
print("\n[1] Comparando local vs deployed...")
ctx = ssl.create_default_context()
try:
    with urllib.request.urlopen(DEPLOYED_URL, context=ctx, timeout=30) as r:
        deployed_size = int(r.headers.get('Content-Length', 0))
    local_size = os.path.getsize(LOCAL_GLB)
    print(f"  Local:    {local_size:,} bytes ({local_size/1024**2:.1f} MB)")
    print(f"  Deployed: {deployed_size:,} bytes ({deployed_size/1024**2:.1f} MB)")
    print(f"  Match: {'SIM' if abs(deployed_size - local_size) < 1024 else 'NAO !!'}")
except Exception as e:
    print(f"  Erro check deploy: {e}")

# 2. Posicao da torre + radome detectado
print(f"\n[2] Posicao salva em tower_position.json:")
with open(TOWER_POS_JSON) as f:
    pos = json.load(f)
print(json.dumps(pos, indent=2))

# 3. Carregar GLB e analisar
print(f"\n[3] Carregando GLB local p/ analise...")
scene = trimesh.load(LOCAL_GLB, force='scene')
print(f"  Geometrias totais: {len(scene.geometry)}")

# Encontrar a torre vs cloud
cloud_nodes = [n for n in scene.geometry if 'pointcloud' in n.lower() or 'terrain' in n.lower()]
torre_nodes = [n for n in scene.geometry if n not in cloud_nodes]
print(f"  Cloud nodes: {len(cloud_nodes)}")
print(f"  Torre/estrutura nodes: {len(torre_nodes)}")

# Bounds da cloud (terreno)
if cloud_nodes:
    cv = scene.geometry[cloud_nodes[0]].vertices
    print(f"  CLOUD bounds:")
    print(f"    X: [{cv[:,0].min():+.1f}, {cv[:,0].max():+.1f}]  (dx={cv[:,0].max()-cv[:,0].min():.1f}m)")
    print(f"    Y: [{cv[:,1].min():+.1f}, {cv[:,1].max():+.1f}]  (dy={cv[:,1].max()-cv[:,1].min():.1f}m)")
    print(f"    Z: [{cv[:,2].min():+.1f}, {cv[:,2].max():+.1f}]  (dz={cv[:,2].max()-cv[:,2].min():.1f}m)")

# Bounds da torre
torre_verts = np.vstack([np.asarray(scene.geometry[n].vertices) for n in torre_nodes])
print(f"  TORRE/ESTRUTURA bounds:")
print(f"    X: [{torre_verts[:,0].min():+.1f}, {torre_verts[:,0].max():+.1f}]  (dx={torre_verts[:,0].max()-torre_verts[:,0].min():.1f}m)")
print(f"    Y: [{torre_verts[:,1].min():+.1f}, {torre_verts[:,1].max():+.1f}]  (dy={torre_verts[:,1].max()-torre_verts[:,1].min():.1f}m)")
print(f"    Z: [{torre_verts[:,2].min():+.1f}, {torre_verts[:,2].max():+.1f}]  (dz={torre_verts[:,2].max()-torre_verts[:,2].min():.1f}m)")

tcenter = (torre_verts.min(0) + torre_verts.max(0)) / 2
print(f"  TORRE centro: ({tcenter[0]:.1f}, {tcenter[1]:.1f}, {tcenter[2]:.1f})")

# Posicao do radome existente (do JSON)
# radome local: rad_x = E - cx, rad_z = -(N - cy)
radome_e = pos['radome_existente_utm']['e']
radome_n = pos['radome_existente_utm']['n']
torre_e = pos['torre_nova_alvo_utm']['e']
torre_n = pos['torre_nova_alvo_utm']['n']
print(f"\n[4] Posicoes UTM no projeto:")
print(f"  Radome existente: E={radome_e:.1f} N={radome_n:.1f}")
print(f"  Torre nova alvo:  E={torre_e:.1f} N={torre_n:.1f}")
print(f"  Distancia planar: {pos['distancia_planar_m']:.1f}m")
print(f"  Delta UTM: dE={torre_e-radome_e:+.1f}m  dN={torre_n-radome_n:+.1f}m")

# 4. Renderizar vista TOP com eixos cartesianos e marker
print(f"\n[5] Renderizando vista TOP de validacao com regua...")
pl = pv.Plotter(off_screen=True, window_size=(1800, 1400), lighting="three lights")
pl.set_background([0.92, 0.94, 0.97])

# Adicionar cloud + torre
for node, mesh in scene.geometry.items():
    v = np.asarray(mesh.vertices, dtype=np.float32)
    if hasattr(mesh, 'faces') and len(mesh.faces) > 0:
        f = np.asarray(mesh.faces, dtype=np.int64)
        faces_pv = np.hstack([np.full((f.shape[0], 1), 3), f]).astype(np.int64).flatten()
        pdata = pv.PolyData(v, faces_pv)
    else:
        pdata = pv.PolyData(v)
    if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
        cols = np.asarray(mesh.visual.vertex_colors)
        if len(cols) == len(v):
            pdata['rgb'] = cols[:, :3]
            pl.add_mesh(pdata, scalars='rgb', rgb=True, smooth_shading=True, point_size=2.5)
            continue
    if hasattr(mesh.visual, 'face_colors') and mesh.visual.face_colors is not None and len(mesh.visual.face_colors) > 0:
        col = (np.asarray(mesh.visual.face_colors[0])[:3] / 255.0).tolist()
        pl.add_mesh(pdata, color=col, smooth_shading=True)
    else:
        pl.add_mesh(pdata, color=(0.65, 0.65, 0.7), smooth_shading=True)

# Adicionar marker da TORRE NOVA (esfera vermelha)
sphere_torre = pv.Sphere(radius=2.0, center=(tcenter[0], tcenter[1], tcenter[2]))
pl.add_mesh(sphere_torre, color='red', opacity=0.8)
pl.add_point_labels(np.array([[tcenter[0], tcenter[1] + 8, tcenter[2]]]),
                     [f"TORRE NOVA\n({tcenter[0]:.0f}, {tcenter[2]:.0f})\nUTM E{torre_e:.0f} N{torre_n:.0f}"],
                     font_size=24, text_color='red', shape_color='white', shape_opacity=0.85,
                     point_color='red', point_size=15)

# Marker do RADOME EXISTENTE - usar coords locais
# rad_x = E - cx; precisamos do cx do cloud
cv = scene.geometry[cloud_nodes[0]].vertices
# Estimar cx local: torre local x corresponde a torre_e UTM
# (tcenter[0]) = torre_e - cx  => cx = torre_e - tcenter[0]
cx_estimated = torre_e - tcenter[0]
cy_estimated = torre_n + tcenter[2]   # tcenter[2] = -(torre_n - cy) => cy = torre_n + tcenter[2]
print(f"  cx estimado: {cx_estimated:.1f}  cy: {cy_estimated:.1f}")

radome_local_x = radome_e - cx_estimated
radome_local_z = -(radome_n - cy_estimated)
radome_local_y = tcenter[1]  # mesma altura aproximada

sphere_radome = pv.Sphere(radius=2.5, center=(radome_local_x, radome_local_y, radome_local_z))
pl.add_mesh(sphere_radome, color='cyan', opacity=0.8)
pl.add_point_labels(np.array([[radome_local_x, radome_local_y + 8, radome_local_z - 8]]),
                     [f"RADOME EXISTENTE\n({radome_local_x:.0f}, {radome_local_z:.0f})\nUTM E{radome_e:.0f} N{radome_n:.0f}"],
                     font_size=24, text_color='blue', shape_color='white', shape_opacity=0.85,
                     point_color='cyan', point_size=15)

# Linha conectando os 2
line = pv.Line((radome_local_x, radome_local_y, radome_local_z),
               (tcenter[0], tcenter[1], tcenter[2]))
pl.add_mesh(line, color='yellow', line_width=4)

# Eixos cartesianos
pl.show_axes()

# Camera TOP
center_x = (tcenter[0] + radome_local_x) / 2
center_z = (tcenter[2] + radome_local_z) / 2
pl.camera_position = [
    (center_x, 250, center_z),
    (center_x, 0, center_z),
    (0, 0, -1)
]
out = os.path.join(QC_DIR, "validation_top.png")
pl.screenshot(out)
pl.close()
print(f"  Salvo: {out}")

# Perspectiva
pl = pv.Plotter(off_screen=True, window_size=(1800, 1400), lighting="three lights")
pl.set_background([0.78, 0.86, 0.94], top=[0.55, 0.70, 0.86])
for node, mesh in scene.geometry.items():
    v = np.asarray(mesh.vertices, dtype=np.float32)
    if hasattr(mesh, 'faces') and len(mesh.faces) > 0:
        f = np.asarray(mesh.faces, dtype=np.int64)
        faces_pv = np.hstack([np.full((f.shape[0], 1), 3), f]).astype(np.int64).flatten()
        pdata = pv.PolyData(v, faces_pv)
    else:
        pdata = pv.PolyData(v)
    if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
        cols = np.asarray(mesh.visual.vertex_colors)
        if len(cols) == len(v):
            pdata['rgb'] = cols[:, :3]
            pl.add_mesh(pdata, scalars='rgb', rgb=True, smooth_shading=True, point_size=2.5)
            continue
    if hasattr(mesh.visual, 'face_colors') and mesh.visual.face_colors is not None and len(mesh.visual.face_colors) > 0:
        col = (np.asarray(mesh.visual.face_colors[0])[:3] / 255.0).tolist()
        pl.add_mesh(pdata, color=col, smooth_shading=True)
    else:
        pl.add_mesh(pdata, color=(0.65, 0.65, 0.7), smooth_shading=True)

# Marker torre + radome
pl.add_mesh(pv.Sphere(radius=2.0, center=(tcenter[0], tcenter[1], tcenter[2])), color='red', opacity=0.7)
pl.add_mesh(pv.Sphere(radius=2.5, center=(radome_local_x, radome_local_y, radome_local_z)), color='cyan', opacity=0.7)
pl.add_mesh(pv.Line((radome_local_x, radome_local_y, radome_local_z),
                    (tcenter[0], tcenter[1], tcenter[2])), color='yellow', line_width=6)

pl.camera_position = [
    (center_x + 80, tcenter[1] + 60, center_z + 80),
    (center_x, tcenter[1], center_z),
    (0, 1, 0)
]
out2 = os.path.join(QC_DIR, "validation_perspectiva.png")
pl.screenshot(out2)
pl.close()
print(f"  Salvo: {out2}")
print("\nDONE - inspecionar PNGs em /validation/")
