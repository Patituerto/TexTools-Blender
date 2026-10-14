import bpy

from . import utilities_color


class op(bpy.types.Operator):
	bl_idname = "uv.ttbake_color_clear"
	bl_label = "Clear Colors"
	bl_description = "Clear the Color IDs (materials or vertex colors) of every selected or edited mesh"
	bl_options = {'UNDO'}

	@classmethod
	def poll(cls, context):
		if not context.area or context.area.ui_type != 'UV':
			return False
		objects, _ = utilities_color.get_target_objects(context)
		return len(objects) > 0

	def execute(self, context):
		clear_colors(context)
		return {'FINISHED'}


def clear_colors(context):
	objects, edit = utilities_color.get_target_objects(context)
	if edit:
		bpy.ops.object.mode_set(mode='OBJECT')

	if context.scene.ttBakeSettings.color_assign_mode == 'MATERIALS':
		for obj in objects:
			obj.data.materials.clear()
		# Delete Color ID materials that are no longer used
		for material in list(bpy.data.materials):
			if utilities_color.material_prefix in material.name and not material.users:
				bpy.data.materials.remove(material, do_unlink=True)
	else:  # VERTEXCOLORS
		for obj in objects:
			attributes = obj.data.color_attributes
			if utilities_color.VERTEX_COLOR_LAYER in attributes:
				attributes.remove(attributes[utilities_color.VERTEX_COLOR_LAYER])

	if edit:
		bpy.ops.object.mode_set(mode='EDIT')

	utilities_color.update_properties_tab()
	utilities_color.update_view_mode()
