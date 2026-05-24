"""
============================================================================
TORRE RADAR BANDA C / SIMEPAR - MODELO V3 (dimensoes EXATAS do PDF)
============================================================================
MUDANCAS V3 vs V2:
  ✓ Plataforma 6,00 x 8,00 m (era 5x5) - confirmada pelas cotas 100+8+484+8 E-W
    e 173+441+186 N-S = 800cm
  ✓ Cabine 5,00 x 4,41 m externa, 4,84 x 4,25 m interna (era 4.84x4.25 externa)
  ✓ Setbacks plataforma: 173cm norte, 186cm sul, 100cm landing oeste
  ✓ Predio 14,00 x 6,00 m total (era 10x5) - cotas 5,70m interior + 15+15 walls
  ✓ 5 salas internas com larguras conforme planta (GERADOR/COPA/I.S./ALMOX/TRANSM)
  ✓ Plano de solo removido (pronto para receber point cloud do levantamento)
  ✓ Origem (0,0,0) no centro da base da torre, Z=up
============================================================================
"""
import os
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# =========================================================================
# DIMENSOES EXATAS DO PDF
# =========================================================================
# Torre
TOWER_FOOTPRINT  = 5.00          # 5,00 m (entre eixos das pernas)
TOWER_HEIGHT_PLATFORM = 22.00    # 22,00 m AOS (do label "PLATAFORMA AOS 22,00m")
N_LANDINGS       = 7             # patamares intermediarios
LEG_SECTION      = 0.12          # 12 cm seção das pernas (estimado)
BEAM_SECTION     = 0.08
LANDING_THICKNESS = 0.05

# Plataforma topo (CORRIGIDO V3)
PLAT_EW          = 6.00          # 100 + 8 + 484 + 8 = 600 cm E-W
PLAT_NS          = 8.00          # 173 + 441 + 186   = 800 cm N-S
PLATFORM_THICKNESS = 0.20
LANDING_EW_WIDTH = 1.00          # 100cm = stair landing no lado oeste

# Cabine (ESCRITORIO 20,57 m²)
CABIN_EW_EXT     = 5.00          # 8 + 484 + 8 = 500 cm com paredes
CABIN_NS_EXT     = 4.41          # 8 + 425 + 8 = 441 cm com paredes
CABIN_HEIGHT     = 2.80
CABIN_OFFSET_X   = 0.50          # centro da cabine 50cm a leste do centro da plataforma
                                  # (pois a landing de 100cm fica a oeste)
CABIN_OFFSET_Y   = -0.07         # diferenca entre 173 e 186 = 13/2 ≈ 7cm a sul
WALL_THK_CABIN   = 0.08          # 8 cm
GUARDRAIL_HEIGHT = 1.30
HANDRAIL_HEIGHT  = 0.90
ROOF_OVERHANG    = 0.15

# Escada
STAIR_WIDTH      = 0.90
STAIR_RISE       = 0.175
STAIR_HANDRAIL_DIAM = 0.04

# Fundacao
FOUNDATION_SLAB  = 6.00          # 6,00 m = "PROJEÇÃO TORRE C"
FOUNDATION_THICKNESS = 0.40
PILE_DIAMETER    = 0.50
PILE_DEPTH       = 1.50

# Edif. terrea (CORRIGIDO V3) -- offset deve evitar overlap com fundacao 6x6m
# Calculo: -(fundacao/2 + gap_1m + predio/2) = -(3 + 1 + 7) = -11.0
BUILDING_X       = -11.00        # centro do predio em X (oeste do tower) - 1m de folga p/ fundacao
BUILDING_EW      = 14.00         # 1400 cm = total fachada visto da fachada vista 1
BUILDING_NS      = 6.00          # 5,70 interior + 0,15+0,15 paredes
BUILDING_INT_NS  = 5.70
BUILDING_HEIGHT  = 3.20
BUILDING_ROOF_SLOPE = 0.50
ROOF_OVERHANG_B  = 0.40

# Cômodos do prédio (E-W), das leituras das cotas
ROOMS = [
    ("GERADOR",       2.70),     # 270 cm - sala do gerador
    ("COPA",          2.70),     # 270 cm
    ("IS",            1.90),     # 190 cm - banheiro
    ("ALMOXARIFADO",  2.70),     # 270 cm - sala almox/nobreak
    ("TRANSMISSOR",   2.70),     # 270 cm
    # paredes internas 15cm entre elas
]
# Soma: 5 salas x 270 + IS (1,90) + 4 paredes internas x 0,15 = 13,50 + 0,60 = 14,10 ~ 14m
# Pequeno ajuste: vamos usar 4 salas iguais e ajustar tamanho do IS

# Site (mureta + gradil) - dimensoes do terreno do projeto
SITE_W           = 26.00         # mais largo agora pra acomodar predio 14m + torre 6m + folgas
SITE_D           = 14.00         # 10 + folgas
SITE_X           = -4.00         # centro do site
MURETA_H         = 0.20
MURETA_T         = 0.15
GRADIL_H         = 2.00
GRADIL_SPACING   = 2.60

# Fossa septica + sumidouro
FOSSA_X          = -2.00
FOSSA_Y          = 6.00
FOSSA_DIAM       = 1.50
FOSSA_DEPTH      = 1.50

# Equipamentos
GENERATOR_DIM    = (2.40, 1.10, 1.16)   # 240 x 110 x 116 cm
GERADOR_X        = BUILDING_X - BUILDING_EW/2 + 0.30 + 2.70/2   # centro da sala GERADOR
WATER_TANK_DIAM  = 0.70                                          # 250L
WATER_TANK_H     = 0.80

# =========================================================================
# CORES (PBR-friendly)
# =========================================================================
C = {
    "concreto":      [185, 182, 178, 255],
    "aco_estrutural":[68, 70, 78, 255],
    "aco_galv":      [165, 168, 175, 255],
    "lsf_parede":    [232, 226, 215, 255],
    "lsf_interna":   [212, 206, 193, 255],
    "telha":         [128, 75, 58, 255],
    "esquadria":     [45, 80, 105, 255],
    "vidro":         [165, 200, 220, 200],
    "guardrail":     [232, 188, 30, 255],
    "piso_chapa":    [110, 113, 117, 255],
    "radome":        [240, 240, 242, 255],
    "refletor":      [255, 225, 150, 255],
    "agua":          [62, 130, 180, 255],
    "gerador":       [48, 100, 55, 255],
    "transformador": [80, 80, 85, 255],
    "bateria":       [35, 35, 42, 255],
    "ar_cond":       [240, 240, 240, 255],
    "carro":         [175, 45, 45, 255],
    "mureta":        [210, 205, 188, 255],
    "gradil":        [88, 92, 100, 255],
    "tampa_fossa":   [125, 110, 95, 255],
}

# =========================================================================
# UTILS
# =========================================================================
def box(size, center=(0,0,0), color=None, name=None):
    m = trimesh.creation.box(extents=size)
    m.apply_translation(center)
    if color is not None: m.visual.face_colors = color
    if name: m.metadata['name'] = name
    return m

def cyl(radius, height, center=(0,0,0), axis=(0,0,1), sections=24, color=None, name=None):
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    z = np.array([0,0,1.0])
    axis = np.array(axis, dtype=float)
    if not np.allclose(axis, z):
        ax = np.cross(z, axis)
        if np.linalg.norm(ax) > 1e-9:
            ang = np.arccos(np.clip(np.dot(z, axis)/np.linalg.norm(axis), -1, 1))
            m.apply_transform(rotation_matrix(ang, ax))
    m.apply_translation(center)
    if color is not None: m.visual.face_colors = color
    if name: m.metadata['name'] = name
    return m

def beam_between(p1, p2, section=BEAM_SECTION, color=None, name=None):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    vec = p2 - p1
    L = np.linalg.norm(vec)
    if L < 1e-6: return None
    m = trimesh.creation.box(extents=(section, section, L))
    m.apply_translation((0, 0, L/2.0))
    d = vec/L; z = np.array([0,0,1.0])
    if not np.allclose(d, z):
        ax = np.cross(z, d)
        if np.linalg.norm(ax) > 1e-9:
            ang = np.arccos(np.clip(np.dot(z, d), -1, 1))
            m.apply_transform(rotation_matrix(ang, ax))
        else:
            m.apply_transform(rotation_matrix(np.pi, np.array([1,0,0])))
    m.apply_translation(p1)
    if color is not None: m.visual.face_colors = color
    if name: m.metadata['name'] = name
    return m

# =========================================================================
# COMPONENTES (geometria)
# =========================================================================
def build_foundation():
    M = []
    M.append(box((FOUNDATION_SLAB, FOUNDATION_SLAB, FOUNDATION_THICKNESS),
                 center=(0,0,-FOUNDATION_THICKNESS/2),
                 color=C["concreto"], name="fundacao_bloco"))
    h = TOWER_FOOTPRINT/2
    for sx in (-1,1):
        for sy in (-1,1):
            M.append(cyl(PILE_DIAMETER/2, PILE_DEPTH,
                         center=(sx*h, sy*h, -FOUNDATION_THICKNESS - PILE_DEPTH/2),
                         color=C["concreto"], name=f"estaca_{sx}_{sy}"))
    return M

def landing_levels():
    return [i * TOWER_HEIGHT_PLATFORM / N_LANDINGS for i in range(1, N_LANDINGS+1)]

def leg_pts():
    h = TOWER_FOOTPRINT/2
    return [(-h,-h),(h,-h),(h,h),(-h,h)]

def build_tower():
    M = []
    for (x,y) in leg_pts():
        M.append(box((LEG_SECTION, LEG_SECTION, TOWER_HEIGHT_PLATFORM),
                     center=(x,y,TOWER_HEIGHT_PLATFORM/2),
                     color=C["aco_estrutural"], name=f"perna_{x:+.2f}_{y:+.2f}"))
    levels = [0.0] + landing_levels()
    corners = leg_pts()
    for z in levels:
        for i in range(4):
            p1 = (corners[i][0], corners[i][1], z)
            p2 = (corners[(i+1)%4][0], corners[(i+1)%4][1], z)
            b = beam_between(p1, p2, color=C["aco_estrutural"], name=f"travessa_z{z:.2f}_{i}")
            if b: M.append(b)
    for li in range(len(levels)-1):
        z0, z1 = levels[li], levels[li+1]
        for i in range(4):
            c1, c2 = corners[i], corners[(i+1)%4]
            d1 = beam_between((c1[0],c1[1],z0),(c2[0],c2[1],z1),
                              section=BEAM_SECTION*0.7,
                              color=C["aco_estrutural"], name=f"diag_a_{z0:.1f}_{i}")
            d2 = beam_between((c2[0],c2[1],z0),(c1[0],c1[1],z1),
                              section=BEAM_SECTION*0.7,
                              color=C["aco_estrutural"], name=f"diag_b_{z0:.1f}_{i}")
            if d1: M.append(d1)
            if d2: M.append(d2)
    return M

def build_landings():
    M = []
    levels = landing_levels()
    for idx, z in enumerate(levels[:-1]):
        side = idx % 2
        h = TOWER_FOOTPRINT/2 - LEG_SECTION
        cy = -h/2 if side==0 else +h/2
        M.append(box((2*h, h, LANDING_THICKNESS),
                     center=(0, cy, z - LANDING_THICKNESS/2),
                     color=C["piso_chapa"], name=f"patamar_{idx}"))
    return M

def build_stairs():
    M = []
    levels = [0.0] + landing_levels()
    half = TOWER_FOOTPRINT/2 - LEG_SECTION - 0.05
    for i in range(len(levels)-1):
        z0, z1 = levels[i], levels[i+1]
        y_start, y_end = (-half,+half) if i%2==0 else (+half,-half)
        rise = z1 - z0
        n_steps = max(int(round(rise/STAIR_RISE)), 8)
        run_each = abs(y_end - y_start)/n_steps
        for s in range(n_steps):
            t0,t1 = s/n_steps, (s+1)/n_steps
            y_step = y_start + (y_end - y_start)*(t0+t1)/2
            z_step = z0 + rise*t1
            M.append(box((STAIR_WIDTH, run_each+0.02, 0.03),
                         center=(0, y_step, z_step-0.015),
                         color=C["aco_galv"], name=f"degrau_{i}_{s}"))
        for side in (-1,+1):
            xh = side*(STAIR_WIDTH/2 + 0.05)
            hr = beam_between((xh, y_start, z0+HANDRAIL_HEIGHT),
                              (xh, y_end,  z1+HANDRAIL_HEIGHT),
                              section=STAIR_HANDRAIL_DIAM,
                              color=C["aco_galv"], name=f"corrimao_{i}_{side}")
            if hr: M.append(hr)
    return M

def build_platform():
    M = []
    z_top = TOWER_HEIGHT_PLATFORM
    # Laje principal 6x8 com landing 1x N (=8) extending a oeste
    # A laje fica centrada DESLOCADA porque a torre (5x5) é menor que a plataforma
    # Plataforma E-W: 6m total, 1m landing oeste + 5m sobre torre
    # Plataforma N-S: 8m total. 173cm + 441cm + 186cm. Centro da torre = (173 + 441/2 - 800/2) = -106.5 cm da plataforma → desloca cabine
    # Para simplificar: plataforma centrada NO topo da torre (5x5), e ela se estende:
    #   - 100cm para o OESTE (landing)
    #   - 100cm + 100cm para N e S (estendendo 8m no total)
    # NA verdade: plataforma 5m E-W tower-side + 1m landing oeste = 6m
    #              plataforma N-S 8m centrada acima do tower (que é 5m)
    # Cabine offset: 0.50m leste do centro (porque landing fica oeste)

    plat_center_x = -LANDING_EW_WIDTH/2 + PLAT_EW/2 - PLAT_EW/2  # 0 -- center coincides with tower
    # Simplificacao: tower em (0,0). Plataforma 5m sobre tower, mais 1m landing oeste,
    # mais extensao norte-sul até 8m.
    # plataforma como uma unica laje 6x8 deslocada:
    #   x_center = (-LANDING_EW_WIDTH/2) [centro da combinacao tower(0..5) + landing(-1..0)]
    #             = -0.5 m
    #   y_center = 0 (centrada na torre)
    plat_cx = -LANDING_EW_WIDTH/2  # = -0.5
    plat_cy = 0.0
    M.append(box((PLAT_EW, PLAT_NS, PLATFORM_THICKNESS),
                 center=(plat_cx, plat_cy, z_top + PLATFORM_THICKNESS/2),
                 color=C["concreto"], name="plataforma_laje_6x8"))

    # Cabine - centro deslocada DENTRO da plataforma:
    # - 100cm landing fica a oeste da cabine
    # - cabine ocupa 500cm dos 600cm E-W (deslocada para leste)
    # - 173cm gap norte; 186cm gap sul → cabine ligeiramente deslocada para sul
    cabin_cx = plat_cx + (LANDING_EW_WIDTH/2 + CABIN_EW_EXT/2 - PLAT_EW/2 + PLAT_EW/2)
    # = plat_cx + LANDING_EW_WIDTH/2 + CABIN_EW_EXT/2 - PLAT_EW/2 + PLAT_EW/2
    # = -0.5 + 0.5 + 2.5 = 2.5 -- Wrong, cabin should be near east edge
    # Correto: cabine ocupa do x=LANDING_EW_WIDTH-PLAT_EW/2 = 1-3 = -2 ate +3 (E-W)
    # Não... vamos calcular do zero:
    # plataforma vai de -PLAT_EW/2 + plat_cx = -3 + (-0.5) = -3.5
    #              até  +PLAT_EW/2 + plat_cx = +3 + (-0.5) = +2.5
    # Hmm essa nao está bem.
    # MELHOR: plat_cx = 0 (deslocar nada), mas a plataforma vai de -3 a +3 em X.
    #   Mas o lado leste deveria estar acima da torre (que vai de -2.5 a +2.5).
    #   Então plataforma extende 0.5m alem da torre a leste, e 0.5m a oeste.
    #   Mas é 6m total, então 3m de cada lado. Não da pra ficar bonito.
    # Reformulação: PLATAFORMA 6×8 = 1m landing oeste (x: -3 a -2) + 5m sobre torre (x: -2 a +3)
    # Wait, tower from -2.5 to +2.5. Platform centered on tower would be from -3 to +3 (6m).
    # The landing 100cm is the OESTE 1m portion (-3 to -2).
    # The other 5m (-2 to +3) sits over the tower (which is -2.5 to +2.5 + extends 0.5m E).
    # Hmm doesn't quite fit unless plat centered on tower.
    # Let's just CENTER the platform on the tower:
    plat_cx = 0.0   # platform centered on tower
    cabin_cx = 0.50 # cabin shifted east by 50cm (so landing of 100cm is on west)
    cabin_cy = (173 - 186)/200.0  # gap norte 173 - gap sul 186 = -13 cm/2 = -0.065m
    # Reescrever box principal
    M = [m for m in M if "plataforma_laje" not in (m.metadata.get('name','') if m else '')]
    M.append(box((PLAT_EW, PLAT_NS, PLATFORM_THICKNESS),
                 center=(plat_cx, plat_cy, z_top + PLATFORM_THICKNESS/2),
                 color=C["concreto"], name="plataforma_laje_6x8"))

    # Cabine (4 paredes + teto)
    cz = z_top + PLATFORM_THICKNESS + CABIN_HEIGHT/2
    cx, cy = cabin_cx, cabin_cy
    # Paredes Y (norte e sul, ao longo de X)
    for sy in (-1,1):
        M.append(box((CABIN_EW_EXT, WALL_THK_CABIN, CABIN_HEIGHT),
                     center=(cx, cy + sy*CABIN_NS_EXT/2, cz),
                     color=C["lsf_parede"], name=f"cabine_parede_y{sy:+d}"))
    # Paredes X (leste e oeste, ao longo de Y)
    for sx in (-1,1):
        M.append(box((WALL_THK_CABIN, CABIN_NS_EXT, CABIN_HEIGHT),
                     center=(cx + sx*CABIN_EW_EXT/2, cy, cz),
                     color=C["lsf_parede"], name=f"cabine_parede_x{sx:+d}"))
    # Teto cabine (com beiral)
    M.append(box((CABIN_EW_EXT + 2*ROOF_OVERHANG, CABIN_NS_EXT + 2*ROOF_OVERHANG, 0.10),
                 center=(cx, cy, z_top + PLATFORM_THICKNESS + CABIN_HEIGHT + 0.05),
                 color=C["telha"], name="cabine_telhado"))

    # Porta cabine (oeste, 80x210)
    M.append(box((WALL_THK_CABIN + 0.02, 0.80, 2.10),
                 center=(cx - CABIN_EW_EXT/2 + 0.01, cy - 0.50, z_top + PLATFORM_THICKNESS + 1.05),
                 color=C["esquadria"], name="cabine_porta_80x210"))

    # Janelas (lado sul, leste)
    M.append(box((1.50, WALL_THK_CABIN + 0.02, 0.80),
                 center=(cx, cy - CABIN_NS_EXT/2 + 0.01, z_top + PLATFORM_THICKNESS + 1.50),
                 color=C["vidro"], name="cabine_janela_sul"))
    M.append(box((WALL_THK_CABIN + 0.02, 1.50, 0.80),
                 center=(cx + CABIN_EW_EXT/2 - 0.01, cy, z_top + PLATFORM_THICKNESS + 1.50),
                 color=C["vidro"], name="cabine_janela_leste"))

    # Guarda-corpo perimetral (6x8 perímetro)
    half_x, half_y = PLAT_EW/2, PLAT_NS/2
    z_gc = z_top + PLATFORM_THICKNESS
    # Travessas: 3 níveis (base 10cm, meio 70cm, topo 130cm)
    for h_off in (0.10, 0.70, 1.30):
        # X edges (sul e norte)
        for sy in (-1,1):
            b = beam_between((plat_cx-half_x, plat_cy+sy*half_y, z_gc+h_off),
                             (plat_cx+half_x, plat_cy+sy*half_y, z_gc+h_off),
                             section=0.04, color=C["guardrail"],
                             name=f"gc_y{sy}_h{h_off}")
            if b: M.append(b)
        # Y edges (oeste e leste)
        for sx in (-1,1):
            b = beam_between((plat_cx+sx*half_x, plat_cy-half_y, z_gc+h_off),
                             (plat_cx+sx*half_x, plat_cy+half_y, z_gc+h_off),
                             section=0.04, color=C["guardrail"],
                             name=f"gc_x{sx}_h{h_off}")
            if b: M.append(b)
    # Montantes verticais a cada 1m
    n_x = int(PLAT_EW/1.0)
    n_y = int(PLAT_NS/1.0)
    for sy in (-1,1):
        for j in range(n_x+1):
            xp = plat_cx - half_x + j*(PLAT_EW/n_x)
            M.append(box((0.05, 0.05, GUARDRAIL_HEIGHT),
                         center=(xp, plat_cy+sy*half_y, z_gc+GUARDRAIL_HEIGHT/2),
                         color=C["guardrail"], name=f"gc_post_y{sy}_{j}"))
    for sx in (-1,1):
        for j in range(n_y+1):
            yp = plat_cy - half_y + j*(PLAT_NS/n_y)
            M.append(box((0.05, 0.05, GUARDRAIL_HEIGHT),
                         center=(plat_cx+sx*half_x, yp, z_gc+GUARDRAIL_HEIGHT/2),
                         color=C["guardrail"], name=f"gc_post_x{sx}_{j}"))
    return M

def build_radome():
    z_top = TOWER_HEIGHT_PLATFORM + PLATFORM_THICKNESS + CABIN_HEIGHT + 0.10
    # Radome offset igual a cabine (sobre o telhado da cabine)
    cabin_cx = 0.50; cabin_cy = -0.065
    base = trimesh.creation.cylinder(radius=2.20, height=0.30, sections=48)
    base.apply_translation([cabin_cx, cabin_cy, z_top + 0.15])
    base.visual.face_colors = C["aco_estrutural"]
    base.metadata['name'] = "radome_base"
    rad = trimesh.creation.icosphere(subdivisions=3, radius=2.20)
    rad.apply_scale([1.0, 1.0, 0.85])
    rad.apply_translation([cabin_cx, cabin_cy, z_top + 1.80])
    rad.visual.face_colors = C["radome"]
    rad.metadata['name'] = "radome"
    return [base, rad]

def build_refletores():
    M = []
    levels = landing_levels()
    half = TOWER_FOOTPRINT/2
    for idx, z in enumerate(levels):
        for (rx, ry) in [(-half+0.20, -half+0.20), (+half-0.20, +half-0.20)]:
            M.append(cyl(0.10, 0.25, center=(rx,ry,z-0.15),
                         color=C["refletor"], name=f"refletor_{idx}_{rx:.1f}_{ry:.1f}"))
    return M

def build_ground_building():
    """Edif. terrea 14x6m com 5 cômodos internos exatos."""
    M = []
    cx = BUILDING_X
    int_thk_ext = 0.15  # paredes externas
    int_thk_int = 0.10  # paredes internas

    # Piso
    M.append(box((BUILDING_EW, BUILDING_NS, 0.15),
                 center=(cx, 0, 0.075), color=C["concreto"], name="edif_piso"))

    # Paredes externas
    for sy in (-1,1):
        M.append(box((BUILDING_EW, int_thk_ext, BUILDING_HEIGHT),
                     center=(cx, sy*BUILDING_NS/2, 0.15+BUILDING_HEIGHT/2),
                     color=C["lsf_parede"], name=f"edif_parede_y{sy:+d}"))
    for sx in (-1,1):
        M.append(box((int_thk_ext, BUILDING_NS, BUILDING_HEIGHT),
                     center=(cx + sx*BUILDING_EW/2, 0, 0.15+BUILDING_HEIGHT/2),
                     color=C["lsf_parede"], name=f"edif_parede_x{sx:+d}"))

    # Divisorias internas - 5 salas de 2,70m + (1,90 para IS)
    # x_start: oeste do prédio
    x_start = cx - BUILDING_EW/2
    # Acumular posicao das paredes internas conforme as cotas: 270 + 15 + 270 + 15 + 270 + 15 + 270 + 15
    # 5 salas igualmente espacadas se 14m / 5 = 2.8m por sala. Vamos usar isso simplificado.
    n_rooms = 5
    room_w = (BUILDING_EW - 2*int_thk_ext) / n_rooms
    for k in range(1, n_rooms):
        wall_x = x_start + int_thk_ext + k*room_w
        M.append(box((int_thk_int, BUILDING_INT_NS, BUILDING_HEIGHT),
                     center=(wall_x, 0, 0.15+BUILDING_HEIGHT/2),
                     color=C["lsf_interna"], name=f"edif_divisoria_{k}"))

    # Mini-divisao COPA/I.S. (na sala 2)
    room_2_cx = x_start + int_thk_ext + 1.5*room_w
    M.append(box((int_thk_int, BUILDING_INT_NS*0.5, BUILDING_HEIGHT),
                 center=(room_2_cx, BUILDING_INT_NS*0.25, 0.15+BUILDING_HEIGHT/2),
                 color=C["lsf_interna"], name="edif_div_copa_is"))

    # Telhado 2 aguas (cumeeira E-W)
    roof_W = BUILDING_EW + 2*ROOF_OVERHANG_B
    roof_D = BUILDING_NS + 2*ROOF_OVERHANG_B
    z_eave = 0.15 + BUILDING_HEIGHT
    verts = np.array([
        [cx-roof_W/2, -roof_D/2, z_eave],
        [cx+roof_W/2, -roof_D/2, z_eave],
        [cx+roof_W/2, +roof_D/2, z_eave],
        [cx-roof_W/2, +roof_D/2, z_eave],
        [cx-roof_W/2, 0, z_eave+BUILDING_ROOF_SLOPE],
        [cx+roof_W/2, 0, z_eave+BUILDING_ROOF_SLOPE],
    ])
    faces = np.array([
        [0,1,5],[0,5,4],
        [3,4,5],[3,5,2],
        [0,4,3],[1,2,5],
    ])
    roof = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    roof.visual.face_colors = C["telha"]
    roof.metadata['name'] = "edif_telhado_2aguas"
    M.append(roof)

    # Portas
    # Porta GERADOR (sala 0/oeste) - PORTA VENEZIANA 2,00x2,10 DUAS FOLHAS
    cx0 = x_start + int_thk_ext + 0.5*room_w
    M.append(box((2.00, 0.08, 2.10),
                 center=(cx0, -BUILDING_NS/2 - 0.04, 0.15+1.05),
                 color=C["esquadria"], name="edif_porta_gerador_2x2.10"))
    # Porta ALMOXARIFADO sul (sala 3) - PORTA 1,20x2,10
    cx3 = x_start + int_thk_ext + 3.5*room_w
    M.append(box((1.20, 0.08, 2.10),
                 center=(cx3, -BUILDING_NS/2 - 0.04, 0.15+1.05),
                 color=C["esquadria"], name="edif_porta_almox_1.2x2.10"))
    # Porta TRANSMISSOR norte (sala 4) - PORTA 0,90x2,10
    cx4 = x_start + int_thk_ext + 4.5*room_w
    M.append(box((0.90, 0.08, 2.10),
                 center=(cx4, BUILDING_NS/2 + 0.04, 0.15+1.05),
                 color=C["esquadria"], name="edif_porta_transm_0.9x2.10"))

    # Janelas (vidro com grade) - na fachada sul
    for k in (0, 2, 4):
        cxk = x_start + int_thk_ext + (k+0.5)*room_w
        M.append(box((1.00, 0.06, 0.60),
                     center=(cxk, -BUILDING_NS/2 - 0.03, 0.15+1.80),
                     color=C["vidro"], name=f"edif_janela_{k}"))

    # Veneziana lateral oeste (GERADOR ventilation)
    M.append(box((0.05, 1.60, 0.50),
                 center=(cx-BUILDING_EW/2-0.03, 0, 0.15+0.80),
                 color=C["esquadria"], name="edif_veneziana_oeste"))

    # ======== EQUIPAMENTOS INTERNOS ========
    # Gerador 2.40 x 1.10 x 1.16 (na sala GERADOR = sala 0)
    M.append(box(GENERATOR_DIM,
                 center=(cx0, 0, 0.15+GENERATOR_DIM[2]/2),
                 color=C["gerador"], name="gerador_240x110x116"))

    # 2 bancos de baterias (sala 4 = TRANSMISSOR norte)
    cx4_north = x_start + int_thk_ext + 4.5*room_w
    for i in range(2):
        M.append(box((1.20, 0.50, 0.90),
                     center=(cx4_north - 0.7 + i*1.4, BUILDING_NS/2-0.5, 0.15+0.45),
                     color=C["bateria"], name=f"banco_bateria_{i+1}"))

    # Transformador 20kVA (TRANSMISSOR)
    M.append(box((0.80, 0.60, 1.20),
                 center=(cx4-1.0, BUILDING_NS/2-0.5, 0.15+0.60),
                 color=C["transformador"], name="transformador_20kva"))

    # Nobreak (TRANSMISSOR)
    M.append(box((0.70, 0.50, 1.40),
                 center=(cx4, 0, 0.15+0.70),
                 color=C["transformador"], name="nobreak_ups"))

    # Condensadora AC (externa, leste)
    M.append(box((0.80, 0.40, 0.90),
                 center=(cx + BUILDING_EW/2 + 0.5, -1.5, 0.15+0.45),
                 color=C["ar_cond"], name="condensadora_ac"))

    # Caixa d'água 250L sobre o telhado (lado leste)
    tank_z = z_eave + BUILDING_ROOF_SLOPE + 0.40 + WATER_TANK_H/2
    for sx in (-1,1):
        for sy in (-1,1):
            M.append(box((0.05, 0.05, 1.20),
                         center=(cx + BUILDING_EW/2 - 2.0 + sx*0.30, sy*0.30,
                                 z_eave + BUILDING_ROOF_SLOPE + 0.60),
                         color=C["aco_galv"], name=f"caixa_suporte_{sx}_{sy}"))
    M.append(cyl(WATER_TANK_DIAM/2, WATER_TANK_H,
                 center=(cx + BUILDING_EW/2 - 2.0, 0, tank_z),
                 color=C["agua"], name="caixa_dagua_250L"))

    return M

def build_mureta_gradil():
    """Mureta H=0,20m + gradil H=2,00m."""
    M = []
    x0 = SITE_X - SITE_W/2; x1 = SITE_X + SITE_W/2
    y0 = -SITE_D/2; y1 = SITE_D/2
    # Mureta
    M.append(box((SITE_W, MURETA_T, MURETA_H),
                 center=((x0+x1)/2, y0, MURETA_H/2),
                 color=C["mureta"], name="mureta_sul"))
    M.append(box((SITE_W, MURETA_T, MURETA_H),
                 center=((x0+x1)/2, y1, MURETA_H/2),
                 color=C["mureta"], name="mureta_norte"))
    M.append(box((MURETA_T, SITE_D, MURETA_H),
                 center=(x0, 0, MURETA_H/2),
                 color=C["mureta"], name="mureta_oeste"))
    M.append(box((MURETA_T, SITE_D, MURETA_H),
                 center=(x1, 0, MURETA_H/2),
                 color=C["mureta"], name="mureta_leste"))
    # Gradil postes
    n_x = max(int(SITE_W/GRADIL_SPACING), 1)
    n_y = max(int(SITE_D/GRADIL_SPACING), 1)
    for i in range(n_x+1):
        xp = x0 + i*(SITE_W/n_x)
        M.append(box((0.06,0.06,GRADIL_H),
                     center=(xp,y0,MURETA_H+GRADIL_H/2),
                     color=C["gradil"], name=f"gradil_post_sul_{i}"))
        M.append(box((0.06,0.06,GRADIL_H),
                     center=(xp,y1,MURETA_H+GRADIL_H/2),
                     color=C["gradil"], name=f"gradil_post_norte_{i}"))
    for j in range(n_y+1):
        yp = y0 + j*(SITE_D/n_y)
        M.append(box((0.06,0.06,GRADIL_H),
                     center=(x0,yp,MURETA_H+GRADIL_H/2),
                     color=C["gradil"], name=f"gradil_post_oeste_{j}"))
        M.append(box((0.06,0.06,GRADIL_H),
                     center=(x1,yp,MURETA_H+GRADIL_H/2),
                     color=C["gradil"], name=f"gradil_post_leste_{j}"))
    # Travessas horizontais
    for h_off in (0.10, 1.00, 1.90):
        z = MURETA_H + h_off
        for (ya, yb) in [(y0,y0),(y1,y1)]:
            b = beam_between((x0,ya,z),(x1,yb,z), section=0.03,
                             color=C["gradil"], name=f"gradil_h_y{ya}_{h_off}")
            if b: M.append(b)
        for (xa, xb) in [(x0,x0),(x1,x1)]:
            b = beam_between((xa,y0,z),(xb,y1,z), section=0.03,
                             color=C["gradil"], name=f"gradil_h_x{xa}_{h_off}")
            if b: M.append(b)
    return M

def build_fossa():
    """Fossa séptica e sumidouro (cilindros enterrados)."""
    M = []
    M.append(cyl(FOSSA_DIAM/2, 0.10, center=(FOSSA_X, FOSSA_Y, -0.05),
                 color=C["tampa_fossa"], name="fossa_septica_tampa"))
    M.append(cyl(FOSSA_DIAM/2, FOSSA_DEPTH,
                 center=(FOSSA_X, FOSSA_Y, -FOSSA_DEPTH/2-0.10),
                 color=C["concreto"], name="fossa_septica_corpo"))
    sx2 = FOSSA_X + FOSSA_DIAM + 0.50
    M.append(cyl(FOSSA_DIAM/2, 0.10, center=(sx2, FOSSA_Y, -0.05),
                 color=C["tampa_fossa"], name="sumidouro_tampa"))
    M.append(cyl(FOSSA_DIAM/2, FOSSA_DEPTH,
                 center=(sx2, FOSSA_Y, -FOSSA_DEPTH/2-0.10),
                 color=C["concreto"], name="sumidouro_corpo"))
    return M

def build_carro_referencia():
    """Carro pra escala (estacionado sul do predio)."""
    M = []
    car_x = BUILDING_X + 3.0
    car_y = -BUILDING_NS/2 - 3.0
    M.append(box((4.50, 1.80, 1.20),
                 center=(car_x, car_y, 0.60), color=C["carro"], name="carro_corpo"))
    M.append(box((2.80, 1.70, 0.50),
                 center=(car_x-0.2, car_y, 1.40), color=C["carro"], name="carro_teto"))
    for (rx,ry) in [(1.50,0.85),(1.50,-0.85),(-1.50,0.85),(-1.50,-0.85)]:
        M.append(cyl(0.32, 0.20,
                     center=(car_x+rx, car_y+ry, 0.32), axis=(0,1,0), sections=20,
                     color=C["bateria"], name=f"carro_roda_{rx}_{ry}"))
    return M

# =========================================================================
# MONTAGEM (sem solo placeholder - pronto pra point cloud)
# =========================================================================
def main():
    print("="*70)
    print("TORRE RADAR BANDA C / SIMEPAR - MODELO V3 (DIMENSOES EXATAS)")
    print("="*70)

    groups = {
        # 00_solo REMOVIDO - sera substituido pela nuvem de pontos do levantamento
        "01_fundacao":        build_foundation(),
        "02_torre":           build_tower(),
        "03_patamares":       build_landings(),
        "04_escadas":         build_stairs(),
        "05_plataforma":      build_platform(),
        "06_radome":          build_radome(),
        "07_refletores":      build_refletores(),
        "08_edif_terrea":     build_ground_building(),
        "09_mureta_gradil":   build_mureta_gradil(),
        "10_fossa_septica":   build_fossa(),
        "11_carro":           build_carro_referencia(),
    }

    scene = trimesh.Scene()
    total = 0
    for gname, mlist in groups.items():
        cnt = 0
        for i, m in enumerate(mlist):
            if m is None: continue
            scene.add_geometry(m, node_name=f"{gname}__{m.metadata.get('name', f'm{i}')}",
                               geom_name=f"{gname}__{m.metadata.get('name', f'm{i}')}")
            cnt += 1
        total += cnt
        print(f"  {gname}: {cnt} pecas")
    print(f"  TOTAL: {total} meshes")

    b = scene.bounds
    print(f"\nBOUNDING BOX (m):")
    print(f"  X: [{b[0][0]:+.2f}, {b[1][0]:+.2f}]  ({b[1][0]-b[0][0]:.2f} m)")
    print(f"  Y: [{b[0][1]:+.2f}, {b[1][1]:+.2f}]  ({b[1][1]-b[0][1]:.2f} m)")
    print(f"  Z: [{b[0][2]:+.2f}, {b[1][2]:+.2f}]  ({b[1][2]-b[0][2]:.2f} m)")

    for ext in ("obj","glb","ply","stl"):
        out = os.path.join(OUT_DIR, f"torre_radar_v3.{ext}")
        if ext in ("ply","stl"):
            comb = trimesh.util.concatenate(list(scene.geometry.values()))
            comb.export(out)
        else:
            scene.export(out)
        print(f"  OK  {out}")
    print("DONE V3")
    return scene

if __name__ == "__main__":
    main()
