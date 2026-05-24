# Estratégia para nuvem de pontos de 5 GB

## O problema

Carregar um arquivo `.las` de 5 GB de uma vez no browser é inviável:
- RAM consumida: ~10-15 GB (formato descomprimido)
- Tempo de download em rede normal: 5-10 min
- WebGL não consegue renderizar 200M+ pontos com pipeline ingênuo
- Mobile: trava completamente

## A solução: **Potree**

Potree é a tecnologia padrão de mercado para visualização web de point clouds gigantes. Roda em qualquer browser moderno via WebGL2.

**Como funciona:**
1. **Pré-processa** a nuvem uma vez (no servidor / máquina Toposcan)
2. Cria uma **árvore octree** com Level-of-Detail (LOD)
3. Salva ~10 mil pequenos arquivos `.bin` organizados hierarquicamente
4. No browser, carrega APENAS os tiles visíveis na resolução adequada (igual Google Maps)
5. Resultado: cena fluida (60 FPS) mesmo com 100+ bilhões de pontos

**Casos reais usando Potree:**
- Heritage Conservation (Notre-Dame, ~1 TB de scan)
- NASA Mars rover data
- Surveys urbanos de cidades inteiras

## Arquitetura proposta

```
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 1 — PRÉ-PROCESSAMENTO (uma vez, na máquina Toposcan)   │
│                                                              │
│ seu_levantamento.las (5 GB)                                  │
│        ↓                                                     │
│ PotreeConverter --output potree-tiles/                       │
│        ↓                                                     │
│ potree-tiles/  ←──── ~10 mil arquivos .bin de 1-50 KB cada   │
│   ├── octree.bin                                             │
│   ├── metadata.json                                          │
│   └── r/0/00/000.bin ... r/7/77/777.bin                      │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ (upload uma vez)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 2 — HOSPEDAGEM                                         │
│                                                              │
│ Opção A: Cloudflare R2 (recomendado)                         │
│   - 10 GB grátis (perfeito para 5 GB)                        │
│   - Egress ilimitado e grátis                                │
│   - CDN global automático                                    │
│   - $0.015/GB se passar de 10 GB                             │
│                                                              │
│ Opção B: Backblaze B2                                        │
│   - 10 GB grátis                                             │
│   - Egress $0.01/GB                                          │
│                                                              │
│ Opção C: Cloudflare Tunnel (sua máquina como server)         │
│   - $0 mas requer máquina ligada 24/7                        │
│   - Útil para desenvolvimento ou clientes ocasionais         │
│                                                              │
│ Opção D: GitHub LFS                                          │
│   - 2 GB grátis, $5/mês para 50 GB                           │
│   - Mas POTREE não funciona via Pages (precisa CORS, etc)    │
│   - Não recomendado para esse caso                           │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTPS GETs de tiles individuais
                            │ (cliente requisita só o que vê)
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 3 — VIEWER (no browser, integrado no nosso index.html) │
│                                                              │
│ Potree.viewer.loadPointCloud("https://r2.../metadata.json")  │
│        ↓                                                     │
│ Octree streaming → renderiza só tiles visíveis na resolução  │
│ adequada (vista atual da câmera + distância)                 │
│        ↓                                                     │
│ Combina com <model-viewer> (torre) overlay:                  │
│   - Mesma cena Three.js                                      │
│   - Coordenadas UTM alinhadas                                │
│   - Torre transladada para o ponto de implantação           │
└──────────────────────────────────────────────────────────────┘
```

## Como executar a Etapa 1 (pré-processamento)

```bash
# 1. Baixar PotreeConverter
# https://github.com/potree/PotreeConverter/releases
# (versão Windows: PotreeConverter_x64.zip)

# 2. Converter sua nuvem
PotreeConverter.exe "C:\caminho\seu_levantamento.las" -o ".\potree-tiles" --generate-page

# Tempo estimado: 5GB → ~20-40 min em PC normal
# Output: pasta potree-tiles/ com ~10k arquivos
```

## Recomendação para Toposcan

**Implementar Opção A (Cloudflare R2):**

1. Conta Cloudflare grátis
2. Criar R2 bucket `toposcan-pointclouds`
3. Upload da pasta `potree-tiles/` via `rclone` ou interface web
4. Configurar custom domain `clouds.toposcan.com.br` apontando para R2
5. CORS headers permissivos
6. Atualizar viewer pra apontar pra esse domínio

**Custo estimado:**
- 5 GB armazenamento: **grátis** (free tier 10 GB)
- Egress: **grátis no R2** (diferente de AWS S3)
- Custom domain: **grátis** (Cloudflare já gerencia)
- Total: **R$ 0/mês** para até 10 GB

Se passar de 10 GB:
- $0.015/GB/mês storage = R$ 0,08/GB/mês ~ R$ 4/mês para 50 GB
- Ainda imbatível

## Próximos passos (quando o levantamento real chegar)

1. ✅ Receber arquivo `.las` da Toposcan
2. ⬜ Validar com `laspy` (extensão geográfica, número de pontos, atributos RGB)
3. ⬜ Pré-processar com PotreeConverter
4. ⬜ Subir para Cloudflare R2 (criar conta + bucket)
5. ⬜ Integrar Potree.js no `index.html` ao lado do model-viewer
6. ⬜ Adicionar UI de seleção de projeto (múltiplas torres)
7. ⬜ Adicionar medições no contexto da nuvem

## Alternativa "low-effort" enquanto não temos Potree

Para nuvens **até 200 MB** (subsample do levantamento original):

1. Usar `laspy` para reduzir a nuvem (manter 1 em cada N pontos)
2. Exportar como `.ply` ou `.glb`
3. Carregar direto no `<model-viewer>` igual fazemos com a torre

Isso já dá ~10-20M pontos visíveis, suficiente para apresentação.

```python
import laspy
las = laspy.read("levantamento_5gb.las")
sub = las[::50]  # 1 em cada 50 → ~100MB de saída
sub.write("levantamento_subsampled.las")
```

## Decisão para HOJE

- ✅ Viewer publicado no GitHub Pages
- ✅ Pipeline Python funcional (`implantar_torre_no_terreno.py`)
- ✅ Demo com terreno sintético rodando
- ⏳ Aguardando arquivo real da Toposcan para Etapa 1 (PotreeConverter)
- ⏳ Aguardando confirmação para criar conta Cloudflare R2 (Etapa 2)
