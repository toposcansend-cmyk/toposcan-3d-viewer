"""
Converte PLY de mesh de igreja (com textura JPG) -> GLB comprimido para web.

Pipeline:
1. Carrega PLY com trimesh (preservando UV se houver)
2. Aplica rotacao Z-up -> Y-up (GLTF 2.0 standard)
3. Decima se muito pesado (faces > 500k)
4. Exporta GLB (Draco se disponivel) com textura embed
"""
import os
import sys
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "models", "igrejas")
os.makedirs(MODELS, exist_ok=True)

# Conversao Z-up -> Y-up
ROT_YUP = rotation_matrix(-np.pi/2, [1, 0, 0])

def convert(ply_path, out_name, texture_path=None, max_faces=2_000_000, no_decimate=False):
    print(f"\n{'='*70}\nProcessando: {ply_path}")
    print(f"  Tamanho: {os.path.getsize(ply_path)/1024/1024:.1f} MB")

    print("  Carregando PLY (isso pode demorar)...")
    mesh = trimesh.load(ply_path, process=False)
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Faces:    {len(mesh.faces):,}")

    has_uv = hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None
    has_vcolor = hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None
    print(f"  UV (texture coords): {has_uv}")
    print(f"  Vertex colors: {has_vcolor}")

    # Centralizar (origem no centroide horizontal, base no Z=0)
    centroid = mesh.vertices.mean(axis=0)
    min_z = mesh.vertices[:, 2].min()
    mesh.vertices[:, 0] -= centroid[0]
    mesh.vertices[:, 1] -= centroid[1]
    mesh.vertices[:, 2] -= min_z

    # Rotaciona Z-up -> Y-up
    mesh.apply_transform(ROT_YUP)
    b = mesh.bounds
    print(f"  Bounds (Y-up, centralizado): X={b[1][0]-b[0][0]:.1f}m Y={b[1][1]-b[0][1]:.1f}m Z={b[1][2]-b[0][2]:.1f}m")

    # Capturar UVs e cores ANTES da decimacao (sera mapeado por nearest-neighbor)
    original_uvs = None
    original_colors = None
    if has_uv:
        try:
            original_uvs = np.asarray(mesh.visual.uv, dtype=np.float32).copy()
            print(f"    UVs capturados: shape={original_uvs.shape}")
        except Exception as e:
            print(f"    aviso UV capture: {e}")
    if has_vcolor:
        try:
            original_colors = np.asarray(mesh.visual.vertex_colors, dtype=np.uint8).copy()
            print(f"    Cores capturadas: shape={original_colors.shape}")
        except Exception as e:
            print(f"    aviso color capture: {e}")
    original_vertices = mesh.vertices.copy()

    # **TRUQUE-CHAVE**: se tem textura + UV, samplar JPG e converter em VERTEX COLORS.
    # Vertex colors sao MUITO mais robustas a decimacao do que UV mapping.
    # (UV remap por NN distorce textura; vertex colors so misturam por NN sem distorcer)
    if has_uv and texture_path and os.path.exists(texture_path):
        from PIL import Image
        print(f"  >> Samplando textura {os.path.basename(texture_path)} em vertex colors...")
        try:
            tex = Image.open(texture_path).convert('RGB')
            tex_arr = np.asarray(tex)
            tex_h, tex_w = tex_arr.shape[:2]
            # UV em [0,1]: u=horizontal, v=vertical. PLY convention: v=0 no topo da textura
            uvs = original_uvs
            u_pix = np.clip((uvs[:, 0] * tex_w).astype(np.int32), 0, tex_w - 1)
            v_pix = np.clip(((1.0 - uvs[:, 1]) * tex_h).astype(np.int32), 0, tex_h - 1)
            rgb = tex_arr[v_pix, u_pix]
            # Construir colors RGBA (alpha=255)
            sampled_colors = np.column_stack([rgb, np.full(len(rgb), 255, dtype=np.uint8)])
            original_colors = sampled_colors
            mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=sampled_colors)
            print(f"     {len(rgb):,} vertices coloridos a partir da textura {tex.size}")
            # Limpar referencia a UVs (nao usaremos mais)
            original_uvs = None
            has_uv = False
        except Exception as e:
            print(f"     ERRO samplando textura: {e}")
            import traceback; traceback.print_exc()

    # Decima usando fast_simplification direto
    if no_decimate:
        print(f"  >> Modo HD: SEM decimacao (mantendo {len(mesh.faces):,} faces)")
    elif len(mesh.faces) > max_faces:
        target_reduction = 1.0 - (max_faces / len(mesh.faces))
        print(f"  Decimando: {len(mesh.faces):,} -> ~{max_faces:,} faces (reduction {target_reduction:.3f})...")
        try:
            import fast_simplification
            verts = np.asarray(mesh.vertices, dtype=np.float32)
            faces = np.asarray(mesh.faces, dtype=np.uint32)
            new_v, new_f = fast_simplification.simplify(verts, faces, target_reduction=target_reduction)

            # Mapear UV/cores por nearest-neighbor para os novos vertices
            new_uvs = None
            new_colors = None
            if original_uvs is not None or original_colors is not None:
                from scipy.spatial import cKDTree
                tree = cKDTree(original_vertices)
                _, idx = tree.query(new_v, k=1)
                if original_uvs is not None and len(original_uvs) == len(original_vertices):
                    new_uvs = original_uvs[idx]
                if original_colors is not None and len(original_colors) == len(original_vertices):
                    new_colors = original_colors[idx]

            # Reconstruir mesh
            mesh = trimesh.Trimesh(vertices=new_v, faces=new_f, process=False)
            if new_colors is not None:
                mesh.visual.vertex_colors = new_colors
                print(f"    Cores remapeadas: {new_colors.shape}")
            if new_uvs is not None:
                # Marca o mesh para receber TextureVisuals depois
                mesh._pending_uv = new_uvs
                print(f"    UVs remapeados: {new_uvs.shape}")
            print(f"  Apos decimacao: {len(mesh.vertices):,} v / {len(mesh.faces):,} f")
        except Exception as e:
            print(f"  Decimacao falhou: {e}")
            import traceback; traceback.print_exc()

    # Anexar textura se foi passada
    if texture_path and os.path.exists(texture_path):
        # Pega UV do pending_uv (apos decimacao) ou do visual original
        uv_to_use = getattr(mesh, '_pending_uv', None)
        if uv_to_use is None and hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None:
            uv_to_use = mesh.visual.uv
        if uv_to_use is None:
            print(f"  Sem UV disponivel - pulando textura")
        else:
            from PIL import Image
            try:
                tex = Image.open(texture_path)
                # Reduzir textura se muito grande (web)
                max_tex = 2048
                if tex.width > max_tex or tex.height > max_tex:
                    tex.thumbnail((max_tex, max_tex), Image.LANCZOS)
                    print(f"  Textura reduzida para {tex.size}")
                mat = trimesh.visual.material.SimpleMaterial(image=tex)
                mesh.visual = trimesh.visual.TextureVisuals(uv=uv_to_use, material=mat)
                print(f"  Textura aplicada: {os.path.basename(texture_path)} ({tex.size})")
            except Exception as e:
                print(f"  Erro aplicando textura: {e}")
                import traceback; traceback.print_exc()

    # Exportar como GLB (trimesh decide se usa Draco)
    out_glb = os.path.join(MODELS, out_name + ".glb")
    print(f"  Exportando GLB...")
    glb_bytes = mesh.export(file_type='glb')
    with open(out_glb, 'wb') as f:
        f.write(glb_bytes)
    print(f"  OK gravado: {out_glb}")
    print(f"  Tamanho final GLB: {os.path.getsize(out_glb)/1024/1024:.1f} MB")
    return out_glb

if __name__ == "__main__":
    base = r"D:\Jonathan China Toposcan PG - Proposta 05202667\B_Aerolevantamento_3D"

    igreja = sys.argv[1] if len(sys.argv) > 1 else "rosario"
    no_decimate = "--hd" in sys.argv or "--no-decimate" in sys.argv
    suffix = "_hd" if no_decimate else ""

    igrejas = {
        "rosario": {
            "ply": os.path.join(base, "02_Igreja Nossa Senhora do Rosario", "03_Mesh_3D", "Rosario.ply"),
            "tex": None,  # PLY tem cores nos vertices, sem JPG separado
            "out": "igreja_rosario",
        },
        "saojose": {
            "ply": os.path.join(base, "05_Igreja Sao Jose", "03_Mesh_3D", "Sao Jose mesh.ply"),
            "tex": os.path.join(base, "05_Igreja Sao Jose", "03_Mesh_3D", "Sao Jose mesh.jpg"),
            "out": "igreja_sao_jose",
        },
        "santarita": {
            "ply": os.path.join(base, "06_Igreja Santa Rita", "03_Mesh_3D", "Santa_Rita_mesh.ply"),
            "tex": os.path.join(base, "06_Igreja Santa Rita", "03_Mesh_3D", "Santa_Rita_mesh.jpg"),
            "out": "igreja_santa_rita",
        },
        "saude": {
            "ply": os.path.join(base, "07_Igreja Nossa Senhora da Saude", "03_Mesh_3D", "Senhora da Saude Mesh.ply"),
            "tex": os.path.join(base, "07_Igreja Nossa Senhora da Saude", "03_Mesh_3D", "Senhora da Saude Mesh.jpg"),
            "out": "igreja_saude",
        },
    }

    if igreja not in igrejas:
        print(f"Igrejas: {list(igrejas.keys())}")
        sys.exit(1)

    info = igrejas[igreja]
    convert(info["ply"], info["out"] + suffix, info.get("tex"), no_decimate=no_decimate)
