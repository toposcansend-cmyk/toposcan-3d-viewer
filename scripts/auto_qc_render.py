"""
Auto-QC: renderiza a cena SIMEPAR (mesh + torre) em 8 angulos pra revisao.
Salva PNGs que o agente vai inspecionar criticamente.
"""
import os
os.environ["PYVISTA_OFF_SCREEN"] = "true"
import pyvista as pv
pv.OFF_SCREEN = True
import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENE = os.path.join(ROOT, "models", "simepar", "simepar_torre_real.glb")
OUT = os.path.join(ROOT, "models", "simepar", "qc_renders")
os.makedirs(OUT, exist_ok=True)

print(f"Carregando: {SCENE}  ({os.path.getsize(SCENE)/1024**2:.1f} MB)")
scene = trimesh.load(SCENE, force='scene')
print(f"Geometrias: {len(scene.geometry)}")

# Bounds
all_verts = np.vstack([np.asarray(g.vertices) for g in scene.geometry.values()])
bmin, bmax = all_verts.min(0), all_verts.max(0)
center = (bmin + bmax) / 2
print(f"Bounds X: [{bmin[0]:.1f}, {bmax[0]:.1f}]  ({bmax[0]-bmin[0]:.1f}m)")
print(f"Bounds Y: [{bmin[1]:.1f}, {bmax[1]:.1f}]  ({bmax[1]-bmin[1]:.1f}m)")
print(f"Bounds Z: [{bmin[2]:.1f}, {bmax[2]:.1f}]  ({bmax[2]-bmin[2]:.1f}m)")

# Identificar torre vs terreno (torre tem nomes contendo perna/cabine/radome/etc)
torre_nodes = [n for n in scene.geometry if any(k in n.lower() for k in
    ['perna','cabine','radome','plataforma_laje','escada','degrau','fundacao','estaca',
     'patamar','gc_','refletor','edif_','carro','mureta','gradil','fossa','sumidouro',
     'travessa','diag_'])]
terrain_nodes = [n for n in scene.geometry if n not in torre_nodes]
print(f"Torre nodes: {len(torre_nodes)}, Terreno nodes: {len(terrain_nodes)}")

# Bounds da torre apenas
if torre_nodes:
    torre_verts = np.vstack([np.asarray(scene.geometry[n].vertices) for n in torre_nodes])
    tmin, tmax = torre_verts.min(0), torre_verts.max(0)
    tcenter = (tmin + tmax) / 2
    print(f"\nTORRE bounds:")
    print(f"  X: [{tmin[0]:.1f}, {tmax[0]:.1f}]  dx={tmax[0]-tmin[0]:.1f}m")
    print(f"  Y: [{tmin[1]:.1f}, {tmax[1]:.1f}]  dy={tmax[1]-tmin[1]:.1f}m (altura)")
    print(f"  Z: [{tmin[2]:.1f}, {tmax[2]:.1f}]  dz={tmax[2]-tmin[2]:.1f}m")
    print(f"  Centro: ({tcenter[0]:.1f}, {tcenter[1]:.1f}, {tcenter[2]:.1f})")

def make_plotter():
    pl = pv.Plotter(off_screen=True, window_size=(1600, 1200), lighting="three lights")
    pl.set_background([0.78, 0.86, 0.94], top=[0.55, 0.70, 0.86])
    # Adicionar todas as geometrias
    for node, mesh in scene.geometry.items():
        v = np.asarray(mesh.vertices, dtype=np.float32)
        if hasattr(mesh, 'faces') and len(mesh.faces) > 0:
            f = np.asarray(mesh.faces, dtype=np.int64)
            faces_pv = np.hstack([np.full((f.shape[0], 1), 3), f]).astype(np.int64).flatten()
            pdata = pv.PolyData(v, faces_pv)
        else:
            pdata = pv.PolyData(v)
        # Cor: se tem vertex_colors usa; senao usa branco
        if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
            cols = np.asarray(mesh.visual.vertex_colors)
            if len(cols) == len(v):
                pdata['rgb'] = cols[:, :3]
                pl.add_mesh(pdata, scalars='rgb', rgb=True, smooth_shading=True)
                continue
        if hasattr(mesh.visual, 'face_colors') and mesh.visual.face_colors is not None and len(mesh.visual.face_colors) > 0:
            col_arr = np.asarray(mesh.visual.face_colors[0])
            col = (col_arr[:3] / 255.0).tolist() if len(col_arr) >= 3 else (0.7, 0.7, 0.7)
            pl.add_mesh(pdata, color=col, smooth_shading=True)
        else:
            pl.add_mesh(pdata, color=(0.65, 0.65, 0.7), smooth_shading=True)
    return pl

# 8 vistas
views = [
    ("01_aerea_45",        (tcenter[0]+150, 90, tcenter[2]+150), tcenter, (0,1,0)),
    ("02_top_planta",      (tcenter[0], 200, tcenter[2]+0.01), tcenter, (0,0,-1)),
    ("03_torre_perspectiva", (tcenter[0]+60, tcenter[1]+40, tcenter[2]+60), tcenter, (0,1,0)),
    ("04_torre_close",     (tcenter[0]+25, tcenter[1]+15, tcenter[2]+25), tcenter, (0,1,0)),
    ("05_torre_lateral",   (tcenter[0]+80, tcenter[1]+10, tcenter[2]), tcenter, (0,1,0)),
    ("06_base_torre",      (tcenter[0]+15, tcenter[1]-5, tcenter[2]+15), (tcenter[0], tmin[1], tcenter[2]), (0,1,0)),
    ("07_overview_baixo",  (bmin[0]-50, 50, bmax[2]+50), tcenter, (0,1,0)),
    ("08_horizonte_torre", (tcenter[0]+200, tcenter[1]+25, tcenter[2]+50), tcenter, (0,1,0)),
]

for name, cam, foc, up in views:
    pl = make_plotter()
    pl.camera_position = [cam, foc, up]
    out_png = os.path.join(OUT, f"qc_{name}.png")
    pl.screenshot(out_png, return_img=False)
    sz = os.path.getsize(out_png) / 1024
    print(f"  {name}: {sz:.0f} KB")
    pl.close()

print(f"\nTodos salvos em {OUT}")
