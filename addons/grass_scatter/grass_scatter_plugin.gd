tool
extends EditorPlugin
# Registra o no unificado "ScatterMultiMesh" no editor do Godot 3.6.

func _enter_tree():
	add_custom_type(
		"ScatterMultiMesh",        # grama E props no mesmo no
		"Spatial",
		preload("scatter_multimesh.gd"),
		null                       # icone (opcional)
	)


func _exit_tree():
	remove_custom_type("ScatterMultiMesh")
