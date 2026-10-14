import bpy

from . import utilities_color


class op(bpy.types.Operator):
	bl_idname = "uv.ttbake_color_assign"
	bl_label = "Assign Color"
	bl_description = "Assign color to the selected Objects, or to the selected faces of every mesh in Edit Mode"
	bl_options = {'UNDO'}

	index: bpy.props.IntProperty(description="Color Index", default=0)

	@classmethod
	def poll(cls, context):
		if not context.area or context.area.ui_type != 'UV':
			return False
		objects, _ = utilities_color.get_target_objects(context)
		return len(objects) > 0

	def execute(self, context):
		count = assign_color(context, self.index)
		if count == 0:
			self.report({'WARNING'}, "Nothing to color: select some faces")
			return {'CANCELLED'}
		return {'FINISHED'}


def assign_color(context, index):
	"""Assign Color ID 'index' to whole objects (Object Mode) or to the selected faces of every edited mesh (Edit Mode).
	Works directly on the mesh data, so multi-object Edit Mode and the selection are preserved."""
	objects, edit = utilities_color.get_target_objects(context)
	mode = context.scene.ttBakeSettings.color_assign_mode
	painted_faces = 0

	for obj in objects:
		mesh = obj.data
		if mode == 'MATERIALS':
			# Make sure the material slot exists and holds the Color ID material
			while len(mesh.materials) <= index:
				mesh.materials.append(None)
			utilities_color.assign_slot(obj, index)

		bm = utilities_color.get_bmesh(obj, edit)
		faces = [f for f in bm.faces if f.select] if edit else list(bm.faces)

		if mode == 'MATERIALS':
			for face in faces:
				face.material_index = index
		else:  # VERTEXCOLORS
			layer = bm.loops.layers.color.get(utilities_color.VERTEX_COLOR_LAYER)
			if layer is None:
				layer = bm.loops.layers.color.new(utilities_color.VERTEX_COLOR_LAYER)
			color = utilities_color.safe_color(tuple(utilities_color.vertex_id_color(index)))
			for face in faces:
				for loop in face.loops:
					loop[layer] = color

		painted_faces += len(faces)
		utilities_color.finish_bmesh(obj, bm, edit)

		if mode != 'MATERIALS':
			attributes = mesh.color_attributes
			if utilities_color.VERTEX_COLOR_LAYER in attributes:
				attributes.active_color = attributes[utilities_color.VERTEX_COLOR_LAYER]

	# Show Material or Data Tab and switch the viewport shading
	utilities_color.update_properties_tab()
	utilities_color.update_view_mode()
	return painted_faces
