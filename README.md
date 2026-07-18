# BlenderToGodot MultiMesh Plugin

Pipeline **Blender → Godot 3.6** para espalhar assets (grama, árvores, pedras,
flores…) sobre um terreno usando **vertex paint** como máscara, e reproduzi-los
no Godot de forma otimizada via **MultiMesh** (1 draw call por modelo), com
**vento** e **colisão** opcionais.

A **raiz deste repositório é o próprio plugin do Godot** (`plugin.cfg` na raiz),
para poder ser usado como **submódulo git** em `res://addons/blendertogodot_multimesh`.
O add-on do Blender vem junto, na pasta [`blender/`](blender/), já que os dois
trabalham em conjunto.

| Parte | Caminho | Onde roda |
|-------|---------|-----------|
| Add-on de autoria/export | [`blender/blendertogodot_multimesh.py`](blender/blendertogodot_multimesh.py) | Blender |
| Plugin de editor + nó `MultiMeshFromBlender` + shader | raiz (`plugin.cfg`, `multimesh_from_blender.gd`, `grass.shader`) | Godot 3.6 |

## Como funciona (resumo)

1. **Blender**: pinte o terreno com vertex colors (ex.: vermelho = pista).
   No painel *Scatter* (barra lateral N), defina a máscara e:
   - **Espalhe** os modelos para visualizar; e/ou
   - **Exporte** um JSON unificado (transform completo, multi-modelo).
2. **Godot**: adicione um nó **`MultiMeshFromBlender`**, aponte para o JSON e as malhas.
   Ele monta um MultiMesh por modelo, aplica o shader de vento (grama) e gera
   colisão (props) conforme configurado.

## Instalar

### Como submódulo (recomendado)
```bash
git submodule add https://github.com/ian-Reis/BlenderToGodot-MultiMesh-Plugin.git addons/blendertogodot_multimesh
```
Depois, no Godot: `Project > Project Settings > Plugins` → ative **"BlenderToGodot MultiMesh Plugin"**.
O add-on do Blender fica em `addons/blendertogodot_multimesh/blender/blendertogodot_multimesh.py`.

### Manual
Copie o conteúdo do repositório para `res://addons/blendertogodot_multimesh/` e ative o plugin.

## Uso detalhado

Veja **[PLUGIN_USAGE.md](PLUGIN_USAGE.md)** — instalação nos dois lados, formato do
JSON, conversão de coordenadas (Blender Z-up → Godot Y-up) e dicas de performance.

## Compatibilidade

- **Godot 3.6** (`MultiMeshInstance`, `StaticBody`, `CollisionShape` da API 3.x).
- **Blender 4.0+** (add-on testado com a API `bpy` 4.x/5.x).

## Licença

MIT — veja [LICENSE](LICENSE).
