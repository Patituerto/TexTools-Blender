import bpy
from mathutils import Color

from . import utilities_color


class op(bpy.types.Operator):
	bl_idname = "uv.ttbake_color_select_vertex"
	bl_label = "Select by Vertex Color"
	bl_description = "Select the faces painted with this Color ID, in every selected or edited mesh"
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
			self.report({'WARNING'}, f"No faces painted with Color ID {self.index + 1}")
		return {'FINISHED'}


def select_color(context, index):
	objects, edit = utilities_color.get_target_objects(context)
	if not edit:
		bpy.ops.object.mode_set(mode='EDIT')
		objects, edit = utilities_color.get_target_objects(context)

	# Same color value that op_color_assign writes, so the comparison matches
	target = Color(utilities_color.vertex_id_color(index)[:3])
	# Faces average their corner colors, so a small threshold is needed
	threshold = context.scene.ttBakeSettings.vertex_color_threshold

	found = 0
	for obj in objects:
		bm = utilities_color.get_bmesh(obj, True)
		for face in bm.faces:
			face.select = False
		for edge in bm.edges:
			edge.select = False
		for vert in bm.verts:
			vert.select = False

		layer = bm.loops.layers.color.get(utilities_color.VERTEX_COLOR_LAYER)
		if layer is not None:
			for face in bm.faces:
				r = g = b = 0.0
				for loop in face.loops:
					c = loop[layer]
					r += c[0]
					g += c[1]
					b += c[2]
				n = len(face.loops)
				if (abs(r / n - target.r) < threshold and
					abs(g / n - target.g) < threshold and
					abs(b / n - target.b) < threshold):
					face.select = True
					found += 1
		bm.select_flush_mode()
		utilities_color.finish_bmesh(obj, bm, True)

	return found
