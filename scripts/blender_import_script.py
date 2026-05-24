"""
============================================================================
SCRIPT BLENDER - Torre Radar Banda C / SIMEPAR
Importa o modelo 3D no Blender com hierarquia organizada em Collections,
materiais por componente e câmera/luz pré-configuradas.

COMO USAR:
  1) Abra o Blender (qualquer 3.x ou 4.x)
  2) Janela "Scripting" (workspace) -> Open -> selecione este arquivo
  3) Clique "Run Script" (atalho Alt+P na area do editor)

  OU via linha de comando (se o blender.exe estiver acessivel):
     blender --background --python blender_import_script.py

O script:
  - Limpa a cena
  - Importa o .obj (na mesma pasta deste script)
  - Reorganiza objetos em Collections por componente
  - Aplica materiais coloridos (BSDF principled simplificado)
  - Adiciona camera + luz + fundo
  - Salva .blend ao lado
============================================================================
"""

import bpy
import os
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__)) if "__file__" in dir() else os.path.dirname(bpy.data.filepath) or os.getcwd()
OBJ_PATH = os.path.join(SCRIPT_DIR, "torre_radar_banda_c.obj")
BLEND_PATH = os.path.join(SCRIPT_DIR, "torre_radar_banda_c.blend")

# Mapeamento prefixo -> (nome colecao, material RGBA, roughness, metallic)
GROUP_MAP = {
    "01_fundacao":          ("01_Fundacao",          (0.70, 0.70, 0.70, 1.0), 0.85, 0.0),
    "02_torre_estrutura":   ("02_Torre_Estrutura",   (0.30, 0.30, 0.34, 1.0), 0.45, 0.8),
    "03_patamares":         ("03_Patamares",         (0.50, 0.50, 0.52, 1.0), 0.60, 0.4),
    "04_escadas":           ("04_Escadas",           (0.62, 0.62, 0.66, 1.0), 0.50, 0.5),
    "05_plataforma":        ("05_Plataforma",        (0.85, 0.83, 0.78, 1.0), 0.75, 0.0),
    "06_radome":            ("06_Radome",            (0.95, 0.95, 0.95, 1.0), 0.30, 0.0),
    "07_refletores":        ("07_Refletores",        (1.00, 0.92, 0.70, 1.0), 0.40, 0.0),
    "08_edificacao_terrea": ("08_Edificacao_Terrea", (0.88, 0.84, 0.74, 1.0), 0.80, 0.0),
}

KEYWORD_MAP = {
    "telhado":   ("Telhas",     (0.50, 0.30, 0.22, 1.0), 0.85, 0.0),
    "telha":     ("Telhas",     (0.50, 0.30, 0.22, 1.0), 0.85, 0.0),
    "guard":     ("Guardrails", (0.86, 0.75, 0.20, 1.0), 0.40, 0.6),
    "gc_":       ("Guardrails", (0.86, 0.75, 0.20, 1.0), 0.40, 0.6),
    "porta":     ("Esquadrias", (0.18, 0.32, 0.45, 1.0), 0.30, 0.4),
    "veneziana": ("Esquadrias", (0.18, 0.32, 0.45, 1.0), 0.30, 0.4),
    "caixa_dagua": ("Caixa_Agua", (0.25, 0.55, 0.75, 1.0), 0.40, 0.0),
    "agua":      ("Caixa_Agua", (0.25, 0.55, 0.75, 1.0), 0.40, 0.0),
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # remover collections antigas (exceto Scene Collection)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    # purge orphans
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def get_or_create_material(name, rgba, roughness, metallic):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = roughness
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
    return mat


def get_or_create_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def classify(obj_name):
    """Retorna (nome_collection, material_kwargs)."""
    n = obj_name.lower()
    for key, (cname, rgba, rough, met) in KEYWORD_MAP.items():
        if key in n:
            return cname, (cname, rgba, rough, met)
    for key, (cname, rgba, rough, met) in GROUP_MAP.items():
        if key in n:
            return cname, (cname, rgba, rough, met)
    return "Outros", ("Outros", (0.55, 0.55, 0.55, 1.0), 0.6, 0.0)


def import_obj():
    if not os.path.exists(OBJ_PATH):
        print(f"OBJ nao encontrado: {OBJ_PATH}")
        return []
    # Blender 4.x usa wm.obj_import; 3.x usa import_scene.obj
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=OBJ_PATH, forward_axis="Y", up_axis="Z")
    else:
        bpy.ops.import_scene.obj(filepath=OBJ_PATH, axis_forward="Y", axis_up="Z")
    return [o for o in bpy.context.selected_objects]


def organize_objects(objs):
    counts = {}
    for obj in objs:
        cname, mat_args = classify(obj.name)
        coll = get_or_create_collection(cname)
        # remover de qualquer collection antiga
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)
        # aplicar material
        mat = get_or_create_material(*mat_args)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        counts[cname] = counts.get(cname, 0) + 1
    return counts


def setup_camera_light():
    # Camera
    bpy.ops.object.camera_add(location=(20, -20, 18), rotation=(1.20, 0, 0.78))
    cam = bpy.context.object
    cam.name = "Camera_Perspectiva"
    bpy.context.scene.camera = cam
    # Sol
    bpy.ops.object.light_add(type="SUN", location=(10, -15, 30))
    sun = bpy.context.object
    sun.data.energy = 4.0
    sun.rotation_euler = (0.6, 0.4, 0.0)
    # fundo claro
    world = bpy.context.scene.world
    if world and world.use_nodes:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Color"].default_value = (0.85, 0.88, 0.93, 1.0)


def main():
    print("=" * 70)
    print("BLENDER IMPORT - Torre Radar Banda C / SIMEPAR")
    print("=" * 70)
    print(f"OBJ: {OBJ_PATH}")
    print(f"BLEND saida: {BLEND_PATH}")

    clear_scene()
    objs = import_obj()
    print(f"Objetos importados: {len(objs)}")
    counts = organize_objects(objs)
    print("Por coleção:")
    for c, n in sorted(counts.items()):
        print(f"  {c}: {n}")
    setup_camera_light()

    # Unidades em metros + escala
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    scn.unit_settings.length_unit = "METERS"

    # salvar
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"Salvo: {BLEND_PATH}")
    print("DONE")


if __name__ == "__main__":
    main()
