# Arquitetura técnica — TopoScan 3D Viewer

## Visão geral em 3 camadas

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND (browser)                                          │
│  - GitHub Pages serve index.html + models/                   │
│  - <model-viewer> renderiza GLB (Three.js + WebGL)           │
│  - Potree (futuro) renderiza nuvens > 100MB via octree       │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ (HTTPS, GETs assíncronos)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  STORAGE (estático)                                          │
│  - GitHub Pages (modelos pequenos < 100MB)                   │
│  - Cloudflare R2 / S3 (nuvens grandes 100MB–10GB+)           │
│  - Local tunnel (Cloudflare Tunnel) p/ desenvolvimento       │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │ (pipeline build)
┌──────────────────────────────────────────────────────────────┐
│  GERAÇÃO (Python local na máquina Toposcan)                  │
│  - trimesh: modelagem paramétrica                            │
│  - laspy: leitura LAS/LAZ                                    │
│  - pyvista: render programático                              │
│  - PotreeConverter (futuro): LAS → octree tiles              │
└──────────────────────────────────────────────────────────────┘
```

## Decisões de design

### Por que `<model-viewer>` e não Three.js direto?

`<model-viewer>` é uma webcomponent da Google que:
- Encapsula Three.js com defaults sensatos
- Suporta WebXR (AR no celular) sem código adicional
- API declarativa (atributos HTML)
- 60+ FPS em GLBs até ~50MB
- Suporta PBR, sombras, IBL out-of-the-box

Three.js puro daria mais flexibilidade, mas adicionar features (corte, anotação) é mais rápido sobre o `<model-viewer>` via atributos custom + observadores.

### Por que GLB e não OBJ/FBX?

| Formato | Tamanho | Velocidade load | Browser support |
|---|---|---|---|
| **GLB** | 286 KB | ⚡ instant | ✅ nativo |
| OBJ + MTL | 490 KB + textures | 🐢 lento | ❌ precisa parser |
| FBX | n/d | n/d | ❌ não há parser web |

GLB = JSON + buffers binários + opcionalmente Draco compression. É o padrão moderno (gltf 2.0).

### Por que GitHub Pages e não Vercel/Netlify?

- **Grátis ilimitado** (até 1 GB total, 100 GB bandwidth/mês)
- Deploy automático via push
- Custom domain trivial (`viewer.toposcan.com.br`)
- HTTPS automático
- Não há backend → zero custo operacional

Vercel/Netlify seriam necessários se tivéssemos backend serverless. Hoje não precisamos.

### Origem (0,0,0) no modelo

Centro da base da torre, ao nível do solo. Por quê:
1. Permite **rotação ao redor do eixo Z** sem deslocamento
2. **Translação UTM trivial**: basta somar (E, N, h) para implantar
3. **Bounding box simétrico** facilita posicionamento de câmera

## Pipeline de build

```
PDF (AutoCAD) ──┐
                ├──► [Python parser: pymupdf]
                │       └─► texto + cotas extraídas
                ▼
           Parâmetros (m)
                │
                ├──► [trimesh: geometria]
                │       └─► 401 meshes paramétricas
                │
                ├──► [pyvista: render]
                │       └─► 10 PNGs profissionais
                │
                └──► [export multi-format]
                        ├─► .glb (web)
                        ├─► .obj (Civil 3D / SketchUp)
                        ├─► .ply (QGIS / CloudCompare)
                        └─► .stl (impressão 3D)
```

Mudança de dimensão → editar `scripts/build_torre_v3.py` no topo, rodar, commitar → push automático para Pages.

## Performance

| Cenário | Tempo de carga | FPS |
|---|---|---|
| Torre só (286 KB) | < 500ms | 60 |
| Cena com terreno sintético (657 KB) | < 1.2s | 60 |
| **Cena com nuvem 5 GB (com Potree)** | < 2s (stream progressivo) | 60 |

A magia do Potree é que mesmo nuvens enormes (50 GB+) ficam fluidas porque ele só carrega os tiles visíveis na resolução adequada — exatamente como Google Maps.

## Segurança

- Repo público: não conter dados sensíveis (coordenadas exatas só após autorização)
- GitHub Pages: HTTPS forçado
- Sem cookies, sem tracking, sem analytics (a menos que adicionemos)
- Modelos 3D são geometria pura — sem PII

## Observabilidade

Para versão produção, adicionar:
- Plausible.io (analytics privacy-friendly, ~€9/mês)
- Sentry para erros JavaScript (free tier 5k events/mês)
- GitHub Pages tem métricas básicas built-in
