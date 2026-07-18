tool
extends Spatial
# MultiMeshFromBlender (Godot 3.6) - no unificado
# Le o JSON exportado pelo add-on do Blender (transform completo, multi-modelo) e monta:
#   - 1 MultiMeshInstance por modelo (visual otimizado, 1 draw call cada);
#   - (opcional) material unico via Override Material (ex.: shader de vento);
#   - (opcional) StaticBody + CollisionShape por instancia dos modelos colidiveis.
#
# RESOLUCAO DAS MALHAS (duas formas):
#   A) DINAMICO (recomendado): defina "Source Scene" com a cena importada (.glb).
#      As malhas sao resolvidas automaticamente pelo NOME de cada no
#      (Pine_1, Grass_Common_Short, ...), que casa com os "models" do JSON.
#      Nao precisa preencher Meshes/Model Names.
#   B) MANUAL (fallback): preencha "Meshes" e "Model Names" na mesma ordem.
#
# Marque "Rebuild" para (re)construir no editor.

export(String, FILE, "*.json") var json_path = "res://scatter.json"

# --- A) modo dinamico ---
export(PackedScene) var source_scene = null
# --- B) modo manual (usado se Source Scene estiver vazio) ---
export(Array, Mesh) var meshes
export(PoolStringArray) var model_names

# Material unico opcional para todas as malhas do no (vazio = usa o material de cada malha).
# Para grama de card com vento, monte um ShaderMaterial com grass.shader e coloque aqui.
export(Material) var override_material = null

# Colisao (para modelos listados em collidable_names)
export(PoolStringArray) var collidable_names
export(int, "Box", "Cylinder", "Sphere") var collision_shape_type = 1
export(float) var collision_size_factor = 0.4
export(int, LAYERS_3D_PHYSICS) var collision_layer = 1

export(int, "Off", "On", "DoubleSided", "ShadowsOnly") var cast_shadow = 1
export(bool) var rebuild setget _set_rebuild


func _set_rebuild(_v):
	build()


func _ready():
	if Engine.editor_hint:
		return
	# Em runtime, so reconstroi se a cena NAO tiver os nos ja "assados".
	# Se voce ja construiu no editor (com Rebuild), os MultiMeshInstance ficam
	# salvos na cena com seus materiais/config (ex.: shader de vento na grama) -
	# preserva-los evita perder overrides e reconstruir a cada execucao.
	# Node fresco (sem filhos) reconstroi normalmente a partir do JSON.
	if get_child_count() == 0:
		build()


func build():
	for c in get_children():
		c.queue_free()

	var data = _load_json(json_path)
	if data == null:
		return

	var models = data["models"]
	var count = int(data["count"])
	var midx = data["model"]
	var xf = data["xf"]

	var name_to_mesh = _resolve_meshes()   # nome -> Mesh
	if name_to_mesh.empty():
		push_warning("MultiMeshFromBlender: defina 'Source Scene' ou 'Meshes' + 'Model Names'.")
		return

	var mat = _resolve_material()

	# agrupa transforms por malha
	var by_mesh = {}          # Mesh -> Array<Transform>
	var mesh_name = {}        # Mesh -> nome (para nomear o no)
	var collide_list = []
	var missing = {}

	for i in range(count):
		var nm = models[int(midx[i])]
		if not name_to_mesh.has(nm):
			missing[nm] = true
			continue
		var mesh = name_to_mesh[nm]
		var o = i * 12
		var t = Transform(
			Vector3(xf[o + 0], xf[o + 1], xf[o + 2]),
			Vector3(xf[o + 3], xf[o + 4], xf[o + 5]),
			Vector3(xf[o + 6], xf[o + 7], xf[o + 8]),
			Vector3(xf[o + 9], xf[o + 10], xf[o + 11]))
		if not by_mesh.has(mesh):
			by_mesh[mesh] = []
			mesh_name[mesh] = nm
		by_mesh[mesh].append(t)
		if _is_collidable(nm):
			collide_list.append({"t": t, "mesh": mesh})

	for mesh in by_mesh.keys():
		var list = by_mesh[mesh]
		var mm = MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		mm.instance_count = list.size()
		for j in range(list.size()):
			mm.set_instance_transform(j, list[j])

		var mmi = MultiMeshInstance.new()
		mmi.name = "MM_" + str(mesh_name[mesh])
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

	if not missing.empty():
		push_warning("MultiMeshFromBlender: sem malha para: " + str(missing.keys()))
	print("MultiMeshFromBlender: ", count, " instancias, ",
		by_mesh.size(), " modelo(s), ", collide_list.size(), " colisores.")


# --- resolucao de malhas ---
func _resolve_meshes():
	var d = {}
	if source_scene != null:
		var root = source_scene.instance()
		_collect_meshes(root, d)
		root.free()
	else:
		for i in range(meshes.size()):
			if i < model_names.size() and meshes[i] != null:
				d[model_names[i]] = meshes[i]
	return d


func _collect_meshes(node, d):
	if node is MeshInstance and node.mesh != null:
		d[node.name] = node.mesh
	for c in node.get_children():
		_collect_meshes(c, d)


func _resolve_material():
	return override_material


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
