"""
Renderiza modelo V2 com pyvista (VTK) - qualidade fotorrealista.
8 vistas: perspectivas, fachadas, planta, closes.
"""
import os
os.environ["PYVISTA_OFF_SCREEN"] = "true"
import pyvista as pv
pv.OFF_SCREEN = True
import numpy as np
import trimesh

GLB = r"C:\Users\23GAMER\Downloads\torre_radar_extract\modelo_3d\torre_radar_v2.glb"
OUT_DIR = r"C:\Users\23GAMER\Downloads\torre_radar_extract\modelo_3d\render_pyvista"
os.makedirs(OUT_DIR, exist_ok=True)

# Carregar GLB
scene = trimesh.load(GLB, force="scene")
print(f"Geometrias: {len(scene.geometry)}")

# Cores por grupo (mais ricas para PBR)
def color_for(node_name):
    n = node_name.lower()
    if "telhado" in n or "telha" in n: return ((0.50, 0.30, 0.22), 0.85, 0.0)  # diffuse, roughness, metallic
    if "guard" in n or "gc_" in n:       return ((0.86, 0.74, 0.16), 0.40, 0.7)
    if "porta" in n or "veneziana" in n or "esquadria" in n or "cabine_porta" in n: return ((0.16, 0.32, 0.45), 0.30, 0.5)
    if "vidro" in n or "janela" in n:    return ((0.65, 0.78, 0.88), 0.10, 0.0)
    if "agua" in n:                       return ((0.23, 0.51, 0.71), 0.40, 0.0)
    if "gerador" in n:                    return ((0.18, 0.40, 0.20), 0.50, 0.3)
    if "transformador" in n or "nobreak" in n or "qg_" in n: return ((0.30, 0.30, 0.32), 0.60, 0.4)
    if "bateria" in n:                    return ((0.10, 0.10, 0.12), 0.70, 0.2)
    if "condensadora" in n:               return ((0.92, 0.92, 0.92), 0.40, 0.1)
    if "carro_corpo" in n or "carro_teto" in n: return ((0.70, 0.20, 0.20), 0.30, 0.4)
    if "carro_roda" in n:                 return ((0.05, 0.05, 0.05), 0.90, 0.1)
    if "mureta" in n:                     return ((0.78, 0.74, 0.65), 0.80, 0.0)
    if "gradil" in n:                     return ((0.35, 0.37, 0.40), 0.50, 0.6)
    if "fossa" in n or "sumidouro" in n or "tampa" in n: return ((0.45, 0.42, 0.38), 0.85, 0.0)
    if "perna" in n or "travessa" in n or "diag" in n or "estrutura" in n: return ((0.30, 0.32, 0.36), 0.45, 0.8)
    if "degrau" in n or "corrimao" in n or "aco_galv" in n: return ((0.62, 0.65, 0.70), 0.50, 0.7)
    if "patamar" in n:                    return ((0.50, 0.50, 0.55), 0.55, 0.5)
    if "fundacao" in n or "estaca" in n or "concreto" in n or "plataforma_laje" in n or "edif_piso" in n: return ((0.78, 0.78, 0.78), 0.85, 0.0)
    if "radome" in n:                     return ((0.95, 0.95, 0.96), 0.20, 0.0)
    if "refletor" in n:                   return ((1.00, 0.92, 0.65), 0.40, 0.2)
    if "lsf_parede" in n or "edif_parede" in n: return ((0.92, 0.88, 0.80), 0.85, 0.0)
    if "edif_div" in n or "lsf_interna" in n: return ((0.80, 0.76, 0.68), 0.85, 0.0)
    if "solo" in n or "terreno" in n:    return ((0.62, 0.55, 0.40), 0.95, 0.0)
    if "caixa_suporte" in n:             return ((0.55, 0.58, 0.60), 0.55, 0.7)
    if "cabine_parede" in n:             return ((0.92, 0.88, 0.80), 0.85, 0.0)
    return ((0.60, 0.60, 0.62), 0.60, 0.0)

# Construir plotter
def make_plotter(off_screen=True, window_size=(1920, 1280)):
    pl = pv.Plotter(off_screen=off_screen, window_size=window_size, lighting="none")
    pl.set_background([0.86, 0.91, 0.96], top=[0.62, 0.74, 0.88])  # gradient ceu

    # Adicionar geometrias
    for node, mesh in scene.geometry.items():
        v = mesh.vertices.astype(np.float32)
        f = mesh.faces.astype(np.int64)
        # pyvista pede faces no formato [3, a, b, c, 3, d, e, f, ...]
        faces_pv = np.hstack([np.full((f.shape[0], 1), 3), f]).astype(np.int64).flatten()
        pdata = pv.PolyData(v, faces_pv)
        col, rough, metal = color_for(node)
        op = 0.5 if "vidro" in node.lower() or "janela" in node.lower() else 1.0
        pl.add_mesh(pdata, color=col, smooth_shading=True,
                    metallic=metal, roughness=rough,
                    pbr=True, opacity=op,
                    show_edges=False)

    # Iluminacao 3-point
    pl.add_light(pv.Light(position=(25, -15, 35), focal_point=(-3, 0, 10),
                          color="white", intensity=0.9, light_type="scene light"))
    pl.add_light(pv.Light(position=(-30, 20, 25), focal_point=(-3, 0, 10),
                          color=[0.85, 0.9, 1.0], intensity=0.4, light_type="scene light"))
    pl.add_light(pv.Light(position=(0, -30, 8), focal_point=(-3, 0, 5),
                          color=[1.0, 0.92, 0.85], intensity=0.3, light_type="scene light"))
    return pl

VIEWS = [
    # (name, camera_position, focal_point, view_up)
    # ENQUADRAR PARA MOSTRAR ATE Z=30m (incluindo radome)
    ("01_perspectiva_geral",
     (35, -28, 30), (-3, 0, 14), (0, 0, 1)),
    ("02_perspectiva_proxima_torre",
     (14, -12, 22), (0, 0, 16), (0, 0, 1)),
    ("03_fachada_sul",
     (-3, -45, 14), (-3, 0, 14), (0, 0, 1)),
    ("04_fachada_oeste",
     (-45, 0, 14), (-3, 0, 14), (0, 0, 1)),
    ("05_planta_topo",
     (-3, 0, 55), (-3, 0, 11), (0, 1, 0)),
    ("06_close_topo_torre",
     (12, -12, 26), (0, 0, 24), (0, 0, 1)),
    ("07_close_base_torre",
     (10, -8, 4), (0, 0, 2), (0, 0, 1)),
    ("08_close_edificacao",
     (-3, -15, 4), (-8, 0, 2.5), (0, 0, 1)),
    ("09_isometrica_NE",
     (28, 28, 32), (-3, 0, 13), (0, 0, 1)),
    ("10_perspectiva_aerea",
     (20, -30, 38), (-3, 0, 12), (0, 0, 1)),
]

for name, cam, foc, up in VIEWS:
    pl = make_plotter()
    pl.camera.position = cam
    pl.camera.focal_point = foc
    pl.camera.up = up
    pl.camera.zoom(1.0)
    out = os.path.join(OUT_DIR, f"render_{name}.png")
    pl.screenshot(out, transparent_background=False, return_img=False)
    pl.close()
    sz = os.path.getsize(out) / 1024
    print(f"  OK  {name}: {sz:.0f} KB -> {out}")

print("\nDONE")
