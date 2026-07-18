# SPDX-License-Identifier: MIT
# BlenderToGodot MultiMesh
# Add-on do Blender: espalha assets sobre uma superficie mascarada por vertex paint
# (evitar/apenas uma cor + limite de altura) e EXPORTA um unico JSON unificado
# (transform completo, multi-modelo) para o no MultiMeshFromBlender do Godot 3.6.
#
# Instalar: Edit > Preferences > Add-ons > Install... e aponte para este arquivo.
# Painel: barra lateral (N) do Viewport, aba "Scatter".

bl_info = {
    "name": "BlenderToGodot MultiMesh",
    "author": "Cozy Kart tools",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar (N) > Scatter",
    "description": "Espalha assets por vertex paint e exporta para MultiMesh do Godot",
    "category": "Object",
}

import bpy
import os
import random
import math
import json
import mathutils


# Troca de base Blender(Z-up) -> Godot(Y-up): (x, y, z) -> (x, z, -y)
_C = mathutils.Matrix(((1, 0, 0, 0),
                       (0, 0, 1, 0),
                       (0, -1, 0, 0),
                       (0, 0, 0, 1)))
_Cinv = _C.inverted()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _face_avg_color(me, ca, poly):
    r = g = b = 0.0
    for li in poly.loop_indices:
        c = ca.data[li].color
        r += c[0]; g += c[1]; b += c[2]
    n = len(poly.loop_indices) or 1
    return r / n, g / n, b / n


def _color_pass(face_rgb, target, tol, mode):
    dr = face_rgb[0] - target[0]
    dg = face_rgb[1] - target[1]
    db = face_rgb[2] - target[2]
    dist = math.sqrt(dr * dr + dg * dg + db * db)
    return dist > tol if mode == 'AVOID' else dist <= tol


def _matrix_to_xf(M):
    """Converte matriz de mundo Blender -> 12 floats no espaco do Godot
    (3 eixos da base como colunas + origem)."""
    Mg = _C @ M @ _Cinv
    cx, cy, cz = Mg.col[0], Mg.col[1], Mg.col[2]
    org = Mg.translation
    return [round(cx[0], 4), round(cx[1], 4), round(cx[2], 4),
            round(cy[0], 4), round(cy[1], 4), round(cy[2], 4),
            round(cz[0], 4), round(cz[1], 4), round(cz[2], 4),
            round(org[0], 3), round(org[1], 3), round(org[2], 3)]


def _sample_surface(context, count, min_dist):
    """Amostra pontos na superficie respeitando mascara de cor e altura.
    Retorna (list[(world_matrix, )], msg) ou (None, erro)."""
    p = context.scene.vsx
    surf = p.surface
    if surf is None or surf.type != 'MESH':
        return None, "Selecione uma Superficie (malha) valida."
    me = surf.data
    ca = me.color_attributes.get(p.color_attr) if p.color_attr else None
    if ca is None:
        return None, "Atributo de cor '%s' nao encontrado." % p.color_attr

    mw = surf.matrix_world
    mw_inv = mw.inverted()
    down_local = (mw_inv.to_3x3() @ mathutils.Vector((0, 0, -1))).normalized()

    xs = [(mw @ v.co).x for v in me.vertices]
    ys = [(mw @ v.co).y for v in me.vertices]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    target = tuple(p.mask_color)
    tol = p.mask_tolerance
    mode = p.mask_mode
    up = mathutils.Vector((0, 0, 1))

    out = []
    placed = []
    attempts = 0
    max_attempts = count * 8
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        wx = random.uniform(xmin, xmax)
        wy = random.uniform(ymin, ymax)
        origin = mw_inv @ mathutils.Vector((wx, wy, 100000.0))
        hit, loc, nrm, idx = surf.ray_cast(origin, down_local)
        if not hit or idx < 0:
            continue
        wh = mw @ loc
        if p.use_height_limit and (wh.z < p.height_min or wh.z > p.height_max):
            continue
        if not _color_pass(_face_avg_color(me, ca, me.polygons[idx]), target, tol, mode):
            continue
        if min_dist > 0.0 and any((wh - q).length < min_dist for q in placed):
            continue
        placed.append(wh)

        yaw = random.uniform(0.0, 2.0 * math.pi)
        s = random.uniform(p.scale_min, p.scale_max)
        world_nrm = (mw.to_3x3() @ nrm).normalized()
        if p.align_normal:
            rot = up.rotation_difference(world_nrm) @ mathutils.Euler((0, 0, yaw)).to_quaternion()
        else:
            rot = mathutils.Euler((0, 0, yaw)).to_quaternion()
        M = (mathutils.Matrix.Translation(wh)
             @ rot.to_matrix().to_4x4()
             @ mathutils.Matrix.Scale(s, 4))
        out.append(M)
    return out, "%d posicoes (em %d tentativas)" % (len(out), attempts)


def _get_or_make_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _source_name(data, cache):
    """Nome do MODELO-FONTE (objeto mais 'limpo' que usa aquela malha),
    casando com o nome do no no glTF (ex.: 'Bush_Common_Flowers')."""
    if data.name in cache:
        return cache[data.name]
    cands = [ob for ob in bpy.data.objects if ob.data == data]
    src = min(cands, key=lambda ob: (('.' in ob.name), len(ob.name)))
    cache[data.name] = src.name
    return src.name


def _scatter_collections():
    """Colecoes que passaram pelo scatter: marcadas com a tag 'btg_scatter'
    ou cujo nome comeca com 'Scatter' / termina com '_Scatter'."""
    out = []
    for c in bpy.data.collections:
        n = c.name.lower()
        if c.get("btg_scatter") or n.startswith("scatter") or n.endswith("_scatter"):
            out.append(c)
    return out


def _collect_from_collections(colls):
    """Junta objetos de varias colecoes num unico conjunto multi-modelo."""
    models = []
    model_idx = []
    xf = []
    cache = {}
    used_colls = []
    for coll in colls:
        n = 0
        for o in coll.objects:
            if o.type != 'MESH':
                continue
            key = _source_name(o.data, cache)
            if key not in models:
                models.append(key)
            model_idx.append(models.index(key))
            xf.extend(_matrix_to_xf(o.matrix_world))
            n += 1
        if n:
            used_colls.append(coll.name)
    return models, model_idx, xf, used_colls


def _prefs(context):
    ad = context.preferences.addons.get(__name__)
    return ad.preferences if ad else None


def _resolve_out_path(context, filename):
    """Pasta lembrada (AddonPreferences) + nome do arquivo."""
    pr = _prefs(context)
    folder = ""
    if pr and pr.export_dir:
        folder = bpy.path.abspath(pr.export_dir)
    if not folder:
        folder = bpy.path.abspath("//") if bpy.data.filepath else os.path.expanduser("~")
    if not filename.lower().endswith(".json"):
        filename += ".json"
    return os.path.join(folder, filename)


class VSXPrefs(bpy.types.AddonPreferences):
    bl_idname = __name__
    export_dir: bpy.props.StringProperty(
        name="Pasta de export", subtype='DIR_PATH', default="",
        description="Pasta onde os JSON serao salvos (lembrada entre sessoes)")

    def draw(self, context):
        self.layout.prop(self, "export_dir")


# --------------------------------------------------------------------------- #
# Properties
# --------------------------------------------------------------------------- #
class VSXProps(bpy.types.PropertyGroup):
    surface: bpy.props.PointerProperty(
        name="Superficie", type=bpy.types.Object,
        description="Malha com a pintura de vertice (o terreno)")
    color_attr: bpy.props.StringProperty(name="Atributo de Cor", default="Attribute")

    mask_color: bpy.props.FloatVectorProperty(
        name="Cor-alvo", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.0, 0.0))
    mask_tolerance: bpy.props.FloatProperty(name="Tolerancia", default=0.5, min=0.0, max=1.8)
    mask_mode: bpy.props.EnumProperty(
        name="Modo", default='AVOID',
        items=[('AVOID', "Evitar a cor", "Nao espalha perto da cor-alvo"),
               ('ONLY', "Apenas a cor", "Espalha somente perto da cor-alvo")])

    use_height_limit: bpy.props.BoolProperty(name="Limitar por altura (Z)", default=False)
    height_min: bpy.props.FloatProperty(name="Z min", default=0.0)
    height_max: bpy.props.FloatProperty(name="Z max", default=8.0)

    # Espalhar (cria objetos no Blender)
    palette: bpy.props.PointerProperty(
        name="Paleta", type=bpy.types.Collection,
        description="Colecao com os modelos a espalhar (sorteados)")
    count: bpy.props.IntProperty(name="Quantidade", default=50, min=1, max=200000)
    min_dist: bpy.props.FloatProperty(name="Dist. minima", default=5.0, min=0.0)
    scale_min: bpy.props.FloatProperty(name="Escala min", default=0.8, min=0.001)
    scale_max: bpy.props.FloatProperty(name="Escala max", default=1.3, min=0.001)
    align_normal: bpy.props.BoolProperty(name="Alinhar a normal", default=False)
    out_collection: bpy.props.StringProperty(name="Colecao destino", default="Scatter")

    # Export unificado -> Godot
    export_mode: bpy.props.EnumProperty(
        name="Origem", default='SAMPLE',
        items=[('SAMPLE', "Amostrar superficie",
                "Gera pontos na hora (denso; ideal p/ grama - 1 modelo)"),
               ('COLLECTION', "De uma colecao",
                "Le objetos ja criados (multi-modelo; ideal p/ arvores/pedras)"),
               ('ALL', "Todas as colecoes scatter",
                "Junta todas as colecoes de scatter num unico JSON multi-modelo")])
    sample_count: bpy.props.IntProperty(name="Quantidade", default=6000, min=1, max=500000)
    sample_model_name: bpy.props.StringProperty(name="Nome do modelo", default="grass")
    prop_source: bpy.props.PointerProperty(
        name="Colecao", type=bpy.types.Collection,
        description="Colecao de scatter ja criada (ex.: Pines_Scatter)")
    export_filename: bpy.props.StringProperty(
        name="Nome do arquivo", default="scatter.json",
        description="Nome do JSON (a pasta e lembrada nas Preferencias do add-on)")


# --------------------------------------------------------------------------- #
# Operators
# --------------------------------------------------------------------------- #
class VSX_OT_scatter(bpy.types.Operator):
    """Espalha os modelos da paleta como copias vinculadas (instancias)"""
    bl_idname = "vsx.scatter_objects"
    bl_label = "Espalhar objetos"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = context.scene.vsx
        if p.palette is None:
            self.report({'ERROR'}, "Defina a Paleta.")
            return {'CANCELLED'}
        sources = [o for o in p.palette.objects if o.type == 'MESH']
        if not sources:
            self.report({'ERROR'}, "A Paleta nao tem malhas.")
            return {'CANCELLED'}

        samples, msg = _sample_surface(context, p.count, p.min_dist)
        if samples is None:
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        coll = _get_or_make_collection(p.out_collection)
        coll["btg_scatter"] = True   # marca p/ o export "Todas as colecoes scatter"
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)

        for M in samples:
            src = random.choice(sources)
            inst = src.copy()  # compartilha a malha = instancia
            coll.objects.link(inst)
            loc, rot, sca = M.decompose()
            inst.location = loc
            inst.rotation_mode = 'QUATERNION'
            inst.rotation_quaternion = rot
            inst.scale = (src.scale.x * sca.x, src.scale.y * sca.y, src.scale.z * sca.z)

        self.report({'INFO'}, "Espalhado: " + msg)
        return {'FINISHED'}


class VSX_OT_export(bpy.types.Operator):
    """Exporta um JSON unificado (transform completo, multi-modelo) para o Godot"""
    bl_idname = "vsx.export_scatter"
    bl_label = "Exportar (JSON)"

    def execute(self, context):
        p = context.scene.vsx
        models = []
        model_idx = []
        xf = []

        if p.export_mode == 'SAMPLE':
            samples, msg = _sample_surface(context, p.sample_count, 0.0)
            if samples is None:
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            models = [p.sample_model_name]
            for M in samples:
                model_idx.append(0)
                xf.extend(_matrix_to_xf(M))
            info = "%s: %d inst" % (p.sample_model_name, len(model_idx))

        elif p.export_mode == 'COLLECTION':
            coll = p.prop_source
            if coll is None:
                self.report({'ERROR'}, "Defina a Colecao.")
                return {'CANCELLED'}
            models, model_idx, xf, used = _collect_from_collections([coll])
            if not model_idx:
                self.report({'ERROR'}, "A colecao nao tem malhas.")
                return {'CANCELLED'}
            info = "%d inst, modelos %s" % (len(model_idx), models)

        else:  # ALL: todas as colecoes de scatter
            colls = _scatter_collections()
            if not colls:
                self.report({'ERROR'}, "Nenhuma colecao de scatter encontrada.")
                return {'CANCELLED'}
            models, model_idx, xf, used = _collect_from_collections(colls)
            if not model_idx:
                self.report({'ERROR'}, "As colecoes scatter estao vazias.")
                return {'CANCELLED'}
            info = "%d inst de %s; modelos %s" % (len(model_idx), used, models)

        data = {"models": models, "count": len(model_idx),
                "model": model_idx, "xf": xf}
        path = _resolve_out_path(context, p.export_filename)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as ex:
            self.report({'ERROR'}, "Falha ao gravar: %s" % ex)
            return {'CANCELLED'}

        self.report({'INFO'}, "Exportado (%s) -> %s" % (info, path))
        return {'FINISHED'}


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
class VSX_PT_panel(bpy.types.Panel):
    bl_label = "BlenderToGodot MultiMesh"
    bl_idname = "VSX_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Scatter"

    def draw(self, context):
        p = context.scene.vsx
        col = self.layout.column()

        box = col.box()
        box.label(text="Superficie e Mascara", icon='BRUSH_DATA')
        box.prop(p, "surface")
        box.prop(p, "color_attr")
        box.prop(p, "mask_color")
        box.prop(p, "mask_tolerance")
        box.prop(p, "mask_mode", expand=True)
        box.prop(p, "use_height_limit")
        if p.use_height_limit:
            row = box.row(align=True)
            row.prop(p, "height_min")
            row.prop(p, "height_max")

        box = col.box()
        box.label(text="Espalhar objetos (Blender)", icon='OUTLINER_OB_MESH')
        box.prop(p, "palette")
        box.prop(p, "count")
        box.prop(p, "min_dist")
        row = box.row(align=True)
        row.prop(p, "scale_min")
        row.prop(p, "scale_max")
        box.prop(p, "align_normal")
        box.prop(p, "out_collection")
        box.operator("vsx.scatter_objects", icon='STICKY_UVS_LOC')

        box = col.box()
        box.label(text="Exportar -> Godot", icon='EXPORT')
        box.prop(p, "export_mode", expand=True)
        if p.export_mode == 'SAMPLE':
            box.prop(p, "sample_count")
            box.prop(p, "sample_model_name")
            row = box.row(align=True)
            row.prop(p, "scale_min")
            row.prop(p, "scale_max")
            box.prop(p, "align_normal")
        elif p.export_mode == 'COLLECTION':
            box.prop(p, "prop_source")
        else:  # ALL
            colls = [c.name for c in _scatter_collections()]
            box.label(text="Colecoes: %s" % (", ".join(colls) if colls else "(nenhuma)"))

        pr = _prefs(context)
        if pr:
            box.prop(pr, "export_dir")
        else:
            box.label(text="(instale o add-on p/ lembrar a pasta)", icon='INFO')
        box.prop(p, "export_filename")
        box.operator("vsx.export_scatter", icon='FILE_TICK')


# --------------------------------------------------------------------------- #
# Register
# --------------------------------------------------------------------------- #
_classes = (VSXPrefs, VSXProps, VSX_OT_scatter, VSX_OT_export, VSX_PT_panel)


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.vsx = bpy.props.PointerProperty(type=VSXProps)


def unregister():
    del bpy.types.Scene.vsx
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
