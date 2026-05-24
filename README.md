# 🗼 TopoScan · Visualizador 3D — Torre Radar Banda C / SIMEPAR

> Visualizador 3D web interativo para projetos arquitetônicos integrados com nuvem de pontos de levantamento topográfico.
> Novo produto **TopoScan**.

[**🌐 Demo online**](https://toposcansend-cmyk.github.io/toposcan-3d-viewer/) · [**📊 Modelo V3**](models/torre_radar_v3.glb) · [**📐 PDF fonte**](#)

---

## 🎯 O que é

Sistema completo de **modelagem 3D paramétrica + visualização web** para projetos de engenharia que precisam ser integrados ao MDT (Modelo Digital de Terreno) de levantamentos topográficos.

Primeiro caso de uso: **Torre Radar Meteorológico Banda C — SIMEPAR**. Modelo 3D reconstruído com fidelidade do PDF arquitetônico oficial, pronto para sobrepor à nuvem de pontos do levantamento Toposcan.

## ✨ Funcionalidades

### Visualizador web
- 🎨 **Design profissional** com tema escuro/claro
- 🌍 **Toggle Torre × Cena Completa** (com terreno)
- 📷 **6 vistas pré-definidas** (Perspectiva, Frontal, Lateral, Topo, Close Topo, Close Base)
- 🔄 **Auto-rotação**, **screenshot em PNG**, **zoom**, **reset**
- 🧭 **Bússola dinâmica** rotaciona junto com a câmera
- 📏 **Scale bar** e indicadores de medida
- ⌨️ **13 atalhos de teclado** completos
- 📱 **Responsivo** — funciona em mobile/tablet
- 🚀 **Onboarding** interativo na primeira visita
- 💾 **Downloads diretos** em GLB / OBJ / PLY / STL

### Modelo 3D
- **401 peças** individuais com dimensões exatas do PDF
- **15 grupos** de componentes (fundação, torre, escadas, plataforma, cabine, radome, edif. térrea, equipamentos, mureta, gradil, fossa séptica, refletores)
- Origem `(0, 0, 0)` no centro da base — pronto para translação UTM
- Unidades em **metros**, padrão GIS/CAD/MDT

### Pipeline de integração com nuvem de pontos
- Aceita formatos: `.las`, `.laz`, `.ply`, `.xyz`, `.pcd`, `.e57`
- Translada o modelo para coordenada UTM do levantamento
- Renderiza cena combinada (terreno + estrutura)
- Exporta GLB unificado
- **Em breve**: streaming Potree para nuvens até **5 GB+** sem travar o browser

---

## 📐 Especificações do modelo (Torre Radar Banda C)

| Elemento | Dimensão |
|---|---|
| Altura plataforma (AOS) | **22,00 m** |
| Torre footprint | 5,00 × 5,00 m |
| Fundação concreto | 6,00 × 6,00 m |
| Plataforma topo | 6,00 × 8,00 m |
| Cabine escritório | 4,84 × 4,25 m (20,57 m²) |
| Pé-direito cabine | 2,80 m |
| Guarda-corpo plataforma | 1,30 m |
| Corrimão escada | 0,90 m |
| Patamares intermediários | 7 níveis |
| Edif. térrea LSF | 14,00 × 6,00 m |
| Pé-direito edif. | 3,20 m |
| Mureta de contenção | 0,20 m |
| Gradil perimetral | 2,00 m |
| Site total (com mureta) | 26 × 14 m |
| Altura total c/ radome | 28,77 m |

---

## 🚀 Como usar

### 1. Visualizar online (mais simples)

Abra: **https://toposcansend-cmyk.github.io/toposcan-3d-viewer/**

Tudo funciona no browser, sem instalação.

### 2. Rodar localmente

```bash
git clone https://github.com/toposcansend-cmyk/toposcan-3d-viewer.git
cd toposcan-3d-viewer
python -m http.server 8765
# Abrir http://localhost:8765/
```

### 3. Regerar o modelo (paramétrico)

```bash
pip install trimesh numpy pillow pyvista laspy
python scripts/build_torre_v3.py
```

### 4. Integrar com sua nuvem de pontos

```bash
# Modo simples (centro da nuvem)
python scripts/implantar_torre_no_terreno.py --cloud "seu_levantamento.las"

# Modo georreferenciado (UTM)
python scripts/implantar_torre_no_terreno.py \
  --cloud "seu_levantamento.las" \
  --easting 7180000 --northing 423500 --elev 920
```

---

## 🏗️ Estrutura do repo

```
toposcan-3d-viewer/
├── index.html              # Visualizador principal (GitHub Pages serve daqui)
├── assets/                 # Logos, CSS, JS
├── models/
│   ├── torre_radar_v3.glb  # Modelo principal (286 KB)
│   ├── torre_radar_v3.obj  # Formato universal
│   ├── torre_radar_v3.ply  # GIS / point cloud
│   ├── torre_radar_v3.stl  # Impressão 3D
│   └── demo/               # Cena demo com terreno sintético
├── scripts/                # Pipeline Python
│   ├── build_torre_v3.py             # Gera modelo (paramétrico)
│   ├── implantar_torre_no_terreno.py # Integra com nuvem
│   ├── render_pyvista.py             # Renders profissionais
│   └── blender_import_script.py      # Bônus: abrir no Blender
├── renders/                # Renders PNG de alta qualidade
├── docs/
│   ├── architecture.md     # Arquitetura técnica
│   └── 5gb-cloud-strategy.md  # Como escalar para 5 GB+
└── README.md
```

---

## 🛠️ Stack técnico

| Camada | Tecnologia |
|---|---|
| Modelagem 3D | Python · trimesh · numpy |
| Rendering programático | pyvista · VTK |
| Visualizador web | Google `<model-viewer>` 3.5 · Three.js |
| Hosting | GitHub Pages (CI/CD via Actions) |
| Point cloud (atual) | laspy · pyvista |
| Point cloud (5GB+, em desenvolvimento) | Potree · PotreeConverter · octree tiles |
| Storage de nuvens grandes | Cloudflare R2 (free 10GB) ou tunnel local |

---

## 📊 Compatibilidade de formatos

Os modelos exportados funcionam direto em:

| Software | Formato |
|---|---|
| **Civil 3D / AutoCAD** | OBJ (via Recap) |
| **SketchUp** | OBJ / DAE |
| **Blender** | GLB / OBJ / qualquer |
| **QGIS** | PLY (com plugin Qgis2threejs) |
| **CloudCompare** | PLY / OBJ |
| **Autodesk Recap** | OBJ |
| **Windows 3D Viewer** | GLB |
| **Browser (Three.js, Babylon)** | GLB |
| **Impressão 3D** | STL |

---

## 🚦 Roadmap

- [x] Modelo V3 paramétrico (Python)
- [x] 4 formatos de export (OBJ/GLB/PLY/STL)
- [x] Visualizador web responsivo
- [x] Pipeline básico point cloud (.las/.ply)
- [x] GitHub Pages deploy
- [ ] **Potree integration** para nuvens grandes (5 GB+)
- [ ] Medições interativas no browser (régua, área)
- [ ] Corte de seção (clipping plane)
- [ ] Anotações persistentes
- [ ] Login Toposcan + biblioteca de projetos
- [ ] Mobile app (Capacitor)
- [ ] Realidade aumentada (model-viewer já suporta WebXR)

Veja [docs/5gb-cloud-strategy.md](docs/5gb-cloud-strategy.md) para detalhes técnicos da próxima fase.

---

## 🏢 Sobre

**TopoScan** — soluções de topografia, agrimensura e modelagem 3D.
Projeto modelado a partir do PDF oficial **01-ARQUITETONICO TORRE RADAR-BANDA C** (SIMEPAR, JUN/2025, rev 01 24/03/2026).

---

## 📄 Licença

Modelo 3D e código deste repositório: TopoScan © 2026.
PDF arquitetônico fonte: propriedade SIMEPAR.

Para uso comercial fora do escopo TopoScan, entre em contato.
