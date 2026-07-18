# Godot Mesh Ready Plugin

Pipeline **Blender → Godot 3.6** para espalhar assets (grama, árvores, pedras,
flores…) sobre um terreno usando **vertex paint** como máscara, e reproduzi-los
no Godot de forma otimizada via **MultiMesh** (1 draw call por modelo), com
**vento** e **colisão** opcionais.

Os dois lados trabalham em conjunto:

| Parte | Pasta | Onde roda |
|-------|-------|-----------|
| Add-on de autoria/export | [`tools/blender_vertex_scatter.py`](tools/blender_vertex_scatter.py) | Blender |
| Plugin de editor + nó `ScatterMultiMesh` + shader | [`addons/grass_scatter/`](addons/grass_scatter/) | Godot 3.6 |

## Como funciona (resumo)

1. **Blender**: pinte o terreno com vertex colors (ex.: vermelho = pista).
   No painel *Scatter* (barra lateral N), defina a máscara e:
   - **Espalhe** os modelos para visualizar; e/ou
   - **Exporte** um JSON unificado (transform completo, multi-modelo).
2. **Godot**: adicione um nó **`ScatterMultiMesh`**, aponte para o JSON e as malhas.
   Ele monta um MultiMesh por modelo, aplica o shader de vento (grama) e gera
   colisão (props) conforme configurado.

## Instalação e uso detalhados

Veja **[`addons/grass_scatter/README.md`](addons/grass_scatter/README.md)** — cobre
instalação nos dois lados, o formato do JSON, a conversão de coordenadas
(Blender Z-up → Godot Y-up) e recomendações de performance.

## Compatibilidade

- **Godot 3.6** (usa `MultiMeshInstance`, `StaticBody`, `CollisionShape` da API 3.x).
- **Blender 4.0+** (add-on testado com a API `bpy` 4.x/5.x).

## Licença

MIT — veja [LICENSE](LICENSE).
