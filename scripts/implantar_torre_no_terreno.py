"""
============================================================================
IMPLANTAR TORRE NO TERRENO - Pipeline Point Cloud + Torre Radar V3
============================================================================
Carrega uma nuvem de pontos do levantamento topografico (Toposcan) e:
  1. Detecta o terreno (Z mais baixo por celula XY) ou usa todo o cloud
  2. Aceita coordenada UTM de implantacao (E, N, h) OU posiciona via mouse
  3. Translada o modelo 3D da torre para essa posicao
  4. Renderiza cena combinada (terreno + torre)
  5. Exporta cena unificada (.glb com terreno + torre)

USO:
  python implantar_torre_no_terreno.py --cloud caminho/nuvem.las --easting 7180000 --northing 423500 --elev 920
  python implantar_torre_no_terreno.py --cloud caminho/nuvem.ply         (modo: posiciona no centro)
  python implantar_torre_no_terreno.py --demo                            (gera terreno sintetico pra teste)

FORMATOS SUPORTADOS:
  .las / .laz  (laspy)
  .ply / .xyz  (pyvista nativo)

NOTA: o modelo da torre tem origem (0,0,0) no centro da base. A nuvem
pode estar em coordenadas UTM grandes. O script faz translacao
necessaria para a torre cair no ponto certo.
============================================================================
"""
import os, sys, argparse
import numpy as np
import trimesh

# Headless rendering
os.environ["PYVISTA_OFF_SCREEN"] = "true"
import pyvista as pv
pv.OFF_SCREEN = True

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB_TORRE = os.path.join(_REPO, "models", "torre_radar_v3.glb")
OUT_DIR = os.path.join(_REPO, "models", "demo")
os.makedirs(OUT_DIR, exist_ok=True)


def load_pointcloud(path):
    """Carrega point cloud em multi-formato. Retorna (Nx3 array, opcional Nx3 cores)."""
    ext = os.path.splitext(path)[1].lower()
    print(f"[cloud] Carregando {path}  (extensao: {ext})")
    if ext in (".las", ".laz"):
        import laspy
        las = laspy.read(path)
        pts = np.column_stack([las.x, las.y, las.z]).astype(np.float64)
        colors = None
        if hasattr(las, "red") and hasattr(las, "green") and hasattr(las, "blue"):
            colors = np.column_stack([las.red, las.green, las.blue]).astype(np.float32)
            if colors.max() > 255:
                colors = colors / 256.0  # LAS sometimes 16bit
            colors = (colors/255.0).clip(0,1)
        print(f"[cloud] LAS carregado: {len(pts)} pontos")
        return pts, colors

    elif ext in (".ply", ".xyz", ".pcd", ".vtk", ".obj"):
        cloud = pv.read(path)
        pts = np.asarray(cloud.points, dtype=np.float64)
        colors = None
        if "RGB" in cloud.array_names:
            colors = (np.asarray(cloud["RGB"]) / 255.0).clip(0, 1)
        print(f"[cloud] Cloud carregado: {len(pts)} pontos")
        return pts, colors

    else:
        raise ValueError(f"Formato nao suportado: {ext}")


def make_demo_terrain(out_path):
    """Gera terreno sintetico pra demonstracao (sem nuvem real ainda)."""
    print("[demo] Gerando terreno sintetico para demonstracao...")
    nx, ny = 200, 150
    xs = np.linspace(-30, 30, nx)
    ys = np.linspace(-20, 20, ny)
    X, Y = np.meshgrid(xs, ys)
    # Terreno suave com leve declive + ondulacao
    Z = (
        + 0.10 * X                            # declive geral
        + 0.5 * np.sin(X/8.0) * np.cos(Y/6.0) # ondulacoes
        + 0.3 * np.cos(X/12.0 + Y/10.0)
        + np.random.normal(0, 0.05, X.shape)  # ruido p/ parecer ponto real
    )
    # Y-up para GLTF: trocar Z (altura nativa) para Y, e Y nativo (planar) vai p/ -Z
    pts = np.column_stack([X.ravel(), Z.ravel(), -Y.ravel()])  # x, height(y), -depth(z)
    # Cores baseadas em altura (Y agora) - verde p/ baixo, marrom p/ alto
    z_norm = (pts[:, 1] - pts[:, 1].min()) / (np.ptp(pts[:, 1]) + 1e-9)
    colors = np.column_stack([
        0.40 + 0.40*z_norm,    # R: aumenta com altura
        0.55 + 0.15*(1-z_norm), # G: fica verde no baixo
        0.30 + 0.10*(1-z_norm), # B
    ])
    # Salvar como PLY
    cloud = pv.PolyData(pts)
    cloud["RGB"] = (colors * 255).astype(np.uint8)
    cloud.save(out_path)
    print(f"[demo] Terreno sintetico salvo: {out_path}  ({len(pts)} pontos)")
    return pts, colors


def load_tower_model():
    """Carrega o modelo da torre V3."""
    print(f"[torre] Carregando {GLB_TORRE}")
    scene = trimesh.load(GLB_TORRE, force="scene")
    print(f"[torre] {len(scene.geometry)} geometrias")
    return scene


def color_for(name):
    """Atribui cor + PBR baseado no nome do node."""
    n = name.lower()
    if "telhado" in n or "telha" in n: return ((0.50,0.30,0.22), 0.85, 0.0)
    if "guard" in n or "gc_" in n:       return ((0.86,0.74,0.16), 0.40, 0.7)
    if "porta" in n or "veneziana" in n or "esquadria" in n: return ((0.16,0.32,0.45), 0.30, 0.5)
    if "vidro" in n or "janela" in n:    return ((0.65,0.78,0.88), 0.10, 0.0)
    if "agua" in n:                       return ((0.23,0.51,0.71), 0.40, 0.0)
    if "gerador" in n:                    return ((0.18,0.40,0.20), 0.50, 0.3)
    if "transformador" in n or "nobreak" in n: return ((0.30,0.30,0.32), 0.60, 0.4)
    if "bateria" in n:                    return ((0.10,0.10,0.12), 0.70, 0.2)
    if "condensadora" in n:               return ((0.92,0.92,0.92), 0.40, 0.1)
    if "carro_corpo" in n or "carro_teto" in n: return ((0.70,0.20,0.20), 0.30, 0.4)
    if "carro_roda" in n:                 return ((0.05,0.05,0.05), 0.90, 0.1)
    if "mureta" in n:                     return ((0.78,0.74,0.65), 0.80, 0.0)
    if "gradil" in n:                     return ((0.35,0.37,0.40), 0.50, 0.6)
    if "fossa" in n or "sumidouro" in n or "tampa" in n: return ((0.45,0.42,0.38), 0.85, 0.0)
    if "perna" in n or "travessa" in n or "diag" in n: return ((0.30,0.32,0.36), 0.45, 0.8)
    if "degrau" in n or "corrimao" in n or "aco_galv" in n: return ((0.62,0.65,0.70), 0.50, 0.7)
    if "patamar" in n:                    return ((0.50,0.50,0.55), 0.55, 0.5)
    if "fundacao" in n or "estaca" in n or "concreto" in n or "plataforma_laje" in n or "edif_piso" in n:
        return ((0.78,0.78,0.78), 0.85, 0.0)
    if "radome" in n:                     return ((0.95,0.95,0.96), 0.20, 0.0)
    if "refletor" in n:                   return ((1.00,0.92,0.65), 0.40, 0.2)
    if "lsf_parede" in n or "edif_parede" in n: return ((0.92,0.88,0.80), 0.85, 0.0)
    if "edif_div" in n or "lsf_interna" in n: return ((0.80,0.76,0.68), 0.85, 0.0)
    if "caixa_suporte" in n:             return ((0.55,0.58,0.60), 0.55, 0.7)
    if "cabine_parede" in n:             return ((0.92,0.88,0.80), 0.85, 0.0)
    return ((0.60,0.60,0.62), 0.60, 0.0)


def _populate_plotter(pl, cloud_pts, cloud_colors, tower_scene, tower_xyz_offset):
    """Adiciona terreno + torre + iluminacao a um plotter."""
    if cloud_pts is not None:
        terrain = pv.PolyData(cloud_pts)
        if cloud_colors is not None:
            terrain["RGB"] = (cloud_colors * 255).astype(np.uint8)
            pl.add_mesh(terrain, scalars="RGB", rgb=True,
                        point_size=3.0, render_points_as_spheres=False, opacity=1.0)
        else:
            pl.add_mesh(terrain, color=(0.55, 0.50, 0.40), point_size=2.5)

    ox, oy, oz = tower_xyz_offset
    for node, mesh in tower_scene.geometry.items():
        v = mesh.vertices.astype(np.float64).copy()
        v[:, 0] += ox; v[:, 1] += oy; v[:, 2] += oz
        f = mesh.faces.astype(np.int64)
        faces_pv = np.hstack([np.full((f.shape[0],1), 3), f]).astype(np.int64).flatten()
        pdata = pv.PolyData(v.astype(np.float32), faces_pv)
        col, rough, metal = color_for(node)
        op = 0.5 if "vidro" in node.lower() or "janela" in node.lower() else 1.0
        pl.add_mesh(pdata, color=col, smooth_shading=True,
                    metallic=metal, roughness=rough, pbr=True, opacity=op,
                    show_edges=False)

    cam_z = oz + 35
    pl.add_light(pv.Light(position=(ox+25, oy-15, cam_z+5), focal_point=(ox, oy, oz+10),
                          color="white", intensity=0.9, light_type="scene light"))
    pl.add_light(pv.Light(position=(ox-30, oy+20, cam_z-5), focal_point=(ox, oy, oz+10),
                          color=[0.85,0.9,1.0], intensity=0.4, light_type="scene light"))
    pl.add_light(pv.Light(position=(ox, oy-30, oz+8), focal_point=(ox, oy, oz+5),
                          color=[1.0,0.92,0.85], intensity=0.3, light_type="scene light"))


def render_scene(cloud_pts, cloud_colors, tower_scene, tower_xyz_offset, render_dir):
    """Renderiza cena em multiplas vistas (plotter fresco por vista pra evitar cache)."""
    ox, oy, oz = tower_xyz_offset
    views = [
        ("01_implantacao_perspectiva", (ox+35, oy-28, oz+30), (ox-2, oy, oz+14), (0,0,1)),
        ("02_implantacao_aerea",       (ox+20, oy-30, oz+45), (ox-2, oy, oz+12), (0,0,1)),
        ("03_implantacao_lateral",     (ox-3, oy-50, oz+14),  (ox-3, oy, oz+14), (0,0,1)),
        ("04_implantacao_planta",      (ox-3, oy, oz+60),     (ox-3, oy, oz+11), (0,1,0)),
        ("05_implantacao_baixa",       (ox+20, oy-25, oz+6),  (ox-2, oy, oz+5),  (0,0,1)),
    ]
    out_files = []
    for name, cam, foc, up in views:
        pl = pv.Plotter(off_screen=True, window_size=(1920, 1280), lighting="none")
        pl.set_background([0.86,0.91,0.96], top=[0.62,0.74,0.88])
        _populate_plotter(pl, cloud_pts, cloud_colors, tower_scene, tower_xyz_offset)
        pl.camera_position = [cam, foc, up]   # forma confiavel: passar [pos, focal, up]
        out = os.path.join(render_dir, f"{name}.png")
        pl.screenshot(out, transparent_background=False, return_img=False)
        size_kb = os.path.getsize(out)/1024
        print(f"  OK  {name}: {size_kb:.0f} KB")
        out_files.append(out)
        pl.close()
    return out_files


def export_combined_scene(cloud_pts, cloud_colors, tower_scene, tower_xyz_offset, out_glb):
    """Exporta cena unificada (terreno + torre) em GLB."""
    print(f"[export] Combinando para {out_glb}")
    out_scene = trimesh.Scene()

    # Adicionar nuvem de pontos como PointCloud trimesh
    if cloud_pts is not None:
        # Subsample se muitos pontos
        n = len(cloud_pts)
        if n > 300000:
            idx = np.random.choice(n, 300000, replace=False)
            sub_pts = cloud_pts[idx]
            sub_col = cloud_colors[idx] if cloud_colors is not None else None
        else:
            sub_pts = cloud_pts
            sub_col = cloud_colors
        pc = trimesh.PointCloud(vertices=sub_pts,
                                colors=(sub_col*255).astype(np.uint8) if sub_col is not None else None)
        out_scene.add_geometry(pc, geom_name="terreno_pontos", node_name="terreno_pontos")

    # Adicionar geometrias da torre transladadas
    ox, oy, oz = tower_xyz_offset
    for node, mesh in tower_scene.geometry.items():
        m = mesh.copy()
        m.apply_translation([ox, oy, oz])
        out_scene.add_geometry(m, geom_name=node, node_name=node)

    out_scene.export(out_glb)
    print(f"[export] OK {out_glb}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloud", help="Caminho para nuvem de pontos (.las/.laz/.ply/.xyz)")
    ap.add_argument("--demo", action="store_true", help="Usar terreno sintetico de demonstracao")
    ap.add_argument("--easting", type=float, help="Coord UTM E do ponto de implantacao")
    ap.add_argument("--northing", type=float, help="Coord UTM N do ponto de implantacao")
    ap.add_argument("--elev", type=float, help="Cota Z do ponto de implantacao")
    ap.add_argument("--out", default=OUT_DIR, help="Diretorio de saida")
    args = ap.parse_args()

    if args.demo or not args.cloud:
        demo_path = os.path.join(args.out, "terreno_demo.ply")
        if not os.path.exists(demo_path) or args.demo:
            make_demo_terrain(demo_path)
        cloud_path = demo_path
    else:
        cloud_path = args.cloud

    cloud_pts, cloud_colors = load_pointcloud(cloud_path)

    # Determinar ponto de implantacao
    if args.easting is not None and args.northing is not None:
        # Coord UTM fornecida
        z_target = args.elev if args.elev is not None else cloud_pts[:, 2].mean()
        target = np.array([args.easting, args.northing, z_target])
        print(f"[implantacao] Usando coords UTM fornecidas: E={args.easting} N={args.northing} h={z_target:.2f}")
    else:
        # Centroide do cloud + minZ + 5% (parecer estar no chao)
        cx = cloud_pts[:, 0].mean()
        cy = cloud_pts[:, 1].mean()
        # Procurar Z minimo proximo do centro (terreno mais baixo => fundacao)
        dist2 = (cloud_pts[:, 0] - cx)**2 + (cloud_pts[:, 1] - cy)**2
        # 1% mais proximo do centro
        n_near = max(int(len(cloud_pts) * 0.01), 50)
        idx_near = np.argpartition(dist2, n_near)[:n_near]
        z_target = cloud_pts[idx_near, 2].mean()
        target = np.array([cx, cy, z_target])
        print(f"[implantacao] Usando centroide do cloud: ({cx:.2f}, {cy:.2f}, {z_target:.2f})")

    # Carregar torre e definir offset
    tower_scene = load_tower_model()
    offset = target  # (0,0,0) da torre vai para target

    # Renderizar
    out_files = render_scene(cloud_pts, cloud_colors, tower_scene, offset, args.out)

    # Exportar cena combinada
    out_glb = os.path.join(args.out, "cena_torre_terreno.glb")
    export_combined_scene(cloud_pts, cloud_colors, tower_scene, offset, out_glb)

    print(f"\n[OK] Implantacao concluida. {len(out_files)} renders + 1 GLB combinado.")
    print(f"Saida em: {args.out}")

if __name__ == "__main__":
    main()
