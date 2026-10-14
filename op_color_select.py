import bpy

from . import utilities_color


class op(bpy.types.Operator):
	bl_idname = "uv.ttbake_color_select"
	bl_label = "Select by Color"
	bl_description = "Select the faces with this Color ID material, in every selected or edited mesh"
	bl_options = {'UNDO'}

	index : bpy.props.IntProperty(description="Color Index", default=0)

	@classmethod
	def poll(cls, context):
		if not context.area or context.area.ui_type != 'UV':
			return False
		objects, _ = utilities_color.get_target_objects(context)
		return len(objects) > 0

	def execute(self, context):
		found = select_color(context, self.index)
		if not found:
			self.report({'WARNING'}, f"No faces use Color ID {self.index + 1}")
		return {'FINISHED'}


def select_color(context, index):
	objects, edit = utilities_color.get_target_objects(context)
	if not edit:
		bpy.ops.object.mode_set(mode='EDIT')
		objects, edit = utilities_color.get_target_objects(context)

	material = utilities_color.get_material(index)
	found = 0
	for obj in objects:
		bm = utilities_color.get_bmesh(obj, True)
		for face in bm.faces:
			face.select = False
		for edge in bm.edges:
			edge.select = False
		for vert in bm.verts:
			vert.select = False

		slots = obj.material_slots
		if index < len(slots) and slots[index].material is not None and slots[index].material == material:
			for face in bm.faces:
				if face.material_index == index:
					face.select = True
					found += 1
		bm.select_flush_mode()
		utilities_color.finish_bmesh(obj, bm, True)

	utilities_color.update_properties_tab()
	utilities_color.update_view_mode()
	return found
