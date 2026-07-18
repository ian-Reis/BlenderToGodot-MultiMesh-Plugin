tool
extends Spatial
# MultiMeshFromBlender (Godot 3.6) - no unificado
# Le o JSON exportado pelo add-on do Blender (transform completo, multi-modelo) e monta:
#   - 1 MultiMeshInstance por modelo (visual otimizado, 1 draw call cada);
#   - (opcional) material de vento a partir de grass.shader, para grama;
#   - (opcional) StaticBody + CollisionShape por instancia dos modelos colidiveis.
#
# Serve tanto para GRAMA (JSON de 1 modelo + textura de vento)
# quanto para PROPS (JSON multi-modelo + colisao). E o mesmo no.
#
# USO:
#   - Add Node > MultiMeshFromBlender, na origem (0,0,0).
#   - "Meshes": as malhas dos modelos.
#   - "Model Names": nomes na MESMA ORDEM das Meshes (casam com os do JSON).
#   - "Json Path": o arquivo exportado.
#   - Grama: preencha "Grass Texture" (gera o material de vento) OU "Override Material".
#   - Props colidiveis: liste nomes em "Collidable Names".
#   - Marque "Rebuild" para (re)construir no editor.

export(Array, Mesh) var meshes
export(PoolStringArray) var model_names
export(String, FILE, "*.json") var json_path = "res://scatter.json"

# Material: prioridade override_material > (grass_shader + grass_texture) > material da malha
export(Material) var override_material = null
export(Texture) var grass_texture = null

# Colisao (para modelos listados em collidable_names)
export(PoolStringArray) var collidable_names
export(int, "Box", "Cylinder", "Sphere") var collision_shape_type = 1
export(float) var collision_size_factor = 0.4
export(int, LAYERS_3D_PHYSICS) var collision_layer = 1

export(int, "Off", "On", "DoubleSided", "ShadowsOnly") var cast_shadow = 1
export(bool) var rebuild setget _set_rebuild

const GRASS_SHADER := preload("grass.shader")


func _set_rebuild(_v):
	build()


func _ready():
	if not Engine.editor_hint:
		build()


func build():
	for c in get_children():
		c.queue_free()

	if meshes.empty():
		push_warning("MultiMeshFromBlender: defina 'Meshes'.")
		return

	var data = _load_json(json_path)
	if data == null:
		return

	var models = data["models"]
	var count = int(data["count"])
	var midx = data["model"]
	var xf = data["xf"]

	# mapa: indice-do-JSON -> indice-da-mesh (por nome; ordem independente)
	var json_to_mesh = []
	for jm in range(models.size()):
		json_to_mesh.append(_mesh_index_for(models[jm]))

	var buckets = []
	for m in range(meshes.size()):
		buckets.append([])
	var collide_list = []

	for i in range(count):
		var o = i * 12
		var t = Transform(
			Vector3(xf[o + 0], xf[o + 1], xf[o + 2]),
			Vector3(xf[o + 3], xf[o + 4], xf[o + 5]),
			Vector3(xf[o + 6], xf[o + 7], xf[o + 8]),
			Vector3(xf[o + 9], xf[o + 10], xf[o + 11]))
		var jm = int(midx[i])
		var mesh_i = json_to_mesh[jm]
		if mesh_i < 0:
			continue
		buckets[mesh_i].append(t)
		if _is_collidable(models[jm]):
			collide_list.append({"t": t, "mesh": meshes[mesh_i]})

	var mat = _resolve_material()

	for m in range(meshes.size()):
		var list = buckets[m]
		if list.empty():
			continue
		var mm = MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = meshes[m]
		mm.instance_count = list.size()
		for j in range(list.size()):
			mm.set_instance_transform(j, list[j])

		var mmi = MultiMeshInstance.new()
		mmi.name = "MM_" + str(_name_for_mesh(m))
		mmi.multimesh = mm
		mmi.cast_shadow = cast_shadow
		if mat != null:
			mmi.material_override = mat
		add_child(mmi)
		_own(mmi)

	if not collide_list.empty():
		var holder = Spatial.new()
		holder.name = "Collisions"
		add_child(holder)
		_own(holder)
		for item in collide_list:
			_make_collision(holder, item["t"], item["mesh"])

	print("MultiMeshFromBlender: ", count, " instancias, ",
		meshes.size(), " modelo(s), ", collide_list.size(), " colisores.")


func _resolve_material():
	if override_material != null:
		return override_material
	if grass_texture != null:
		var sm = ShaderMaterial.new()
		sm.shader = GRASS_SHADER
		sm.set_shader_param("texture_albedo", grass_texture)
		return sm
	return null


func _make_collision(parent, xform, mesh):
	var body = StaticBody.new()
	body.collision_layer = collision_layer
	body.transform = xform
	parent.add_child(body)
	_own(body)

	var cs = CollisionShape.new()
	var aabb = mesh.get_aabb()
	var size = aabb.size
	var center = aabb.position + size * 0.5
	var f = collision_size_factor

	var shape
	if collision_shape_type == 0:        # Box
		shape = BoxShape.new()
		shape.extents = Vector3(size.x * 0.5 * f, size.y * 0.5, size.z * 0.5 * f)
	elif collision_shape_type == 2:      # Sphere
		shape = SphereShape.new()
		shape.radius = max(size.x, max(size.y, size.z)) * 0.5 * f
	else:                                # Cylinder (padrao, bom p/ tronco)
		shape = CylinderShape.new()
		shape.radius = max(size.x, size.z) * 0.5 * f
		shape.height = size.y

	cs.shape = shape
	cs.transform.origin = center
	body.add_child(cs)
	_own(cs)


func _mesh_index_for(name):
	for i in range(model_names.size()):
		if model_names[i] == name:
			return i if i < meshes.size() else -1
	# fallback: se so ha 1 mesh e o JSON tambem tem 1 modelo, casa direto
	if meshes.size() == 1 and model_names.empty():
		return 0
	return -1


func _name_for_mesh(i):
	if i < model_names.size():
		return model_names[i]
	return i


func _is_collidable(name):
	for c in collidable_names:
		if c == name:
			return true
	return false


func _own(node):
	if Engine.editor_hint and get_tree() != null:
		node.owner = get_tree().get_edited_scene_root()


func _load_json(path):
	var f = File.new()
	if f.open(path, File.READ) != OK:
		push_error("MultiMeshFromBlender: nao consegui abrir " + path)
		return null
	var txt = f.get_as_text()
	f.close()
	var res = JSON.parse(txt)
	if res.error != OK:
		push_error("MultiMeshFromBlender: JSON invalido - " + res.error_string)
		return null
	return res.result
