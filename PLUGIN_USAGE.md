# Scatter MultiMesh — Blender → Godot 3.6

Pipeline para espalhar assets (grama, árvores, pedras, flores…) sobre um terreno
no **Blender** usando **vertex paint** como máscara, e reproduzi-los no **Godot 3.6**
de forma otimizada via **MultiMesh** (1 draw call por modelo), com **vento** e
**colisão** opcionais.

Grama e "props" usam o **mesmo** export e o **mesmo** nó — a única diferença é a
origem dos pontos e quais opções você liga.

---

## Componentes

| Parte | Arquivo | Onde roda |
|-------|---------|-----------|
| Add-on de autoria/export | `blender/blendertogodot_multimesh.py` | Blender |
| Plugin de editor | `plugin.cfg` + `plugin.gd` | Godot |
| Nó unificado | `multimesh_from_blender.gd` (`MultiMeshFromBlender`) | Godot |
| Shader de grama | `grass.shader` | Godot |

---

## Instalação

### Blender
1. `Edit > Preferences > Add-ons > Install…`
2. Aponte para `blender/blendertogodot_multimesh.py` e ative **"BlenderToGodot MultiMesh"**.
3. O painel fica na **barra lateral (N)** do Viewport, aba **"Scatter"**.

### Godot 3.6
1. Coloque o repositório em `res://addons/blendertogodot_multimesh/` (via submódulo git ou cópia).
2. `Project > Project Settings > Plugins` → ative **"BlenderToGodot MultiMesh Plugin"**.
3. O nó **`MultiMeshFromBlender`** aparece em **Add Node**.
   O add-on do Blender fica em `addons/blendertogodot_multimesh/blender/`.

---

## Fluxo de uso

### 1) No Blender

**Máscara (comum a tudo)**
- **Superfície**: a malha do terreno (com a pintura de vértice).
- **Atributo de Cor**: nome do color attribute (ex.: `Attribute`).
- **Cor-alvo + Tolerância**: a cor que serve de referência.
- **Modo**: `Evitar a cor` (espalha longe dela) ou `Apenas a cor` (só sobre ela).
- **Limitar por altura (Z)**: opcional, para excluir montanhas etc.

**Espalhar objetos (dentro do Blender)** — cria cópias vinculadas para você ver/ajustar:
- **Paleta**: coleção com os modelos (sorteados aleatoriamente).
- Quantidade, distância mínima, faixa de escala, alinhar à normal, coleção destino.

**Exportar → Godot** — gera o JSON:
- **Origem = Amostrar superfície**: gera N pontos na hora (denso, 1 modelo). Ideal para **grama**.
  - `Nome do modelo` (ex.: `grass`), quantidade, escala, alinhar à normal.
- **Origem = De uma coleção**: lê uma coleção de scatter já criada (multi-modelo,
  transform completo). Ideal para **árvores/pedras**.
- **Arquivo JSON**: destino (ex.: `//scatter.json` grava ao lado do `.blend`;
  aponte para dentro do projeto Godot, ex.: `res://.../scatter.json`).

### 2) No Godot

Adicione um **`MultiMeshFromBlender`** na cena, **na origem (0,0,0)**, e configure:

- **Json Path**: o arquivo exportado.
- **Resolução das malhas** — escolha um dos dois modos:
  - **A) Dinâmico (recomendado)**: preencha **Source Scene** com a cena importada
    (`.glb`). O plugin varre a cena e resolve as malhas **pelo nome de cada nó**
    (`Pine_1`, `Grass_Common_Short`…), que casa com os `models` do JSON.
    **Não precisa preencher Meshes/Model Names.**
  - **B) Manual (fallback)**: **Meshes** + **Model Names** na mesma ordem, se você
    preferir apontar recursos `.mesh` avulsos em vez da cena inteira.
- **Override Material** (opcional): material único aplicado a todas as malhas do nó
  (vazio = usa o material de cada malha). Para grama de *card* com vento, monte um
  `ShaderMaterial` com `grass.shader` e coloque aqui.
- **Props colidíveis**: liste nomes em **Collidable Names** →
  gera `StaticBody` + `CollisionShape` por instância.
  - `Collision Shape Type`: Box / Cylinder / Sphere (Cylinder é ótimo p/ tronco).
  - `Collision Size Factor`: engrossa/afina o colisor (dimensionado pelo AABB da malha).
- Marque **Rebuild** para (re)construir no editor.

> **Assado vs. runtime:** ao clicar Rebuild no editor, os `MultiMeshInstance`
> ficam **salvos na cena** com seus materiais/ajustes (ex.: um `ShaderMaterial`
> de vento aplicado à grama). Em runtime o nó **preserva** esses nós salvos e
> **não** reconstrói — assim seus overrides não se perdem. Um nó **sem filhos**
> (nunca construído no editor) reconstrói sozinho a partir do JSON ao rodar.
> Portanto: se você aplicar materiais manualmente nos `MM_*`, faça isso **depois**
> do Rebuild, no editor.

---

## Formato do JSON

```json
{
  "models": ["Pine_1", "Pine_2"],
  "count":  120,
  "model":  [0, 1, 0, ...],
  "xf":     [ /* 12 floats por instância */ ]
}
```

- `models`: nomes dos modelos.
- `model[i]`: índice do modelo da instância `i`.
- `xf`: por instância, **3 eixos da base (x, y, z) + origem**, já no espaço do Godot
  (Y-up). Reconstruído como `Transform(x_axis, y_axis, z_axis, origin)`.

### Conversão de coordenadas
O add-on converte Blender (Z-up) → Godot (Y-up) por `(x, y, z) → (x, z, -y)`,
aplicando também a escala do terreno (usa `matrix_world`). Por isso o
`MultiMeshFromBlender` deve ficar na **origem do mundo**, no mesmo espaço do terreno
importado. Se o terreno estiver sob um nó pai transformado, coloque o
`MultiMeshFromBlender` sob o **mesmo pai**.

---

## Recomendações de performance (kart)

- **Vegetação densa sem colisão** (grama, flores, plantas): `MultiMeshFromBlender`
  com material de vento. Milhares de instâncias = 1 draw call por modelo.
- **Árvores/pedras**: `MultiMeshFromBlender` com colisão **só nos modelos que importam**
  perto da pista (via `Collidable Names`). Visual barato + colisão onde o kart bate.
- **Culling**: no Godot 3.6 o MultiMesh é cull como um bloco único. Para assets
  espalhados pelo mapa inteiro, considere **dividir por regiões** (um
  `MultiMeshFromBlender` por chunk) para recuperar culling.
- Material da grama: **alpha scissor** (pipeline opaco), nunca alpha blend.
  O fade por distância usa dithering (screen-door), compatível com opaco.

---

## Shader de grama (`grass.shader`)

Parâmetros principais:
- `texture_albedo`, `tint`, `alpha_scissor`
- Vento: `wind_direction`, `wind_speed`, `wind_strength`, `wind_scale`, `wind_height`
- Fade: `fade_start`, `fade_end`

`wind_height` = altura aproximada da grama (máscara base-fixa/topo-balança).
Assume a grama crescendo em **+Y a partir da base**. Se balançar pela ponta errada,
ajuste esse valor ou o pivô da malha.
