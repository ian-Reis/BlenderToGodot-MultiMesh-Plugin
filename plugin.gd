tool
extends EditorPlugin
# Registra o no unificado "MultiMeshFromBlender" no editor do Godot 3.6.

func _enter_tree():
	add_custom_type(
		"MultiMeshFromBlender",     # grama E props no mesmo no
		"Spatial",
		preload("multimesh_from_blender.gd"),
		null                        # icone (opcional)
	)


func _exit_tree():
	remove_custom_type("MultiMeshFromBlender")
